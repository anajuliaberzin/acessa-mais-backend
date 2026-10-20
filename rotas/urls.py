from django.urls import path

from .views import CompararRotasView

urlpatterns = [path("rotas/comparar/", CompararRotasView.as_view(), name="comparar-rotas")]
