from decimal import Decimal

from django.db import migrations


MISSING_DATA = [
    ('Vitomer Kids 150 ml', Decimal('5'), Decimal('3'), Decimal('8'), Decimal('0')),
    ('Moksivista 100ml', Decimal('30'), Decimal('0'), Decimal('0'), Decimal('30')),
    ('Peynstop N10 şase', Decimal('27'), Decimal('15'), Decimal('13'), Decimal('29')),
]

NAME_ALIASES = {
    'Vitomer Kids 150 ml': 'Vitomer Kids',
    'Moksivista 100ml': 'Moxivista',
    'Peynstop N10 şase': 'Painstop',
}


def _find_drug(Medical, label):
    alias = NAME_ALIASES.get(label, label)
    drug = Medical.objects.filter(med_full_name=alias).first()
    if drug:
        return drug
    drug = Medical.objects.filter(med_name__iexact=alias).first()
    if drug:
        return drug
    base = label.split()[0]
    return Medical.objects.filter(med_name__iexact=base).first()


def add_missing_movements(apps, schema_editor):
    Medical = apps.get_model('medicine', 'Medical')
    AnbarHereket = apps.get_model('aptek', 'AnbarHereket')
    Qaime = apps.get_model('aptek', 'Qaime')
    Aptek = apps.get_model('aptek', 'Aptek')

    qaime = Qaime.objects.first()
    default_aptek = Aptek.objects.first()
    if not qaime or not default_aptek:
        return

    for label, evvel, gelen, cixan, _qalan in MISSING_DATA:
        drug = _find_drug(Medical, label)
        if not drug or AnbarHereket.objects.filter(drug=drug).exists():
            continue

        if evvel > 0:
            AnbarHereket.objects.create(
                drug=drug,
                movement_type='in',
                quantity=evvel,
                date='2026-05-31',
                note='Əvvələ qalıq',
            )

        if gelen > 0:
            AnbarHereket.objects.create(
                drug=drug,
                movement_type='in',
                quantity=gelen,
                date='2026-06-15',
                note='İyun girişi',
            )

        if cixan > 0:
            AnbarHereket.objects.create(
                drug=drug,
                movement_type='out',
                quantity=cixan,
                date='2026-06-20',
                aptek=default_aptek,
                qaime=qaime,
                note='İyun çıxışı',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0002_seed_june_ledger'),
    ]

    operations = [
        migrations.RunPython(add_missing_movements, migrations.RunPython.noop),
    ]
