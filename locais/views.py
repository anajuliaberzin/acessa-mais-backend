from rest_framework import generics

from .models import Local
from .serializers import LocalSerializer


class LocalListView(generics.ListAPIView):
    queryset = Local.objects.all()
    serializer_class = LocalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        nome = self.request.query_params.get("nome")

        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        return queryset


class LocalDetailView(generics.RetrieveAPIView):
    queryset = Local.objects.all()
    serializer_class = LocalSerializer
