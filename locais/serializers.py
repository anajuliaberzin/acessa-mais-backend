from rest_framework import serializers

from .models import Local


class LocalSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        max_digits=8,
        decimal_places=6,
        allow_null=True,
        coerce_to_string=False,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        coerce_to_string=False,
    )

    class Meta:
        model = Local
        fields = (
            "id",
            "nome",
            "categoria",
            "endereco",
            "descricao",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
