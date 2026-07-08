from decimal import Decimal

from django.db import migrations


JUNE_DATA = [
    ('Betasol N30 kapsul', Decimal('0'), Decimal('2'), Decimal('2'), Decimal('0')),
    ('Serrasol N30 kapsul', Decimal('4'), Decimal('53'), Decimal('33.3'), Decimal('23.7')),
    ('Genosfer N30 tablet', Decimal('4'), Decimal('1'), Decimal('5'), Decimal('0')),
    ('Kalvey N30 tablet', Decimal('0'), Decimal('6'), Decimal('6'), Decimal('0')),
    ('Soltep N30', Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')),
    ('Soltrop N30', Decimal('24'), Decimal('16'), Decimal('17.3'), Decimal('22.7')),
    ('Solseda N30', Decimal('16'), Decimal('17.3'), Decimal('5'), Decimal('28.3')),
    ('Litasol N30', Decimal('15'), Decimal('25'), Decimal('11'), Decimal('29')),
    ('Vitomer D3 15ml', Decimal('30'), Decimal('1'), Decimal('0'), Decimal('31')),
    ('Opeblock N5 amp', Decimal('17'), Decimal('0'), Decimal('5'), Decimal('12')),
    ('Levostrong 100ml', Decimal('61'), Decimal('35'), Decimal('40'), Decimal('56')),
    ('Fensavin 150 ml', Decimal('6'), Decimal('7'), Decimal('2'), Decimal('11')),
    ('Vitomer Kids 150 ml', Decimal('5'), Decimal('3'), Decimal('8'), Decimal('0')),
    ('Ropsol', Decimal('16'), Decimal('2'), Decimal('6'), Decimal('12')),
    ('Opsidol N30', Decimal('3'), Decimal('1'), Decimal('4'), Decimal('0')),
    ('Zemovar N30', Decimal('9'), Decimal('15'), Decimal('9'), Decimal('15')),
    ('Kartovey N30', Decimal('10'), Decimal('11'), Decimal('21'), Decimal('0')),
    ('Fesola 150 ml', Decimal('4'), Decimal('3'), Decimal('7'), Decimal('0')),
    ('Moksivista 100ml', Decimal('30'), Decimal('0'), Decimal('0'), Decimal('30')),
    ('Peynstop N10 şase', Decimal('27'), Decimal('15'), Decimal('13'), Decimal('29')),
    ('Lipomaq+', Decimal('0'), Decimal('18'), Decimal('18'), Decimal('0')),
    ('SperAktiv', Decimal('0'), Decimal('24'), Decimal('0'), Decimal('24')),
    ('Heptrazol', Decimal('10'), Decimal('0'), Decimal('0'), Decimal('10')),
    ('Prostazolin N30', Decimal('24'), Decimal('0'), Decimal('6'), Decimal('18')),
]

APTEKLER = [
    'Seymur Aptek (Pharma+)',
    'Nərgiz Aptek',
    'Xəzər Aptek',
]

NAME_ALIASES = {
    'Ropsol': 'Ropsol 30ml',
    'Opsidol N30': 'Opsidol N30 kapsul',
    'Zemovar N30': 'Zemovar N30 tablet',
    'Kartovey N30': 'Kartovey N30 tablet',
    'Fesola 150 ml': 'Fesola 250 ml',
    'Vitomer Kids 150 ml': 'Vitomer Kids',
    'Moksivista 100ml': 'Moxivista',
    'Peynstop N10 şase': 'Painstop',
    'Heptrazol': 'Heptrazol 80 ml N5',
    'Prostazolin N30': 'Prostazolin N30 kapsul',
    'Soltrop N30': 'Soltrop N30 tablet',
    'Solseda N30': 'Solseda N30 tablet',
    'Litasol N30': 'Litasol N30 kapsul',
}


def _find_drug(Medical, label):
    alias = NAME_ALIASES.get(label, label)
    drug = Medical.objects.filter(med_full_name=alias).first()
    if drug:
        return drug
    drug = Medical.objects.filter(med_full_name=label).first()
    if drug:
        return drug
    drug = Medical.objects.filter(med_name__iexact=alias).first()
    if drug:
        return drug
    base = label.split()[0]
    return Medical.objects.filter(med_name__iexact=base).first()


def seed_june_ledger(apps, schema_editor):
    Medical = apps.get_model('medicine', 'Medical')
    Aptek = apps.get_model('aptek', 'Aptek')
    AnbarHereket = apps.get_model('aptek', 'AnbarHereket')
    Qaime = apps.get_model('aptek', 'Qaime')

    if AnbarHereket.objects.exists():
        return

    aptek_map = {}
    for name in APTEKLER:
        aptek_map[name] = Aptek.objects.create(name=name)

    default_aptek = aptek_map[APTEKLER[0]]
    qaime = Qaime.objects.create(
        aptek=default_aptek,
        number=4,
        total=Decimal('0'),
    )
    qaime.created_at = '2026-07-06T11:02:00+04:00'
    qaime.save(update_fields=['created_at'])

    for label, evvel, gelen, cixan, _qalan in JUNE_DATA:
        drug = _find_drug(Medical, label)
        if not drug:
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


def unseed_june_ledger(apps, schema_editor):
    AnbarHereket = apps.get_model('aptek', 'AnbarHereket')
    Qaime = apps.get_model('aptek', 'Qaime')
    Aptek = apps.get_model('aptek', 'Aptek')
    AnbarHereket.objects.all().delete()
    Qaime.objects.all().delete()
    Aptek.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0001_initial'),
        ('medicine', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_june_ledger, unseed_june_ledger),
    ]
