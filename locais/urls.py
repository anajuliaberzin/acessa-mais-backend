from django.urls import path

from .views import LocalDetailView, LocalListView


urlpatterns = [
    path("locais/", LocalListView.as_view(), name="local-list"),
    path("locais/<int:pk>/", LocalDetailView.as_view(), name="local-detail"),
]
