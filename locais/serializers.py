from rest_framework import serializers
from .models import Local, FotoLocal, Avaliacao, Perfil, Ocorrencia, HistoricoOcorrencia
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


class PerfilSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='usuario_id', read_only=True)
    cidade = serializers.SerializerMethodField()
    uf = serializers.SerializerMethodField()
    membroDesde = serializers.DateTimeField(source='usuario.date_joined', read_only=True)
    gestor = serializers.BooleanField(source='usuario.is_staff', read_only=True)

    def get_cidade(self, obj):
        return 'Sorocaba'

    def get_uf(self, obj):
        return 'SP'

    class Meta:
        model = Perfil
        fields = ('id', 'nome', 'cidade', 'uf', 'membroDesde', 'preferencias', 'gestor')


class HistoricoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoOcorrencia
        fields = ('id', 'status', 'justificativa', 'created_at')


class OcorrenciaSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=8, decimal_places=6, min_value=-90, max_value=90, required=False, allow_null=True, coerce_to_string=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180, required=False, allow_null=True, coerce_to_string=False)
    tipoProblema = serializers.ChoiceField(source='tipo_problema', choices=Ocorrencia._meta.get_field('tipo_problema').choices)
    dataCriacao = serializers.DateTimeField(source='created_at', read_only=True)
    foto = serializers.ImageField(write_only=True, required=False)
    fotoUrl = serializers.SerializerMethodField()
    historico = HistoricoSerializer(many=True, read_only=True)
    endereco = serializers.CharField(min_length=5, max_length=500)
    descricao = serializers.CharField(min_length=10, max_length=5000)
    confirmadoSorocaba = serializers.BooleanField(write_only=True, required=True)

    def get_fotoUrl(self, obj):
        return f'/api/ocorrencias/{obj.pk}/foto/' if obj.foto else None

    def validate_foto(self, foto):
        if foto.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('A foto deve ter no máximo 5 MB.')
        if foto.image.format not in ('JPEG', 'PNG', 'WEBP'):
            raise serializers.ValidationError('Envie uma imagem JPEG, PNG ou WebP.')
        return foto

    def validate(self, attrs):
        if not attrs.pop('confirmadoSorocaba', False):
            raise serializers.ValidationError({'confirmadoSorocaba': 'Confirme que o endereço pertence a Sorocaba/SP.'})
        if (attrs.get('latitude') is None) != (attrs.get('longitude') is None):
            raise serializers.ValidationError('Informe as duas coordenadas ou nenhuma.')
        return attrs

    class Meta:
        model = Ocorrencia
        fields = ('id', 'protocolo', 'endereco', 'latitude', 'longitude', 'tipoProblema', 'descricao',
                  'foto', 'fotoUrl', 'status', 'dataCriacao', 'historico', 'confirmadoSorocaba')
        read_only_fields = ('id', 'protocolo', 'status')
