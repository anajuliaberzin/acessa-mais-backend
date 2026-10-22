from rest_framework import serializers
from .models import Local, FotoLocal, Avaliacao
from .acessibilidade import calcular_acessibilidade


class FotoLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoLocal
        fields = ('id', 'foto', 'legenda')


class LocalSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=8, decimal_places=6, allow_null=True, coerce_to_string=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True, coerce_to_string=False)
    acessibilidade = serializers.SerializerMethodField()
    fotos = FotoLocalSerializer(many=True, read_only=True)
    media_avaliacoes = serializers.FloatField(read_only=True, allow_null=True)
    total_avaliacoes = serializers.IntegerField(read_only=True)

    def get_acessibilidade(self, obj):
        return calcular_acessibilidade(obj.recursos)

    class Meta:
        model = Local
        fields = ('id', 'nome', 'categoria', 'endereco', 'descricao', 'latitude', 'longitude',
                  'cidade', 'estado', 'recursos', 'acessibilidade', 'fotos', 'media_avaliacoes',
                  'total_avaliacoes', 'created_at', 'updated_at')
        read_only_fields = fields


class AvaliacaoSerializer(serializers.ModelSerializer):
    nomeLocal = serializers.CharField(source='local.nome', read_only=True)

    class Meta:
        model = Avaliacao
        fields = ('id', 'local', 'nomeLocal', 'nota', 'comentario', 'created_at')
        read_only_fields = ('id', 'local', 'created_at')
