import django.core.validators
import django.db.models.deletion
import locais.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("locais", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(
            model_name='local',
            name='cidade',
            field=models.CharField(choices=[('Sorocaba', 'Sorocaba')], default='Sorocaba', max_length=40),
        ),
        migrations.AddField(
            model_name='local',
            name='estado',
            field=models.CharField(choices=[('SP', 'SP')], default='SP', max_length=2),
        ),
        migrations.AddField(
            model_name='local',
            name='localizacao_confirmada',
            field=models.BooleanField(default=False, help_text='Confirme que o endereço pertence a Sorocaba/SP.'),
        ),
        migrations.AddField(
            model_name='local',
            name='recursos',
            field=models.JSONField(blank=True, default=dict, validators=[locais.validators.validar_recursos]),
        ),
        migrations.CreateModel(
            name='FotoLocal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto', models.ImageField(upload_to='locais/%Y/%m/')),
                ('legenda', models.CharField(blank=True, max_length=200)),
                ('local', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fotos', to='locais.local')),
            ],
        ),
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(max_length=3000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('local', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to='locais.local')),
            ],
            options={
                'ordering': ['-created_at', '-pk'],
                'constraints': [models.UniqueConstraint(fields=('local', 'autor'), name='avaliacao_unica_por_autor')],
            },
        ),
    ]
