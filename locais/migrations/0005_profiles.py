import django.core.validators
import django.db.models.deletion
import locais.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("locais", "0004_reports"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Perfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(blank=True, max_length=150)),
                ('preferencias', models.JSONField(blank=True, default=list, validators=[locais.validators.validar_preferencias])),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Favorito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('local', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='locais.local')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('usuario', 'local'), name='favorito_unico')],
            },
        ),
    ]
