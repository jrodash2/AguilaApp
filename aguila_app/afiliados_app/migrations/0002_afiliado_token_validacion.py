import uuid

from django.db import migrations, models


def asignar_tokens(apps, schema_editor):
    Afiliado = apps.get_model('afiliados_app', 'Afiliado')
    for afiliado in Afiliado.objects.filter(token_validacion__isnull=True).iterator():
        afiliado.token_validacion = uuid.uuid4()
        afiliado.save(update_fields=['token_validacion'])


class Migration(migrations.Migration):
    dependencies = [
        ('afiliados_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='afiliado',
            name='token_validacion',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(asignar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='afiliado',
            name='token_validacion',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
