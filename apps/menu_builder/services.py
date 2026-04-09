from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Max, QuerySet

from apps.bot.models import MenuNode, MenuNodeType

MAX_BUTTON_TEXT_LENGTH = 40


@dataclass(slots=True)
class MenuRenderResult:
    node: MenuNode
    text: str
    buttons: list[list[dict[str, str]]]


@dataclass(slots=True)
class MenuQualityCheck:
    level: str
    message: str


@dataclass(slots=True)
class MenuQualityReport:
    checks: list[MenuQualityCheck]

    @property
    def warning_count(self) -> int:
        return len([item for item in self.checks if item.level == "warning"])

    @property
    def info_count(self) -> int:
        return len([item for item in self.checks if item.level == "info"])


@dataclass(slots=True)
class BranchQualityItem:
    node: MenuNode
    checks: list[MenuQualityCheck]


@dataclass(slots=True)
class BranchQualityReport:
    root: MenuNode | None
    items: list[BranchQualityItem]

    @property
    def total_checks(self) -> int:
        return sum(len(item.checks) for item in self.items)


class MenuTreeService:
    @staticmethod
    def root_nodes() -> QuerySet[MenuNode]:
        return MenuNode.objects.filter(parent__isnull=True, is_active=True).order_by("sort_order", "id")

    @staticmethod
    def children(node: MenuNode) -> QuerySet[MenuNode]:
        return node.children.filter(is_active=True).order_by("sort_order", "id")

    @staticmethod
    def move_up(node: MenuNode) -> None:
        sibling = (
            MenuNode.objects.filter(parent=node.parent, sort_order__lt=node.sort_order)
            .order_by("-sort_order")
            .first()
        )
        if sibling:
            node.sort_order, sibling.sort_order = sibling.sort_order, node.sort_order
            node.save(update_fields=["sort_order"])
            sibling.save(update_fields=["sort_order"])

    @staticmethod
    def move_down(node: MenuNode) -> None:
        sibling = (
            MenuNode.objects.filter(parent=node.parent, sort_order__gt=node.sort_order)
            .order_by("sort_order")
            .first()
        )
        if sibling:
            node.sort_order, sibling.sort_order = sibling.sort_order, node.sort_order
            node.save(update_fields=["sort_order"])
            sibling.save(update_fields=["sort_order"])

    @staticmethod
    @transaction.atomic
    def create_node(**data: object) -> MenuNode:
        if not data.get("sort_order"):
            last = (
                MenuNode.objects.filter(parent=data.get("parent"))
                .aggregate(max_sort=Max("sort_order"))
                .get("max_sort")
                or 0
            )
            data["sort_order"] = int(last) + 10
        node = MenuNode.objects.create(**data)
        return node

    @staticmethod
    @transaction.atomic
    def reorder_level(node_ids: list[int], parent_id: int | None) -> None:
        expected_ids = list(
            MenuNode.objects.filter(parent_id=parent_id).order_by("sort_order", "id").values_list("id", flat=True)
        )
        requested_ids = list(node_ids)
        if not requested_ids:
            raise ValueError("Список узлов не может быть пустым")
        if len(requested_ids) != len(set(requested_ids)):
            raise ValueError("Список узлов содержит дубликаты")
        if set(requested_ids) != set(expected_ids):
            raise ValueError("ordered_ids должны совпадать с текущим уровнем меню")

        nodes = list(MenuNode.objects.filter(id__in=requested_ids, parent_id=parent_id))
        node_map = {node.id: node for node in nodes}
        for index, node_id in enumerate(requested_ids):
            node = node_map.get(node_id)
            if node is None:
                continue
            node.sort_order = (index + 1) * 10
            node.save(update_fields=["sort_order"])

    @staticmethod
    @transaction.atomic
    def duplicate_node(node: MenuNode) -> MenuNode:
        siblings = MenuNode.objects.filter(parent=node.parent).order_by("-sort_order")
        last = siblings.first()
        next_sort_order = (int(last.sort_order) if last else 0) + 10

        base_slug = f"{node.slug}-copy"
        slug = base_slug
        suffix = 2
        while MenuNode.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        return MenuNode.objects.create(
            parent=node.parent,
            title=f"{node.title} (копия)",
            slug=slug,
            response_text=node.response_text,
            node_type=node.node_type,
            sort_order=next_sort_order,
            is_active=node.is_active,
            is_visible=node.is_active,
            payload=node.payload,
            icon=node.icon,
            admin_comment=node.admin_comment,
        )


class MenuQualityService:
    def build_report(self, nodes: list[MenuNode]) -> MenuQualityReport:
        checks: list[MenuQualityCheck] = []

        long_titles = [node.title for node in nodes if len((node.title or "").strip()) > MAX_BUTTON_TEXT_LENGTH]
        if long_titles:
            checks.append(
                MenuQualityCheck(
                    level="warning",
                    message=(
                        f"Длинные названия кнопок длиннее {MAX_BUTTON_TEXT_LENGTH} символов: "
                        f"{', '.join(long_titles[:3])}"
                    ),
                )
            )

        empty_responses = [node.title for node in nodes if node.node_type != MenuNodeType.MENU and not node.response_text.strip()]
        if empty_responses:
            checks.append(
                MenuQualityCheck(
                    level="warning",
                    message=f"У некоторых узлов пустой текст ответа: {', '.join(empty_responses[:3])}",
                )
            )

        return MenuQualityReport(checks=checks)

    def build_branch_report(self, root: MenuNode | None) -> BranchQualityReport:
        if root is None:
            nodes = list(MenuNode.objects.order_by("sort_order", "id"))
        else:
            nodes = self._collect_branch_nodes(root)

        items: list[BranchQualityItem] = []
        for node in nodes:
            checks = self._checks_for_node(node)
            if checks:
                items.append(BranchQualityItem(node=node, checks=checks))
        return BranchQualityReport(root=root, items=items)

    def _collect_branch_nodes(self, root: MenuNode) -> list[MenuNode]:
        collected: list[MenuNode] = []

        def walk(node: MenuNode) -> None:
            collected.append(node)
            children = list(node.children.order_by("sort_order", "id"))
            for child in children:
                walk(child)

        walk(root)
        return collected

    def _checks_for_node(self, node: MenuNode) -> list[MenuQualityCheck]:
        checks: list[MenuQualityCheck] = []
        title = (node.title or "").strip()
        if len(title) > MAX_BUTTON_TEXT_LENGTH:
            checks.append(
                MenuQualityCheck(
                    level="warning",
                    message=f"Слишком длинное название кнопки: максимум {MAX_BUTTON_TEXT_LENGTH} символов.",
                )
            )
        if node.node_type != MenuNodeType.MENU and not (node.response_text or "").strip():
            checks.append(MenuQualityCheck(level="warning", message="Пустой текст ответа для выбранного типа узла."))
        if node.node_type == MenuNodeType.LINK:
            payload = node.payload if isinstance(node.payload, dict) else {}
            if not str(payload.get("url") or "").strip():
                checks.append(MenuQualityCheck(level="warning", message='Для типа "Ссылка" не заполнен payload.url.'))
        if node.children.exists() and not node.is_active:
            checks.append(MenuQualityCheck(level="info", message="У узла есть дочерние элементы, но сам узел выключен."))
        return checks


class MenuRuntimeService:
    @staticmethod
    def _button_text(raw: str) -> str:
        return (raw or "").strip()

    def build_keyboard(self, node: MenuNode) -> list[list[dict[str, str]]]:
        children = MenuTreeService.children(node)
        keyboard: list[list[dict[str, str]]] = []
        for child in children:
            display = self._button_text(f"{child.icon} {child.title}".strip())
            keyboard.append([
                {
                    "type": "callback",
                    "text": display,
                    "payload": f"menu:{child.slug}",
                }
            ])
        if node.parent:
            keyboard.append(
                [
                    {"type": "callback", "text": "◀️ Назад", "payload": "nav:back"},
                    {"type": "callback", "text": "🏠 Главное меню", "payload": "nav:root"},
                ]
            )
        return keyboard

    def render_node(self, node: MenuNode) -> MenuRenderResult:
        text = node.response_text or f"Раздел: {node.title}"
        if node.node_type == MenuNodeType.LINK and node.payload and isinstance(node.payload, dict):
            link = node.payload.get("url", "")
            if link:
                text = f"{text}\n{link}"
        return MenuRenderResult(node=node, text=text, buttons=self.build_keyboard(node))

    def resolve_by_payload(self, payload: str) -> MenuNode | None:
        if payload.startswith("menu:"):
            slug = payload.split(":", maxsplit=1)[1]
            return MenuNode.objects.filter(slug=slug, is_active=True).first()
        return None
