from rest_framework import generics

from .models import Local
from .serializers import LocalSerializer


class LocalListView(generics.ListAPIView):
    queryset = Local.objects.all()
    serializer_class = LocalSerializer


class LocalDetailView(generics.RetrieveAPIView):
    queryset = Local.objects.all()
    serializer_class = LocalSerializer
