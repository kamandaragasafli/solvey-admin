from decimal import Decimal
from django.db import transaction

from .models import AnbarHereket, Aptek, Qaime
from .pdf_import import QaimeParseError, _clean_aptek_name, find_drug, parse_qaime_pdf


def _get_or_create_aptek(name: str) -> Aptek:
    normalized = _clean_aptek_name(name)
    aptek = Aptek.objects.filter(name__iexact=normalized).first()
    if not aptek:
        for candidate in Aptek.objects.all():
            if _clean_aptek_name(candidate.name) == normalized:
                aptek = candidate
                break
    if aptek:
        if aptek.name != normalized:
            aptek.name = normalized
            aptek.save(update_fields=['name'])
        return aptek
    return Aptek.objects.create(name=normalized)


def _next_qaime_number(aptek: Aptek, document_type: str) -> int:
    last = (
        Qaime.objects.filter(aptek=aptek, document_type=document_type)
        .order_by('-number')
        .values_list('number', flat=True)
        .first()
    )
    return (last or 0) + 1


@transaction.atomic
def import_qaime_pdf(uploaded_file):
    parsed = parse_qaime_pdf(uploaded_file)
    aptek = _get_or_create_aptek(parsed.aptek_name)

    movement_type = (
        AnbarHereket.MOVEMENT_IN
        if parsed.document_type == Qaime.DOC_RETURN
        else AnbarHereket.MOVEMENT_OUT
    )
    doc_label = 'Geri qaytarma' if parsed.document_type == Qaime.DOC_RETURN else 'Qaimə'
    qaime_number = _next_qaime_number(aptek, parsed.document_type)
    movement_date = parsed.doc_date

    qaime = Qaime.objects.create(
        aptek=aptek,
        number=qaime_number,
        document_type=parsed.document_type,
        total=parsed.total,
        doc_date=movement_date,
    )

    uploaded_file.seek(0)
    qaime.pdf.save(uploaded_file.name, uploaded_file, save=True)

    missing_drugs = []
    movement_count = 0

    for item in parsed.items:
        drug = find_drug(item.name)
        if not drug:
            missing_drugs.append(item.name)
            continue

        AnbarHereket.objects.create(
            drug=drug,
            movement_type=movement_type,
            quantity=item.quantity,
            date=movement_date,
            aptek=aptek,
            qaime=qaime,
            note=f'{doc_label} №{qaime_number}',
        )
        movement_count += 1

    if movement_count == 0:
        qaime.delete()
        raise QaimeParseError(
            'Heç bir dərman bazada tapılmadı: ' + ', '.join(missing_drugs[:5])
        )

    warehouse_action = (
        'anbara əlavə edildi' if movement_type == AnbarHereket.MOVEMENT_IN
        else 'anbardan çıxıldı'
    )

    return {
        'aptek': aptek.name,
        'aptek_id': aptek.id,
        'number': qaime_number,
        'document_type': parsed.document_type,
        'doc_date': movement_date,
        'movement_count': movement_count,
        'missing_drugs': missing_drugs,
        'created': True,
        'message': (
            f'{doc_label} — {aptek.name} əlavə olundu. '
            f'{movement_count} dərman {warehouse_action}.'
        ),
    }
