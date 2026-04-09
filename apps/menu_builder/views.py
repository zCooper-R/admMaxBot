from __future__ import annotations

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import EditorRequiredMixin, ViewerRequiredMixin
from apps.audit.services import audit_action
from apps.bot.models import MenuNode
from apps.core.http import parse_json_request

from .forms import EDITOR_NODE_TYPE_CHOICES, MenuNodeForm
from .services import MenuQualityService, MenuRuntimeService, MenuTreeService


def _build_breadcrumbs(node: MenuNode | None) -> list[MenuNode]:
    if node is None:
        return []
    items: list[MenuNode] = []
    cursor = node
    while cursor is not None:
        items.append(cursor)
        cursor = cursor.parent
    items.reverse()
    return items


class MenuTreeView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest, parent_id: int | None = None) -> HttpResponse:
        parent = None
        query = request.GET.get("q", "").strip()
        node_type = request.GET.get("node_type", "").strip()
        status = request.GET.get("status", "").strip()
        if parent_id:
            parent = get_object_or_404(MenuNode, pk=parent_id)
            nodes = parent.children.all()
        else:
            nodes = MenuNode.objects.filter(parent__isnull=True)

        if query:
            nodes = nodes.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        if node_type:
            nodes = nodes.filter(node_type=node_type)
        if status == "active":
            nodes = nodes.filter(is_active=True)
        elif status == "inactive":
            nodes = nodes.filter(is_active=False)

        nodes = nodes.annotate(child_count=Count("children")).order_by("sort_order", "id")
        node_list = list(nodes)
        first_node = node_list[0] if node_list else None
        first_preview = MenuRuntimeService().render_node(first_node) if first_node else None
        return render(
            request,
            "menu_builder/tree.html",
            {
                "nodes": node_list,
                "parent": parent,
                "breadcrumbs": _build_breadcrumbs(parent),
                "initial_preview_node": first_node,
                "initial_preview": first_preview,
                "quality_report": MenuQualityService().build_report(node_list),
                "filter_q": query,
                "filter_node_type": node_type,
                "filter_status": status,
                "node_type_choices": EDITOR_NODE_TYPE_CHOICES,
            },
        )


class MenuNodeCreateView(EditorRequiredMixin, View):
    def get(self, request: HttpRequest, parent_id: int | None = None) -> HttpResponse:
        parent = MenuNode.objects.filter(pk=parent_id).first() if parent_id else None
        form = MenuNodeForm(initial={"parent": parent})
        return render(request, "menu_builder/form.html", {"form": form, "title": "Создать узел"})

    def post(self, request: HttpRequest, parent_id: int | None = None) -> HttpResponse:
        form = MenuNodeForm(request.POST)
        if form.is_valid():
            node = form.save()
            audit_action(request.user, "create", "MenuNode", str(node.id), None, form.cleaned_data)
            messages.success(request, "Узел успешно создан")
            if node.parent_id:
                return redirect("menu_builder:tree-child", parent_id=node.parent_id)
            return redirect("menu_builder:tree-root")
        return render(request, "menu_builder/form.html", {"form": form, "title": "Создать узел"})


class MenuNodeUpdateView(EditorRequiredMixin, View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        form = MenuNodeForm(instance=node)
        return render(request, "menu_builder/form.html", {"form": form, "title": "Редактировать узел", "node": node})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        before = {
            "title": node.title,
            "slug": node.slug,
            "node_type": node.node_type,
            "parent_id": node.parent_id,
            "is_active": node.is_active,
        }
        form = MenuNodeForm(request.POST, instance=node)
        if form.is_valid():
            saved = form.save()
            audit_action(request.user, "update", "MenuNode", str(saved.id), before, form.cleaned_data)
            messages.success(request, "Изменения сохранены")
            if saved.parent_id:
                return redirect("menu_builder:tree-child", parent_id=saved.parent_id)
            return redirect("menu_builder:tree-root")
        return render(request, "menu_builder/form.html", {"form": form, "title": "Редактировать узел", "node": node})


class MenuNodeDeleteView(EditorRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        parent_id = node.parent_id
        if node.children.exists():
            messages.error(request, "Нельзя удалить узел, у которого есть дочерние элементы")
            if parent_id:
                return redirect("menu_builder:tree-child", parent_id=parent_id)
            return redirect("menu_builder:tree-root")
        before = {"title": node.title, "slug": node.slug}
        node.delete()
        audit_action(request.user, "delete", "MenuNode", str(pk), before, None)
        messages.success(request, "Узел удален")
        if parent_id:
            return redirect("menu_builder:tree-child", parent_id=parent_id)
        return redirect("menu_builder:tree-root")


class MenuNodeMoveView(EditorRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int, direction: str) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        if direction == "up":
            MenuTreeService.move_up(node)
        elif direction == "down":
            MenuTreeService.move_down(node)
        messages.success(request, "Порядок обновлен")
        if node.parent_id:
            return redirect("menu_builder:tree-child", parent_id=node.parent_id)
        return redirect("menu_builder:tree-root")


class MenuNodeDuplicateView(EditorRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        duplicated = MenuTreeService.duplicate_node(node)
        audit_action(
            request.user,
            "duplicate",
            "MenuNode",
            str(duplicated.id),
            {"source_id": node.id, "source_slug": node.slug},
            {"title": duplicated.title, "slug": duplicated.slug},
        )
        messages.success(request, "Узел успешно продублирован")
        if duplicated.parent_id:
            return redirect("menu_builder:tree-child", parent_id=duplicated.parent_id)
        return redirect("menu_builder:tree-root")


class MenuPreviewView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        preview = MenuRuntimeService().render_node(node)
        return render(
            request,
            "menu_builder/preview.html",
            {
                "node": node,
                "preview": preview,
                "breadcrumbs": _build_breadcrumbs(node),
            },
        )


class MenuPreviewPartialView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        node = get_object_or_404(MenuNode, pk=pk)
        preview = MenuRuntimeService().render_node(node)
        return render(
            request,
            "menu_builder/_preview_panel.html",
            {
                "node": node,
                "preview": preview,
            },
        )


class MenuNodeReorderView(EditorRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        payload, error = parse_json_request(request)
        if error is not None:
            return JsonResponse({"ok": False, "error": "Невалидный payload"}, status=400)

        try:
            ordered_ids = [int(item) for item in payload.get("ordered_ids", [])]
            raw_parent_id = payload.get("parent_id")
            parent_id = int(raw_parent_id) if raw_parent_id is not None else None
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Невалидный payload"}, status=400)

        if not ordered_ids:
            return JsonResponse({"ok": False, "error": "Список узлов пуст"}, status=400)

        try:
            MenuTreeService.reorder_level(ordered_ids, parent_id)
        except ValueError:
            return JsonResponse({"ok": False, "error": "Невалидный payload"}, status=400)
        audit_action(
            request.user,
            "reorder",
            "MenuNodeLevel",
            str(parent_id) if parent_id is not None else "root",
            None,
            {"ordered_ids": ordered_ids, "parent_id": parent_id},
        )
        return JsonResponse({"ok": True})


class MenuBranchQualityView(ViewerRequiredMixin, View):
    def get(self, request: HttpRequest, pk: int | None = None) -> HttpResponse:
        root = get_object_or_404(MenuNode, pk=pk) if pk is not None else None
        report = MenuQualityService().build_branch_report(root)
        return render(
            request,
            "menu_builder/branch_quality.html",
            {
                "root_node": root,
                "report": report,
                "breadcrumbs": _build_breadcrumbs(root),
            },
        )
