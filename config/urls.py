"""Root URL configuration for ACESSA+."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("locais.urls")),
]
