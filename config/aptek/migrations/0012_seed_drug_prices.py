from django.db import migrations


def forwards(apps, schema_editor):
    from aptek.price_seed import seed_drug_prices
    seed_drug_prices()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0011_drugprice_extra_fields'),
        ('medicine', '0004_medical_position'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
