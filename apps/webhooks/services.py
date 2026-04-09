from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone as django_timezone

from apps.bot.models import BotUser, MenuNode, UserSessionState, WebhookEvent, WebhookEventStatus
from apps.max_integration.config import WebhookConfigResolver
from apps.max_integration.services import MessageService
from apps.menu_builder.services import MenuRuntimeService

logger = logging.getLogger(__name__)

SAFE_PROCESSING_ERROR_CODE = "processing_error"
SAFE_PROCESSING_ERROR_MESSAGE = "Внутренняя ошибка обработки webhook"
SUPPORTED_UPDATE_TYPES: tuple[str, ...] = (
    "message_created",
    "message_callback",
    "bot_started",
)


@dataclass(slots=True)
class ProcessResult:
    ok: bool
    status: WebhookEventStatus
    message: str


@dataclass(slots=True)
class PreparedEventContext:
    ext_event_id: str
    event_type: str
    payload: dict[str, Any]
    user: BotUser
    event: WebhookEvent


class WebhookProcessor:
    def __init__(self) -> None:
        self.config = WebhookConfigResolver().resolve()
        self.runtime = MenuRuntimeService()
        self.message_service = MessageService(config=self.config)

    def validate_secret(self, header_secret: str | None) -> bool:
        expected = self.config.webhook_secret.strip()
        if not expected:
            return getattr(settings, "MAXBOT_ENV", "development").strip().lower() != "production"
        return bool(header_secret and secrets.compare_digest(header_secret, expected))

    def is_secret_configured(self) -> bool:
        return bool(self.config.webhook_secret.strip())

    @staticmethod
    def is_production_mode() -> bool:
        return getattr(settings, "MAXBOT_ENV", "development").strip().lower() == "production"

    @staticmethod
    def validate_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        event_type = WebhookProcessor.event_type(payload)
        if event_type not in SUPPORTED_UPDATE_TYPES:
            return False, "unsupported_update_type"

        user_external_id, _ = WebhookProcessor.extract_user_data(payload)
        if user_external_id == "unknown":
            return False, "missing_user_id"

        requires_chat_id = event_type in {"message_created", "message_callback"}
        if requires_chat_id and WebhookProcessor.extract_chat_id(payload) is None:
            return False, "missing_chat_id"

        if event_type == "message_callback":
            callback = payload.get("callback")
            if not isinstance(callback, dict) or not str(callback.get("payload") or "").strip():
                return False, "missing_callback_payload"

        return True, ""

    @staticmethod
    def event_id(payload: dict[str, Any]) -> str:
        explicit = payload.get("update_id") or payload.get("event_id")
        if explicit:
            return str(explicit)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def event_type(payload: dict[str, Any]) -> str:
        return str(payload.get("update_type") or payload.get("type") or "unknown")

    @staticmethod
    def extract_user_data(payload: dict[str, Any]) -> tuple[str, str]:
        user = payload.get("user") or {}
        message = payload.get("message") or {}
        sender = message.get("sender") if isinstance(message, dict) else {}
        callback = payload.get("callback") or {}
        callback_sender = callback.get("sender") if isinstance(callback, dict) else {}
        callback_user = callback.get("user") if isinstance(callback, dict) else {}

        candidates: list[dict[str, Any]] = []
        for candidate in (sender, callback_sender, callback_user, user):
            if isinstance(candidate, dict):
                candidates.append(candidate)

        preferred: dict[str, Any] | None = None
        fallback: dict[str, Any] | None = None
        for candidate in candidates:
            candidate_id = candidate.get("user_id")
            if not candidate_id:
                continue
            if fallback is None:
                fallback = candidate
            if candidate.get("is_bot") is False:
                preferred = candidate
                break

        chosen = preferred or fallback or {}
        user_id = chosen.get("user_id")
        name = chosen.get("name") or chosen.get("username") or ""

        if not user_id:
            recipient = message.get("recipient") if isinstance(message, dict) else {}
            user_id = payload.get("user_id") or (recipient.get("user_id") if isinstance(recipient, dict) else None)
        return str(user_id or "unknown"), str(name)

    @staticmethod
    def extract_chat_id(payload: dict[str, Any]) -> int | None:
        chat_id = payload.get("chat_id")
        if chat_id is None:
            message = payload.get("message") or {}
            recipient = message.get("recipient") if isinstance(message, dict) else {}
            if isinstance(recipient, dict):
                chat_id = recipient.get("chat_id")
        if isinstance(chat_id, int):
            return chat_id
        if isinstance(chat_id, str) and chat_id.isdigit():
            return int(chat_id)
        return None

    @staticmethod
    def extract_callback_message_id(payload: dict[str, Any]) -> str | None:
        callback = payload.get("callback")
        if not isinstance(callback, dict):
            return None
        direct_mid = callback.get("message_id") or callback.get("mid")
        if isinstance(direct_mid, str) and direct_mid:
            return direct_mid
        message = callback.get("message")
        if isinstance(message, dict):
            body = message.get("body")
            if isinstance(body, dict):
                mid = body.get("mid")
                if isinstance(mid, str) and mid:
                    return mid
        return None

    def process(self, payload: dict[str, Any]) -> ProcessResult:
        ext_event_id = self.event_id(payload)
        event_type = self.event_type(payload)

        is_valid, validation_error = self.validate_payload(payload)
        if not is_valid:
            logger.warning(
                "webhook_rejected event_id=%s type=%s reason=%s",
                ext_event_id,
                event_type,
                validation_error,
            )
            return ProcessResult(False, WebhookEventStatus.REJECTED, validation_error)

        prepared = self._prepare_event_context(ext_event_id, event_type, payload)
        if isinstance(prepared, ProcessResult):
            return prepared
        return self._process_event(
            prepared.ext_event_id,
            prepared.event_type,
            prepared.payload,
            prepared.user,
            prepared.event,
        )

    def _prepare_event_context(
        self,
        ext_event_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> PreparedEventContext | ProcessResult:
        with transaction.atomic():
            user_external_id, display_name = self.extract_user_data(payload)
            user, _ = BotUser.objects.get_or_create(
                external_user_id=user_external_id,
                defaults={"display_name": display_name},
            )
            if display_name and user.display_name != display_name:
                BotUser.objects.filter(pk=user.pk).update(display_name=display_name, updated_at=django_timezone.now())
                user.display_name = display_name

            try:
                event, created = WebhookEvent.objects.get_or_create(
                    external_event_id=ext_event_id,
                    defaults={
                        "event_type": event_type,
                        "payload": payload,
                        "status": WebhookEventStatus.RECEIVED,
                        "user": user,
                    },
                )
            except IntegrityError:
                event = WebhookEvent.objects.filter(external_event_id=ext_event_id).first()
                created = False

            if not created:
                if event and event.status == WebhookEventStatus.FAILED:
                    logger.info("webhook_retry event_id=%s type=%s", ext_event_id, event_type)
                    return PreparedEventContext(ext_event_id, event_type, payload, user, event)
                logger.info("webhook_duplicate event_id=%s", ext_event_id)
                return ProcessResult(True, WebhookEventStatus.DUPLICATE, "Дубликат события")

            BotUser.objects.filter(pk=user.pk).update(
                interactions_count=F("interactions_count") + 1,
                last_seen_at=django_timezone.now(),
                updated_at=django_timezone.now(),
            )
            return PreparedEventContext(ext_event_id, event_type, payload, user, event)

    def _process_event(
        self,
        ext_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        user: BotUser,
        event: WebhookEvent,
    ) -> ProcessResult:
        started = time.perf_counter()
        try:
            self._process_business(payload, user, event)
            event.status = WebhookEventStatus.PROCESSED
            event.error_message = ""
            event.processed_at = datetime.now(tz=timezone.utc)
            event.processing_duration_ms = int((time.perf_counter() - started) * 1000)
            event.save(update_fields=["status", "error_message", "processed_at", "processing_duration_ms"])
            logger.info(
                "webhook_processed event_id=%s type=%s duration_ms=%s",
                ext_event_id,
                event_type,
                event.processing_duration_ms,
            )
            return ProcessResult(True, WebhookEventStatus.PROCESSED, "Обработано")
        except Exception:  # noqa: BLE001
            event.status = WebhookEventStatus.FAILED
            event.error_message = self._safe_error_message()
            event.processed_at = datetime.now(tz=timezone.utc)
            event.processing_duration_ms = int((time.perf_counter() - started) * 1000)
            event.save(update_fields=["status", "error_message", "processed_at", "processing_duration_ms"])
            logger.exception("webhook_failed event_id=%s type=%s", ext_event_id, event_type)
            return ProcessResult(False, WebhookEventStatus.FAILED, self._safe_error_message())

    @staticmethod
    def _safe_error_message() -> str:
        return f"{SAFE_PROCESSING_ERROR_CODE}: {SAFE_PROCESSING_ERROR_MESSAGE}"

    def _process_business(self, payload: dict[str, Any], user: BotUser, event: WebhookEvent) -> None:
        event_type = self.event_type(payload)
        chat_id = self.extract_chat_id(payload)
        user_id = self._extract_numeric_user_id(user.external_user_id)
        session: UserSessionState | None = None
        if chat_id is not None:
            session = UserSessionState.objects.filter(chat_id=chat_id).first()
        if session is None:
            session, _ = UserSessionState.objects.get_or_create(user=user, defaults={"chat_id": chat_id})
        elif session.chat_id is None and chat_id is not None:
            session.chat_id = chat_id
            session.save(update_fields=["chat_id", "updated_at"])

        node: MenuNode | None = session.current_node
        callback_payload = ""
        should_edit_existing = event_type == "message_callback"

        if event_type == "message_callback":
            callback = payload.get("callback") or {}
            callback_payload = str(callback.get("payload") or "")
        elif event_type == "message_created":
            message = payload.get("message") or {}
            raw_body = message.get("body")
            if isinstance(raw_body, dict):
                body = str(raw_body.get("text") or "").strip().lower()
            else:
                body = str(raw_body or "").strip().lower()
            if body in {"/start", "start", "меню"}:
                callback_payload = "nav:root"
        elif event_type == "bot_started":
            callback_payload = "nav:root"

        if callback_payload == "nav:root" and event_type in {"message_created", "bot_started"}:
            should_edit_existing = False

        if callback_payload == "nav:root" or node is None:
            node = MenuNode.objects.filter(parent__isnull=True, is_active=True).order_by("sort_order").first()
        elif callback_payload == "nav:back":
            current = session.current_node
            if current and current.parent:
                node = current.parent
            else:
                node = MenuNode.objects.filter(parent__isnull=True, is_active=True).order_by("sort_order").first()
        else:
            resolved = self.runtime.resolve_by_payload(callback_payload)
            if resolved:
                node = resolved

        if node is None:
            return

        render_result = self.runtime.render_node(node)

        session.previous_node = session.current_node
        session.current_node = node
        history = session.history if isinstance(session.history, list) else []
        history.append(node.slug)
        session.history = history[-30:]
        session.save(update_fields=["previous_node", "current_node", "history", "updated_at"])

        event.related_node = node
        event.save(update_fields=["related_node"])

        if chat_id is not None and self.config.is_enabled:
            callback_mid = self.extract_callback_message_id(payload)
            send_result = self.message_service.send_text(
                chat_id,
                render_result.text,
                render_result.buttons,
                edit_message_id=(session.last_bot_message_id or callback_mid or None) if should_edit_existing else None,
                user_id=user_id,
            )
            if not send_result["ok"]:
                raise RuntimeError(f"MAX /messages error: {send_result['error']}")
            message_id = send_result.get("message_id")
            if isinstance(message_id, str) and message_id:
                session.last_bot_message_id = message_id
                session.save(update_fields=["last_bot_message_id", "updated_at"])
        elif self.config.is_enabled and user_id is not None:
            send_result = self.message_service.send_text(
                None,
                render_result.text,
                render_result.buttons,
                user_id=user_id,
            )
            if not send_result["ok"]:
                raise RuntimeError(f"MAX /messages error: {send_result['error']}")
            message_id = send_result.get("message_id")
            if isinstance(message_id, str) and message_id:
                session.last_bot_message_id = message_id
                session.save(update_fields=["last_bot_message_id", "updated_at"])

    @staticmethod
    def _extract_numeric_user_id(external_user_id: str) -> int | None:
        if external_user_id.isdigit():
            return int(external_user_id)
        return None
