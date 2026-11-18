from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Local, FotoLocal, Avaliacao, Perfil, Ocorrencia, HistoricoOcorrencia
from .acessibilidade import calcular_acessibilidade


class CadastroSerializer(serializers.Serializer):
    nome = serializers.CharField(min_length=2, max_length=150)
    username = serializers.CharField(
        max_length=150,
        validators=[UniqueValidator(queryset=get_user_model().objects.all())],
    )
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({'password_confirmation': 'As senhas não conferem.'})

        user_model = get_user_model()
        user = user_model(username=attrs['username'], email=attrs['email'])
        try:
            validate_password(attrs['password'], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': error.messages}) from error
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_model = get_user_model()
        usuario = user_model.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        Perfil.objects.create(usuario=usuario, nome=validated_data['nome'])
        return usuario


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


class CriarLocalSerializer(serializers.ModelSerializer):
    localizacao_confirmada = serializers.BooleanField(required=True)
    latitude = serializers.DecimalField(max_digits=8, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)

    class Meta:
        model = Local
        fields = ('nome', 'categoria', 'endereco', 'descricao', 'cidade', 'estado',
                  'latitude', 'longitude', 'localizacao_confirmada', 'recursos')

    def validate_categoria(self, value):
        return value.strip().casefold()

    def validate_localizacao_confirmada(self, value):
        if not value:
            raise serializers.ValidationError('Confirme que o local pertence a Sorocaba/SP.')
        return value


class AvaliacaoSerializer(serializers.ModelSerializer):
    nomeLocal = serializers.CharField(source='local.nome', read_only=True)
    comentario = serializers.CharField(required=False, allow_blank=True, max_length=3000)

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
    superadmin = serializers.BooleanField(source='usuario.is_superuser', read_only=True)

    def get_cidade(self, obj):
        return 'Sorocaba'

    def get_uf(self, obj):
        return 'SP'

    class Meta:
        model = Perfil
        fields = ('id', 'nome', 'cidade', 'uf', 'membroDesde', 'preferencias', 'gestor', 'superadmin')


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


class AlterarStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ocorrencia._meta.get_field('status').choices)
    justificativa = serializers.CharField(min_length=5, max_length=3000)
