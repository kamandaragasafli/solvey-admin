from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0006_qaime_doc_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anbarhereket',
            name='qaime',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='hereketler',
                to='aptek.qaime',
            ),
        ),
    ]
