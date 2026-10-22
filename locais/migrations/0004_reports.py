import django.core.validators
import django.db.models.deletion
import locais.validators
from django.conf import settings
from django.db import migrations, models
import locais.models


class Migration(migrations.Migration):
    dependencies = [("locais", "0003_local_local_somente_sorocaba_sp"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Ocorrencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('protocolo', models.CharField(default=locais.models.gerar_protocolo, editable=False, max_length=35, unique=True)),
                ('endereco', models.CharField(max_length=500)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ('tipo_problema', models.CharField(choices=[('rampa_ausente_ou_inadequada', 'rampa_ausente_ou_inadequada'), ('calcada_em_mau_estado', 'calcada_em_mau_estado'), ('elevador_indisponivel', 'elevador_indisponivel'), ('banheiro_nao_adaptado', 'banheiro_nao_adaptado'), ('vaga_acessivel_indisponivel', 'vaga_acessivel_indisponivel'), ('piso_tatil_ausente_ou_danificado', 'piso_tatil_ausente_ou_danificado'), ('obstaculo_na_via', 'obstaculo_na_via'), ('outro', 'outro')], max_length=60)),
                ('descricao', models.TextField(max_length=5000)),
                ('foto', models.ImageField(blank=True, upload_to='ocorrencias/%Y/%m/')),
                ('status', models.CharField(choices=[('em_analise', 'Em análise'), ('confirmada', 'Confirmada'), ('resolvida', 'Resolvida')], default='em_analise', max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='HistoricoOcorrencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('em_analise', 'Em análise'), ('confirmada', 'Confirmada'), ('resolvida', 'Resolvida')], max_length=15)),
                ('justificativa', models.TextField(max_length=3000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('ocorrencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='locais.ocorrencia')),
            ],
            options={
                'ordering': ['created_at', 'pk'],
            },
        ),
    ]
