from django.urls import path

from .views import LocalDetailView, LocalListView
from . import views


urlpatterns = [
    path('locais/filtros/', views.FiltrosView.as_view()),
    path('locais/mapa/', views.MapaView.as_view()),
    path('locais/<int:pk>/avaliacoes/', views.AvaliacoesView.as_view()),
    path('ocorrencias/', views.OcorrenciasView.as_view()),
    path('ocorrencias/<int:pk>/', views.OcorrenciaView.as_view()),
    path('ocorrencias/<int:pk>/foto/', views.FotoOcorrenciaView.as_view()),
    path("locais/", LocalListView.as_view(), name="local-list"),
    path("locais/<int:pk>/", LocalDetailView.as_view(), name="local-detail"),
]
