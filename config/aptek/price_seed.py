"""Anbar dərman qiymətləri (DrugPrice) seed məlumatı."""
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import transaction

from medicine.models import Medical

from .models import Depo, DrugPrice


def _end_of_month(year, month):
    return date(year, month, monthrange(year, month)[1])


# (uyğunlaşdırma açarı, qiymət, SKT ay/il və ya None)
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

# Medical-da olmayanlar üçün yaradılacaq adlar
ENSURE_MEDICAL = {
    'SperAktiv': 'SperAktiv saşe',
    'Feelon': 'Feelon N10',
}


def _find_medical(key: str):
    key_l = key.lower()
    # Əvvəl dəqiq / prefiks uyğunluğu
    qs = Medical.objects.filter(status=True)
    exact = qs.filter(med_name__iexact=key).first()
    if exact:
        return exact
    starts = qs.filter(med_name__istartswith=key).order_by('med_name')
    if starts.exists():
        # Vitomer Kids vs Vitomer D3 — tam açar üstün
        for m in starts:
            if m.med_name.lower().startswith(key_l):
                return m
        return starts.first()
    contains = qs.filter(med_name__icontains=key).order_by('med_name')
    return contains.first()


def _ensure_medical(key: str):
    med = _find_medical(key)
    if med:
        return med
    full_name = ENSURE_MEDICAL.get(key, key)
    return Medical.objects.create(
        med_name=full_name,
        med_full_name=full_name,
        med_price=Decimal('0'),
        komissiya=Decimal('0'),
        status=True,
        in_stock=True,
    )


@transaction.atomic
def seed_drug_prices(depo=None):
    """Default (və ya verilmiş) depo üçün DrugPrice yaz / yenilə."""
    if depo is None:
        depo = Depo.objects.filter(is_default=True).first() or Depo.objects.order_by('id').first()
    if depo is None:
        depo = Depo.objects.create(name='Əsas depo', is_default=True)

    created = updated = skipped = 0
    for key, price_str, skt in PRICE_ROWS:
        drug = _ensure_medical(key)
        if not drug:
            skipped += 1
            continue
        price = Decimal(price_str)
        expiry = _end_of_month(*skt) if skt else None
        obj, was_created = DrugPrice.objects.update_or_create(
            depo=depo,
            drug=drug,
            defaults={
                'price': price,
                'expiry_date': expiry,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {'depo_id': depo.id, 'created': created, 'updated': updated, 'skipped': skipped}
