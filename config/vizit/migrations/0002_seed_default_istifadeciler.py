import hashlib

from django.db import migrations


def md5(value):
    return hashlib.md5(value.encode('utf-8')).hexdigest()


def seed_istifadeciler(apps, schema_editor):
    Istifadeci = apps.get_model('vizit', 'Istifadeci')
    Region = apps.get_model('regions', 'Region')

    if Istifadeci.objects.exists():
        return

    bolge = Region.objects.filter(pk=2).first() or Region.objects.order_by('pk').first()
    bolge_id = bolge.pk if bolge else None

    defaults = [
        ('Nümayəndə', md5('Solvey2026'), 'Tibbi Nümayəndə', 'numayende', bolge_id),
        ('Menecer', md5('Solvey2024'), 'Menecer', 'menecer', bolge_id),
        ('Rəhbər', md5('Solvey2022'), 'Rəhbər', 'rehber', None),
    ]
    for login, sifre, ad, rol, bolge_id in defaults:
        Istifadeci.objects.create(
            login=login,
            sifre=sifre,
            ad=ad,
            rol=rol,
            bolge_id=bolge_id,
            aktiv=True,
        )


def unseed_istifadeciler(apps, schema_editor):
    Istifadeci = apps.get_model('vizit', 'Istifadeci')
    Istifadeci.objects.filter(
        login__in=['Nümayəndə', 'Menecer', 'Rəhbər'],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vizit', '0001_initial'),
        ('regions', '0004_alter_region_region_type'),
    ]

    operations = [
        migrations.RunPython(seed_istifadeciler, unseed_istifadeciler),
    ]
