from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ComparacaoSerializer, CompararRotasSerializer
from .services.accessibility_service import comparar_rotas
from .services.routing_service import RoutingError, buscar_rotas


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
