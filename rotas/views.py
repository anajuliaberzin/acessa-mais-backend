from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ComparacaoSerializer, CompararRotasSerializer
from .services.accessibility_service import comparar_rotas
from .services.routing_service import RoutingError, buscar_rotas
from .services.geocoding_service import buscar_enderecos
from rest_framework import serializers
from rest_framework.throttling import AnonRateThrottle


class BuscaEnderecoSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=250)


class BuscaEnderecoThrottle(AnonRateThrottle):
    rate = '30/minute'


class EnderecosView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [BuscaEnderecoThrottle]

    def get(self, request):
        entrada = BuscaEnderecoSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        try:
            return Response({'results': buscar_enderecos(entrada.validated_data['q'])})
        except RoutingError as exc:
            return Response({'detail': exc.mensagem}, status=exc.status)


class CompararRotasView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = CompararRotasSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            rotas = buscar_rotas(**entrada.validated_data)
        except RoutingError as exc:
            return Response({"codigo": exc.codigo, "detail": exc.mensagem}, status=exc.status)
        return Response(ComparacaoSerializer(comparar_rotas(rotas)).data)
