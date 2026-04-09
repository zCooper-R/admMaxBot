import json

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.utils.text import slugify

from apps.bot.models import MenuNode, MenuNodeType

RU_TO_LAT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

EDITOR_NODE_TYPE_CHOICES = [
    (MenuNodeType.MENU, "Меню"),
    (MenuNodeType.MESSAGE, "Сообщение"),
    (MenuNodeType.LINK, "Ссылка"),
]
EDITOR_NODE_TYPE_VALUES = {value for value, _ in EDITOR_NODE_TYPE_CHOICES}


def translit_slug(value: str) -> str:
    lowered = value.lower().translate(RU_TO_LAT)
    return slugify(lowered, allow_unicode=False)


class MenuNodeForm(forms.ModelForm):
    slug = forms.CharField(required=False)
    payload = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    class Meta:
        model = MenuNode
        fields = [
            "parent",
            "title",
            "slug",
            "response_text",
            "node_type",
            "sort_order",
            "is_active",
            "payload",
            "icon",
            "admin_comment",
        ]
        widgets = {
            "response_text": forms.Textarea(attrs={"rows": 4}),
            "admin_comment": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["node_type"].choices = self._node_type_choices()
        self.fields["slug"].required = False
        self.fields["slug"].help_text = "Если оставить пустым, slug заполнится автоматически. Пробелы заменяются на дефисы."
        self.fields["node_type"].help_text = "В конструкторе доступны только три рабочих типа: меню, сообщение и ссылка."
        self.fields["payload"].help_text = (
            'JSON для служебных данных. Для типа "Ссылка" укажите, например: {"url": "https://example.com"}'
        )
        self.fields["sort_order"].help_text = "Чем меньше число, тем выше кнопка в списке."
        self.fields["is_active"].help_text = "Один переключатель для доступности узла и показа кнопки в меню."
        self.fields["payload"].widget.attrs["placeholder"] = '{"url": "https://example.com"}'
        self.fields["payload"].initial = self._format_payload_initial()
        if not self.instance or not self.instance.pk:
            self.fields["sort_order"].initial = 0

    def clean_node_type(self) -> str:
        node_type = self.cleaned_data.get("node_type")
        if node_type not in EDITOR_NODE_TYPE_VALUES:
            raise forms.ValidationError("Сейчас в конструкторе доступны только типы: меню, сообщение и ссылка.")
        return node_type

    def clean_slug(self) -> str:
        incoming = (self.cleaned_data.get("slug") or "").strip()
        title = (self.cleaned_data.get("title") or "").strip()
        base = translit_slug(incoming) if incoming else translit_slug(title) or "node"

        slug = base
        suffix = 2
        queryset = MenuNode.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        while queryset.exists():
            slug = f"{base}-{suffix}"
            suffix += 1
            queryset = MenuNode.objects.filter(slug=slug)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
        return slug

    def clean_sort_order(self) -> int:
        incoming = self.cleaned_data.get("sort_order")
        if self.instance and self.instance.pk:
            return int(incoming or self.instance.sort_order or 100)
        if incoming and int(incoming) > 0:
            return int(incoming)
        parent = self.cleaned_data.get("parent")
        siblings = MenuNode.objects.filter(parent=parent).order_by("-sort_order")
        last = siblings.first()
        last_sort = int(last.sort_order) if last else 0
        return last_sort + 10

    def clean_payload(self):
        raw_payload = (self.cleaned_data.get("payload") or "").strip()
        node_type = self.cleaned_data.get("node_type")

        if not raw_payload:
            if node_type == MenuNodeType.LINK:
                raise forms.ValidationError('Для типа "Ссылка" заполните payload c полем "url".')
            return None

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Payload должен быть валидным JSON: {exc.msg}.") from exc

        if not isinstance(payload, dict):
            raise forms.ValidationError("Payload должен быть JSON-объектом вида { ... }.")

        if node_type == MenuNodeType.LINK:
            url = str(payload.get("url") or "").strip()
            if not url:
                raise forms.ValidationError('Для типа "Ссылка" в payload обязательно поле "url".')
            validator = URLValidator(schemes=["http", "https"])
            try:
                validator(url)
            except DjangoValidationError as exc:
                raise forms.ValidationError("Поле url в payload должно содержать корректный http/https URL.") from exc

        return payload

    def clean(self):
        cleaned_data = super().clean()
        node_type = cleaned_data.get("node_type")
        response_text = str(cleaned_data.get("response_text") or "").strip()

        if node_type == MenuNodeType.MESSAGE and not response_text:
            self.add_error("response_text", "Для типа «Сообщение» заполните текст ответа.")

        return cleaned_data

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        instance.is_visible = instance.is_active
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def _format_payload_initial(self) -> str:
        payload = getattr(self.instance, "payload", None)
        if not payload:
            return ""
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except TypeError:
            return ""

    def _node_type_choices(self) -> list[tuple[str, str]]:
        choices = list(EDITOR_NODE_TYPE_CHOICES)
        current_type = getattr(self.instance, "node_type", "")
        if current_type and current_type not in EDITOR_NODE_TYPE_VALUES:
            choices.append((current_type, f"{self.instance.get_node_type_display()} (устаревший тип)"))
        return choices
