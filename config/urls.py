"""Root URL configuration for ACESSA+."""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from locais.cadastro import CadastroView

urlpatterns = [
    path("api/auth/register/", CadastroView.as_view(), name="cadastro"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("locais.urls")),
    path("api/", include("rotas.urls")),
]

# Apenas fotos públicas de locais. Fotos de ocorrências exigem JWT, inclusive em desenvolvimento.
if settings.DEBUG:
    urlpatterns += static('/media/locais/', document_root=settings.MEDIA_ROOT / 'locais')
