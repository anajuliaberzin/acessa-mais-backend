from django.contrib import admin

from .models import Local


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "endereco", "latitude", "longitude")
    search_fields = ("nome", "categoria", "endereco")
