from datetime import date
from math import isfinite
from django.db import transaction, IntegrityError
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Local, Avaliacao, Perfil, Favorito, Ocorrencia, HistoricoOcorrencia, STATUS, TIPOS_PROBLEMA
from .serializers import LocalSerializer, AvaliacaoSerializer, PerfilSerializer, OcorrenciaSerializer
from .acessibilidade import PESOS, NECESSIDADES, calcular_acessibilidade


class Paginacao(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def locais_publicos():
    return Local.objects.filter(cidade='Sorocaba', estado='SP', localizacao_confirmada=True).annotate(
        media_avaliacoes=Avg('avaliacoes__nota'), total_avaliacoes=Count('avaliacoes')).prefetch_related('fotos')


def filtrar_locais(queryset, params):
    if nome := params.get('nome', '').strip():
        queryset = queryset.filter(nome__icontains=nome)
    if categoria := params.get('categoria', '').strip():
        queryset = queryset.filter(categoria__iexact=categoria)
    recursos = [x for x in params.get('recursos', '').split(',') if x]
    if set(recursos) - set(PESOS):
        raise ValidationError({'recursos': 'Recurso desconhecido.'})
    for recurso in recursos:
        queryset = queryset.filter(**{f'recursos__{recurso}': 'atendido'})
    if necessidade := params.get('necessidade'):
        if necessidade not in NECESSIDADES:
            raise ValidationError({'necessidade': 'Necessidade desconhecida.'})
        condicao = Q()
        for recurso in NECESSIDADES[necessidade]:
            condicao |= Q(**{f'recursos__{recurso}': 'atendido'})
        queryset = queryset.filter(condicao)
    if bbox := params.get('bbox'):
        try:
            oeste, sul, leste, norte = [float(x) for x in bbox.split(',')]
            if not all(isfinite(x) for x in (oeste, sul, leste, norte)) or not (-180 <= oeste <= leste <= 180 and -90 <= sul <= norte <= 90):
                raise ValueError
        except ValueError:
            raise ValidationError({'bbox': 'Use oeste,sul,leste,norte em graus válidos.'})
        queryset = queryset.filter(longitude__range=(oeste, leste), latitude__range=(sul, norte))
    return queryset


class LocalListView(generics.ListAPIView):
    serializer_class = LocalSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = Paginacao

    def get_queryset(self):
        queryset = filtrar_locais(locais_publicos(), self.request.query_params)
        ordem = self.request.query_params.get('ordenacao', 'nome')
        if ordem not in ('nome', 'acessibilidade'):
            raise ValidationError({'ordenacao': 'Use nome ou acessibilidade.'})
        if ordem == 'acessibilidade':
            locais = [local for local in queryset if calcular_acessibilidade(local.recursos)['nota'] is not None]
            return sorted(locais, key=lambda local: (-calcular_acessibilidade(local.recursos)['nota'], local.nome, local.pk))
        return queryset.order_by('nome', 'pk')


class LocalDetailView(generics.RetrieveAPIView):
    serializer_class = LocalSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return locais_publicos()


class FiltrosView(APIView):
    def get(self, request):
        return Response({'categorias': list(Local.objects.filter(cidade='Sorocaba', estado='SP', localizacao_confirmada=True).order_by('categoria').values_list('categoria', flat=True).distinct()),
                         'recursos': list(PESOS), 'necessidades': list(NECESSIDADES)})


class MapaView(generics.ListAPIView):
    serializer_class = LocalSerializer
    pagination_class = Paginacao

    def get_queryset(self):
        return filtrar_locais(locais_publicos().exclude(latitude=None).exclude(longitude=None), self.request.query_params).order_by('pk')


class AvaliacoesView(generics.ListCreateAPIView):
    serializer_class = AvaliacaoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = Paginacao

    def get_queryset(self):
        local = get_object_or_404(locais_publicos(), pk=self.kwargs['pk'])
        return Avaliacao.objects.filter(local=local).select_related('local')

    def perform_create(self, serializer):
        local = get_object_or_404(locais_publicos(), pk=self.kwargs['pk'])
        try:
            with transaction.atomic():
                serializer.save(autor=self.request.user, local=local)
        except IntegrityError:
            raise ValidationError('Você já avaliou este local.')


class MinhaAvaliacaoView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvaliacaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Avaliacao.objects.filter(autor=self.request.user).select_related('local')


class PerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = PerfilSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        perfil, _ = Perfil.objects.get_or_create(usuario=self.request.user, defaults={'nome': self.request.user.get_full_name() or self.request.user.username})
        return perfil


class MinhasAvaliacoesView(generics.ListAPIView):
    serializer_class = AvaliacaoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = Paginacao

    def get_queryset(self):
        return Avaliacao.objects.filter(autor=self.request.user).select_related('local')


class FavoritosView(generics.ListAPIView):
    serializer_class = LocalSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = Paginacao

    def get_queryset(self):
        return locais_publicos().filter(pk__in=Favorito.objects.filter(usuario=self.request.user).values('local_id')).order_by('nome', 'pk')


class FavoritoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        local = get_object_or_404(locais_publicos(), pk=pk)
        _, criado = Favorito.objects.get_or_create(usuario=request.user, local=local)
        return Response(status=201 if criado else 200)

    def delete(self, request, pk):
        Favorito.objects.filter(usuario=request.user, local_id=pk).delete()
        return Response(status=204)


class ContribuicoesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'avaliacoes': Avaliacao.objects.filter(autor=request.user).count(),
                         'ocorrencias': Ocorrencia.objects.filter(autor=request.user).count(),
                         'favoritos': Favorito.objects.filter(usuario=request.user, local__localizacao_confirmada=True).count()})


class OcorrenciasView(generics.ListCreateAPIView):
    serializer_class = OcorrenciaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = Paginacao
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Ocorrencia.objects.filter(autor=self.request.user).prefetch_related('historico')

    @transaction.atomic
    def perform_create(self, serializer):
        ocorrencia = serializer.save(autor=self.request.user)
        HistoricoOcorrencia.objects.create(ocorrencia=ocorrencia, responsavel=self.request.user,
                                          status='em_analise', justificativa='Ocorrência recebida para análise.')


class OcorrenciaView(generics.RetrieveAPIView):
    serializer_class = OcorrenciaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ocorrencia.objects.filter(autor=self.request.user).prefetch_related('historico')


class FotoOcorrenciaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        queryset = Ocorrencia.objects.all() if request.user.is_staff else Ocorrencia.objects.filter(autor=request.user)
        ocorrencia = get_object_or_404(queryset.exclude(foto=''), pk=pk)
        return FileResponse(ocorrencia.foto.open('rb'))
