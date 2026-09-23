from django.db import migrations, models

import afiliados_app.models


class Migration(migrations.Migration):
    dependencies = [
        ('afiliados_app', '0022_coberturavisitaplanhormiga_coordinadorplanhormiga_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FotoPersona',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dpi', models.CharField(db_index=True, max_length=13, unique=True)),
                ('foto', models.ImageField(upload_to=afiliados_app.models.foto_persona_upload_to)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='afiliado',
            name='foto',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=afiliados_app.models.foto_persona_upload_to,
            ),
        ),
    ]
