# Generated manually for depo FK

import django.db.models.deletion
from django.db import migrations, models


def create_default_depo(apps, schema_editor):
    Depo = apps.get_model("depo_sales", "Depo")
    Depo.objects.get_or_create(id=1, defaults={"name": "Default"})


class Migration(migrations.Migration):

    dependencies = [
        ("depo_sales", "0002_depo"),
    ]

    operations = [
        migrations.RunPython(create_default_depo, migrations.RunPython.noop),
        migrations.AddField(
            model_name="uploadedreport",
            name="depo",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reports",
                to="depo_sales.depo",
                verbose_name="Depo",
            ),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name="uploadedreport",
            name="title",
        ),
        migrations.AlterModelOptions(
            name="depo",
            options={
                "ordering": ["name"],
                "verbose_name": "Depo",
                "verbose_name_plural": "Depolar",
            },
        ),
    ]
