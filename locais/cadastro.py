"""Cadastro público de cidadãos usando a autenticação existente."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from .models import Perfil


class CadastroSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(min_length=2, max_length=150, write_only=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = get_user_model()
        fields = ('id', 'nome', 'username', 'email', 'password', 'password_confirmation')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({'password_confirmation': 'As senhas não coincidem.'})
        usuario = get_user_model()(username=attrs['username'], email=attrs['email'], first_name=attrs['nome'])
        try:
            validate_password(attrs['password'], usuario)
        except ValidationError as erro:
            raise serializers.ValidationError({'password': erro.messages}) from erro
        return attrs

    def create(self, validated_data):
        nome = validated_data.pop('nome')
        validated_data.pop('password_confirmation')
        try:
            with transaction.atomic():
                usuario = get_user_model().objects.create_user(**validated_data, first_name=nome)
                Perfil.objects.create(usuario=usuario, nome=nome)
        except IntegrityError as erro:
            raise serializers.ValidationError({'username': 'Este nome de usuário já está em uso.'}) from erro
        return usuario


class CadastroThrottle(AnonRateThrottle):
    rate = '10/hour'


class CadastroView(generics.CreateAPIView):
    serializer_class = CadastroSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CadastroThrottle]
