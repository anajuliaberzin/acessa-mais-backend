from django.urls import path

from .views import LocalListView


urlpatterns = [
    path("locais/", LocalListView.as_view(), name="local-list"),
]
