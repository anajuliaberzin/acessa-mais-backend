from django.contrib import admin

from .models import Local
from .models import FotoLocal, Avaliacao, Perfil
from .acessibilidade import PESOS, ESTADOS
from django import forms


class LocalForm(forms.ModelForm):
    rampa = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])
    banheiro_adaptado = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])
    vaga_acessivel = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])
    elevador = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])
    piso_tatil = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])
    recurso_auditivo = forms.ChoiceField(choices=[(estado, estado) for estado in ESTADOS])

    class Meta:
        model = Local
        exclude = ('recursos',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in PESOS:
            self.fields[nome] = forms.ChoiceField(
                label='Rampa ou acesso sem degrau' if nome == 'rampa' else nome.replace('_', ' ').capitalize(),
                choices=[(estado, estado.replace('_', ' ').capitalize()) for estado in ESTADOS],
                initial=self.instance.recursos.get(nome, 'nao_informado'))

    def clean_categoria(self):
        return self.cleaned_data['categoria'].strip().casefold()

    def save(self, commit=True):
        self.instance.recursos = {nome: self.cleaned_data[nome] for nome in PESOS}
        return super().save(commit)


class FotoInline(admin.TabularInline):
    model = FotoLocal
    extra = 0


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    form = LocalForm
    inlines = [FotoInline]
    list_filter = ('localizacao_confirmada', 'categoria')
    list_display = ("nome", "categoria", "endereco", "latitude", "longitude")
    search_fields = ("nome", "categoria", "endereco")


admin.site.register(Avaliacao)
admin.site.register(Perfil)
