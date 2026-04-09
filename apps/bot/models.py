from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.crypto import decrypt_value, encrypt_value, is_encrypted_value
from apps.core.models import TimeStampedModel


class BotSettings(TimeStampedModel):
    SECRET_FIELD_NAMES = ("token", "webhook_secret")

    token = models.CharField("Токен бота", max_length=2048, blank=True)
    webhook_secret = models.CharField("Webhook secret", max_length=1024, blank=True)
    base_url = models.URLField("Базовый URL", default="https://platform-api.max.ru")
    webhook_path = models.CharField("Путь webhook", max_length=128, default="/webhooks/max/")
    is_enabled = models.BooleanField("Бот включен", default=True)
    debug_logging = models.BooleanField("Расширенное логирование", default=False)

    class Meta:
        verbose_name = "Настройки бота"
        verbose_name_plural = "Настройки бота"

    def __str__(self) -> str:
        return "Настройки бота"

    @classmethod
    def get_solo(cls) -> "BotSettings":
        settings, _ = cls.objects.get_or_create(id=1)
        return settings

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._decrypt_secret_fields()
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        self._decrypt_secret_fields()

    def save(self, *args, **kwargs):
        plaintext = self._encrypt_secret_fields()
        try:
            return super().save(*args, **kwargs)
        finally:
            for field_name, original_value in plaintext.items():
                self.__dict__[field_name] = original_value

    def _decrypt_secret_fields(self) -> None:
        for field_name in self.SECRET_FIELD_NAMES:
            value = self.__dict__.get(field_name)
            if isinstance(value, str) and is_encrypted_value(value):
                self.__dict__[field_name] = decrypt_value(value)

    def _encrypt_secret_fields(self) -> dict[str, str]:
        plaintext: dict[str, str] = {}
        for field_name in self.SECRET_FIELD_NAMES:
            value = self.__dict__.get(field_name)
            if not isinstance(value, str) or not value or is_encrypted_value(value):
                continue
            plaintext[field_name] = value
            self.__dict__[field_name] = encrypt_value(value)
        return plaintext


class MenuNodeType(models.TextChoices):
    MENU = "menu", "Меню"
    MESSAGE = "message", "Сообщение"
    LINK = "link", "Ссылка"
    BACK = "back", "Назад"
    ROOT = "root", "В главное меню"
    ACTION = "action", "Заглушка под действие"
    TRANSITION = "transition", "Служебный переход"


class MenuNode(TimeStampedModel):
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", blank=True, null=True
    )
    title = models.CharField("Название кнопки", max_length=120)
    slug = models.SlugField("Slug", max_length=120, unique=True)
    response_text = models.TextField("Текст ответа", blank=True)
    node_type = models.CharField(
        "Тип узла", max_length=32, choices=MenuNodeType.choices, default=MenuNodeType.MENU
    )
    sort_order = models.PositiveIntegerField("Порядок", default=100)
    is_active = models.BooleanField("Активен", default=True)
    is_visible = models.BooleanField("Показывать кнопку", default=True)
    payload = models.JSONField("Служебный payload", blank=True, null=True)
    icon = models.CharField("Иконка/эмодзи", max_length=16, blank=True)
    admin_comment = models.TextField("Комментарий", blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Узел меню"
        verbose_name_plural = "Узлы меню"

    def __str__(self) -> str:
        return f"{self.title} ({self.slug})"

    def clean(self) -> None:
        super().clean()
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Узел не может быть родителем сам себе")
        if self.id and self.parent_id:
            cursor = self.parent
            while cursor is not None:
                if cursor.id == self.id:
                    raise ValidationError("Обнаружен цикл в дереве меню")
                cursor = cursor.parent


class BotUser(TimeStampedModel):
    external_user_id = models.CharField("Внешний ID", max_length=128, unique=True)
    display_name = models.CharField("Имя", max_length=255, blank=True)
    first_seen_at = models.DateTimeField("Первое взаимодействие", auto_now_add=True)
    last_seen_at = models.DateTimeField("Последнее взаимодействие", auto_now=True)
    interactions_count = models.PositiveIntegerField("Кол-во взаимодействий", default=0)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Пользователь бота"
        verbose_name_plural = "Пользователи бота"

    def __str__(self) -> str:
        return f"{self.display_name or 'Без имени'} ({self.external_user_id})"


class UserSessionState(TimeStampedModel):
    user = models.OneToOneField(BotUser, on_delete=models.CASCADE, related_name="session")
    chat_id = models.BigIntegerField("ID чата", null=True, blank=True, unique=True)
    current_node = models.ForeignKey(
        MenuNode, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_sessions"
    )
    previous_node = models.ForeignKey(
        MenuNode, on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_sessions"
    )
    history = models.JSONField("История", default=list, blank=True)
    last_bot_message_id = models.CharField("ID последнего сообщения бота", max_length=128, blank=True)

    class Meta:
        verbose_name = "Состояние сессии"
        verbose_name_plural = "Состояния сессий"


class WebhookEventStatus(models.TextChoices):
    RECEIVED = "received", "Получено"
    PROCESSED = "processed", "Обработано"
    FAILED = "failed", "Ошибка"
    DUPLICATE = "duplicate", "Дубликат"
    REJECTED = "rejected", "Отклонено"


class WebhookEvent(TimeStampedModel):
    external_event_id = models.CharField("Внешний ID события", max_length=255, unique=True)
    event_type = models.CharField("Тип события", max_length=80)
    payload = models.JSONField("Payload")
    received_at = models.DateTimeField("Получено", auto_now_add=True)
    processed_at = models.DateTimeField("Обработано", null=True, blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=WebhookEventStatus.choices, default=WebhookEventStatus.RECEIVED
    )
    error_message = models.TextField("Ошибка", blank=True)
    processing_duration_ms = models.PositiveIntegerField("Длительность, мс", null=True, blank=True)
    user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True)
    related_node = models.ForeignKey(MenuNode, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Webhook-событие"
        verbose_name_plural = "Webhook-события"


class WebhookOperationType(models.TextChoices):
    SET = "set", "Установить webhook"
    UPDATE = "update", "Обновить webhook"
    INFO = "info", "Получить информацию"
    DELETE = "delete", "Удалить webhook"
    CHECK = "check", "Проверка соединения"


class WebhookOperationLog(TimeStampedModel):
    operation_type = models.CharField("Операция", max_length=16, choices=WebhookOperationType.choices)
    request_payload = models.JSONField("Запрос", blank=True, null=True)
    response_payload = models.JSONField("Ответ", blank=True, null=True)
    status = models.CharField("Статус", max_length=32)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Операция webhook"
        verbose_name_plural = "Операции webhook"

