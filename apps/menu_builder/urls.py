from django.urls import path

from .views import (
    MenuBranchQualityView,
    MenuNodeCreateView,
    MenuNodeDeleteView,
    MenuNodeDuplicateView,
    MenuNodeMoveView,
    MenuNodeReorderView,
    MenuNodeUpdateView,
    MenuPreviewPartialView,
    MenuPreviewView,
    MenuTreeView,
)

app_name = "menu_builder"

urlpatterns = [
    path("", MenuTreeView.as_view(), name="tree-root"),
    path("quality/", MenuBranchQualityView.as_view(), name="branch-quality-root"),
    path("<int:parent_id>/", MenuTreeView.as_view(), name="tree-child"),
    path("create/", MenuNodeCreateView.as_view(), name="create-root"),
    path("create/<int:parent_id>/", MenuNodeCreateView.as_view(), name="create-child"),
    path("<int:pk>/edit/", MenuNodeUpdateView.as_view(), name="edit"),
    path("<int:pk>/duplicate/", MenuNodeDuplicateView.as_view(), name="duplicate"),
    path("<int:pk>/delete/", MenuNodeDeleteView.as_view(), name="delete"),
    path("<int:pk>/move/<str:direction>/", MenuNodeMoveView.as_view(), name="move"),
    path("reorder/", MenuNodeReorderView.as_view(), name="reorder"),
    path("<int:pk>/preview-panel/", MenuPreviewPartialView.as_view(), name="preview-panel"),
    path("<int:pk>/preview/", MenuPreviewView.as_view(), name="preview"),
    path("<int:pk>/quality/", MenuBranchQualityView.as_view(), name="branch-quality"),
]
