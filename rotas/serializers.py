import math

from rest_framework import serializers


class CoordenadaField(serializers.FloatField):
    def to_internal_value(self, data):
        try:
            valido = type(data) in (int, float) and math.isfinite(data)
        except OverflowError:
            valido = False
        if not valido:
            raise serializers.ValidationError("Informe uma coordenada numérica finita.")
        return super().to_internal_value(data)


class PontoSerializer(serializers.Serializer):
    latitude = CoordenadaField(min_value=-90, max_value=90)
    longitude = CoordenadaField(min_value=-180, max_value=180)


class CompararRotasSerializer(serializers.Serializer):
    origem = PontoSerializer()
    destino = PontoSerializer()


class BarreiraSerializer(serializers.Serializer):
    tipo = serializers.CharField()
    descricao = serializers.CharField()
    trecho = serializers.ListField(child=serializers.IntegerField())


class RotaSerializer(serializers.Serializer):
    tempo_minutos = serializers.FloatField()
    distancia_metros = serializers.FloatField()
    geometria = serializers.JSONField()
    score_acessibilidade = serializers.FloatField(allow_null=True)
    barreiras = BarreiraSerializer(many=True)
    acessibilidade_avaliada = serializers.BooleanField()
    nivel_confianca = serializers.CharField()


class ComparacaoSerializer(serializers.Serializer):
    rota_rapida = RotaSerializer()
    rota_acessivel = RotaSerializer(allow_null=True)
    alternativas = RotaSerializer(many=True)
    acessibilidade_avaliada = serializers.BooleanField()
    nivel_confianca = serializers.CharField()
    mensagem = serializers.CharField()
