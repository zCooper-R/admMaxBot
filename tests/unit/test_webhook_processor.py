import pytest
from django.db import connection

from apps.bot.models import (
    BotUser,
    MenuNode,
    MenuNodeType,
    UserSessionState,
    WebhookEvent,
    WebhookEventStatus,
)
from apps.max_integration.services import MessageService
from apps.webhooks.services import (
    SAFE_PROCESSING_ERROR_CODE,
    SAFE_PROCESSING_ERROR_MESSAGE,
    WebhookProcessor,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {
            "update_id": "evt-unsupported",
            "update_type": "unknown_type",
            "chat_id": 1001,
            "user": {"user_id": "u-unsupported", "name": "Test User"},
        },
        {
            "update_id": "evt-missing-user",
            "update_type": "message_created",
            "chat_id": 1001,
            "message": {"body": {"text": "Привет"}},
        },
        {
            "update_id": "evt-missing-chat",
            "update_type": "message_created",
            "user": {"user_id": "u-missing-chat", "name": "Test User"},
        },
    ],
)
def test_rejects_unsupported_or_malformed_payload_without_side_effects(payload):
    processor = WebhookProcessor()

    result = processor.process(payload)

    assert result.ok is False
    assert result.status == WebhookEventStatus.REJECTED
    assert WebhookEvent.objects.count() == 0
    assert BotUser.objects.count() == 0
    assert UserSessionState.objects.count() == 0


@pytest.mark.django_db
def test_callback_prefers_first_bot_message_for_edit(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])
    MenuNode.objects.create(
        parent=root_node,
        title="Section",
        slug="section",
        node_type=MenuNodeType.MENU,
        response_text="Section text",
        sort_order=20,
    )

    calls: list[dict[str, object]] = []

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        calls.append(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "text": text,
                "edit_message_id": edit_message_id,
            }
        )
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": "mid-root" if edit_message_id is None else edit_message_id,
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    processor = WebhookProcessor()
    processor.process(
        {
            "update_id": "evt-1",
            "update_type": "bot_started",
            "chat_id": 1001,
            "user": {"user_id": "5809367", "name": "Test User"},
        }
    )
    processor.process(
        {
            "update_id": "evt-2",
            "update_type": "message_callback",
            "chat_id": 1001,
            "user": {"user_id": "129086805", "name": "Test User"},
            "callback": {
                "payload": "menu:section",
                "message_id": "callback-mid",
            },
        }
    )

    assert len(calls) == 2
    assert calls[0]["edit_message_id"] is None
    assert calls[1]["edit_message_id"] == "mid-root"
    assert UserSessionState.objects.count() == 1
    assert UserSessionState.objects.filter(chat_id=1001).count() == 1
    assert BotUser.objects.filter(external_user_id="5809367").count() == 1
    assert BotUser.objects.filter(external_user_id="129086805").count() == 1


@pytest.mark.django_db
def test_bot_started_without_chat_id_is_not_rejected(root_node):
    processor = WebhookProcessor()

    result = processor.process(
        {
            "update_id": "evt-bot-started-no-chat",
            "update_type": "bot_started",
            "user": {"user_id": "u-start", "name": "Start User"},
        }
    )

    assert result.ok is True
    assert result.status == WebhookEventStatus.PROCESSED
    assert WebhookEvent.objects.filter(external_event_id="evt-bot-started-no-chat").count() == 1
    assert BotUser.objects.filter(external_user_id="u-start").count() == 1
    assert UserSessionState.objects.count() == 1
    assert UserSessionState.objects.get().chat_id is None


@pytest.mark.django_db
def test_back_navigates_to_parent_not_previous_node(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])
    root_node.response_text = "Root"
    root_node.save(update_fields=["response_text", "updated_at"])

    node_a = MenuNode.objects.create(
        parent=root_node,
        title="A",
        slug="a",
        node_type=MenuNodeType.MENU,
        response_text="A",
        sort_order=10,
    )
    MenuNode.objects.create(
        parent=node_a,
        title="B",
        slug="b",
        node_type=MenuNodeType.MENU,
        response_text="B",
        sort_order=10,
    )
    MenuNode.objects.create(
        parent=root_node,
        title="X",
        slug="x",
        node_type=MenuNodeType.MENU,
        response_text="X",
        sort_order=20,
    )

    calls: list[dict[str, object]] = []

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        calls.append({"chat_id": chat_id, "text": text, "edit_message_id": edit_message_id})
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": "mid-root" if edit_message_id is None else edit_message_id,
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    processor = WebhookProcessor()
    common = {"chat_id": 1001, "user": {"user_id": "u1", "name": "Test User"}}
    processor.process({"update_id": "evt-1", "update_type": "bot_started", **common})
    processor.process(
        {
            "update_id": "evt-2",
            "update_type": "message_callback",
            **common,
            "callback": {"payload": "menu:a", "message_id": "callback-mid"},
        }
    )
    processor.process(
        {
            "update_id": "evt-3",
            "update_type": "message_callback",
            **common,
            "callback": {"payload": "menu:b", "message_id": "callback-mid"},
        }
    )
    processor.process(
        {
            "update_id": "evt-4",
            "update_type": "message_callback",
            **common,
            "callback": {"payload": "menu:x", "message_id": "callback-mid"},
        }
    )
    processor.process(
        {
            "update_id": "evt-5",
            "update_type": "message_callback",
            **common,
            "callback": {"payload": "nav:back", "message_id": "callback-mid"},
        }
    )

    assert calls[-1]["text"] == "Root"


@pytest.mark.django_db
def test_failed_webhook_retries_without_duplicate_status(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])
    root_node.response_text = "Root"
    root_node.save(update_fields=["response_text", "updated_at"])

    calls: list[dict[str, object]] = []

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        calls.append({"chat_id": chat_id, "edit_message_id": edit_message_id})
        if len(calls) == 1:
            raise RuntimeError("token=secret123 upstream failure")
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": "mid-2",
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    processor = WebhookProcessor()
    payload = {
        "update_id": "evt-retry-1",
        "update_type": "message_created",
        "chat_id": 1001,
        "user": {"user_id": "u-retry", "name": "Retry User"},
        "message": {"body": {"text": "меню"}},
    }

    first = processor.process(payload)
    event = WebhookEvent.objects.get(external_event_id="evt-retry-1")
    assert first.ok is False
    assert first.status == WebhookEventStatus.FAILED
    assert SAFE_PROCESSING_ERROR_CODE in first.message
    assert SAFE_PROCESSING_ERROR_MESSAGE in first.message
    assert event.status == WebhookEventStatus.FAILED
    assert SAFE_PROCESSING_ERROR_CODE in event.error_message
    assert SAFE_PROCESSING_ERROR_MESSAGE in event.error_message
    assert "token=secret123" not in event.error_message

    second = processor.process(payload)
    event.refresh_from_db()
    assert second.ok is True
    assert second.status == WebhookEventStatus.PROCESSED
    assert event.status == WebhookEventStatus.PROCESSED
    assert event.error_message == ""
    assert len(calls) == 2


@pytest.mark.django_db
def test_outbound_send_happens_outside_atomic_transaction(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])
    root_node.response_text = "Root"
    root_node.save(update_fields=["response_text", "updated_at"])

    savepoint_depths: list[int] = []
    initial_savepoint_depth = len(connection.savepoint_ids)

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        savepoint_depths.append(len(connection.savepoint_ids))
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": "mid-ok",
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    result = WebhookProcessor().process(
        {
            "update_id": "evt-non-atomic-send",
            "update_type": "message_created",
            "chat_id": 1001,
            "user": {"user_id": "u-atomic", "name": "Atomic User"},
            "message": {"body": {"text": "меню"}},
        }
    )

    assert result.ok is True
    assert savepoint_depths == [initial_savepoint_depth]


@pytest.mark.django_db
def test_start_command_sends_new_menu_message_instead_of_edit(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])

    calls: list[dict[str, object]] = []

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        calls.append(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "text": text,
                "edit_message_id": edit_message_id,
            }
        )
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": f"mid-{len(calls)}",
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    processor = WebhookProcessor()
    common = {"chat_id": 1001, "user": {"user_id": "5809367", "name": "Start User"}}
    processor.process({"update_id": "evt-start-1", "update_type": "bot_started", **common})
    processor.process(
        {
            "update_id": "evt-start-2",
            "update_type": "message_created",
            **common,
            "message": {"body": {"text": "/start"}},
        }
    )

    assert len(calls) == 2
    assert calls[0]["edit_message_id"] is None
    assert calls[1]["edit_message_id"] is None


@pytest.mark.django_db
def test_bot_started_without_chat_id_sends_menu_by_user_id(monkeypatch, bot_settings, root_node):
    bot_settings.is_enabled = True
    bot_settings.save(update_fields=["is_enabled", "updated_at"])

    calls: list[dict[str, object]] = []

    def fake_send_text(self, chat_id, text, buttons=None, edit_message_id=None, user_id=None):
        calls.append(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "text": text,
                "edit_message_id": edit_message_id,
                "buttons": buttons,
            }
        )
        return {
            "ok": True,
            "status_code": 200,
            "data": {},
            "error": "",
            "message_id": "mid-user-start",
        }

    monkeypatch.setattr(MessageService, "send_text", fake_send_text)

    result = WebhookProcessor().process(
        {
            "update_id": "evt-bot-start-user-send",
            "update_type": "bot_started",
            "user": {"user_id": "5809367", "name": "Start User"},
        }
    )

    assert result.ok is True
    assert calls == [
        {
            "chat_id": None,
            "user_id": 5809367,
            "text": root_node.response_text,
            "edit_message_id": None,
            "buttons": [],
        }
    ]
