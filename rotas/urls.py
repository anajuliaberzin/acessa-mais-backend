from django.urls import path

from .views import CompararRotasView, EnderecosView

urlpatterns = [path("rotas/comparar/", CompararRotasView.as_view(), name="comparar-rotas"),
               path("rotas/enderecos/", EnderecosView.as_view(), name="buscar-enderecos")]
