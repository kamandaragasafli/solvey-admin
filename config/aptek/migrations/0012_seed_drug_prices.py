from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import migrations


PRICE_ROWS = [
    ('Levostrong', '7.5', (2026, 12)),
    ('Ropsol', '16.7', (2028, 2)),
    ('Fesola', '24.9', (2026, 6)),
    ('Soltep', '28.5', (2026, 3)),
    ('Vitomer Kids', '26', (2026, 6)),
    ('Fensavin', '24', (2026, 6)),
    ('Litasol', '29.5', (2028, 9)),
    ('Solseda', '26', (2027, 11)),
    ('Soltrop', '34', (2027, 4)),
    ('Zemovar', '38.42', (2027, 11)),
    ('Kartovey', '28.5', (2026, 6)),
    ('Opsidol', '33', (2026, 6)),
    ('Lipomaq', '55', (2029, 3)),
    ('SperAktiv', '77', None),
    ('Prostazolin', '15.03', (2027, 12)),
    ('Heptrazol', '35.07', (2029, 1)),
    ('Moxivista', '13.72', (2026, 10)),
    ('Feelon', '25', (2026, 12)),
    ('Provital', '5', None),
    ('Painstop', '16.67', (2027, 3)),
]

ENSURE_MEDICAL = {
    'SperAktiv': 'SperAktiv saşe',
    'Feelon': 'Feelon N10',
}


def _end_of_month(year, month):
    return date(year, month, monthrange(year, month)[1])


def _find_medical(Medical, key):
    key_l = key.lower()
    qs = Medical.objects.filter(status=True)
    exact = qs.filter(med_name__iexact=key).first()
    if exact:
        return exact
    starts = list(qs.filter(med_name__istartswith=key).order_by('med_name')[:20])
    for m in starts:
        if m.med_name.lower().startswith(key_l):
            return m
    if starts:
        return starts[0]
    return qs.filter(med_name__icontains=key).order_by('med_name').first()


def forwards(apps, schema_editor):
    """Historical model istifadə et — category/min_stock hələ DB-də var."""
    Depo = apps.get_model('aptek', 'Depo')
    DrugPrice = apps.get_model('aptek', 'DrugPrice')
    Medical = apps.get_model('medicine', 'Medical')

    depo = Depo.objects.filter(is_default=True).first() or Depo.objects.order_by('id').first()
    if depo is None:
        depo = Depo.objects.create(name='Əsas depo', is_default=True)

    for key, price_str, skt in PRICE_ROWS:
        drug = _find_medical(Medical, key)
        if drug is None:
            full_name = ENSURE_MEDICAL.get(key, key)
            drug = Medical.objects.create(
                med_name=full_name,
                med_full_name=full_name,
                med_price=Decimal('0'),
                komissiya=Decimal('0'),
                status=True,
                in_stock=True,
            )

        expiry = _end_of_month(*skt) if skt else None
        defaults = {
            'price': Decimal(price_str),
            'expiry_date': expiry,
            'category': '',
            'min_stock': Decimal('5'),
        }
        existing = DrugPrice.objects.filter(depo=depo, drug=drug).first()
        if existing:
            for attr, value in defaults.items():
                setattr(existing, attr, value)
            existing.save()
        else:
            DrugPrice.objects.create(depo=depo, drug=drug, **defaults)


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
