import gc
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AnbarHereket, Aptek, Depo, Qaime
from .pdf_import import (
    QaimeParseError,
    _clean_aptek_name,
    clear_drug_cache,
    find_drug,
    parse_official_qaime_pdf,
    parse_qaime_pdf,
)


def _get_or_create_aptek(name: str, depo: Depo) -> Aptek:
    normalized = _clean_aptek_name(name)
    aptek = Aptek.objects.filter(depo=depo, name__iexact=normalized).first()
    if not aptek:
        for candidate in Aptek.objects.filter(depo=depo):
            if _clean_aptek_name(candidate.name) == normalized:
                aptek = candidate
                break
    if aptek:
        if aptek.name != normalized:
            aptek.name = normalized
            aptek.save(update_fields=['name'])
        return aptek
    return Aptek.objects.create(depo=depo, name=normalized)


def _next_qaime_number(aptek: Aptek, document_type: str, depo: Depo) -> int:
    last = (
        Qaime.objects.filter(depo=depo, aptek=aptek, document_type=document_type)
        .order_by('-number')
        .values_list('number', flat=True)
        .first()
    )
    return (last or 0) + 1


def _should_keep_pdf() -> bool:
    return bool(getattr(settings, 'APTEK_KEEP_QAIME_PDF', True))


def purge_qaime_pdfs(*, older_than_days=None, all_files=False):
    """
    Qaimə PDF fayllarını diskdən sil, DB qeydini (Qaime/hərəkət) saxla.
    all_files=True → bütün PDF-lər
    older_than_days=N → N gündən köhnə (default: settings APTEK_QAIME_PDF_RETENTION_DAYS)
    """
    qs = Qaime.objects.exclude(pdf='').exclude(pdf__isnull=True)
    if not all_files:
        days = older_than_days
        if days is None:
            days = int(getattr(settings, 'APTEK_QAIME_PDF_RETENTION_DAYS', 30))
        cutoff = timezone.now() - timedelta(days=max(1, days))
        qs = qs.filter(created_at__lt=cutoff)

    removed = 0
    freed = 0
    for qaime in qs.iterator():
        try:
            if qaime.pdf and qaime.pdf.name:
                try:
                    size = qaime.pdf.size
                except Exception:
                    size = 0
                qaime.pdf.delete(save=False)
                qaime.pdf = None
                qaime.save(update_fields=['pdf'])
                removed += 1
                freed += size or 0
        except Exception:
            continue
    return {'removed': removed, 'freed_bytes': freed}


def cleanup_expired_qaime_pdfs():
    """Cron üçün: 1 aydan köhnə PDF fayllarını sil."""
    return purge_qaime_pdfs(older_than_days=None, all_files=False)


@transaction.atomic
def import_qaime_pdf(uploaded_file, depo: Depo, is_official: bool = False):
    clear_drug_cache()
    try:
        if is_official:
            parsed = parse_official_qaime_pdf(uploaded_file)
        else:
            parsed = parse_qaime_pdf(uploaded_file, side='left')

        aptek = _get_or_create_aptek(parsed.aptek_name, depo)

        movement_type = (
            AnbarHereket.MOVEMENT_IN
            if parsed.document_type == Qaime.DOC_RETURN
            else AnbarHereket.MOVEMENT_OUT
        )
        doc_label = 'Geri qaytarma' if parsed.document_type == Qaime.DOC_RETURN else 'Qaimə'
        kind_label = 'rəsmi' if is_official else 'qeyri rəsmi'
        qaime_number = (
            parsed.number if (is_official and parsed.number)
            else _next_qaime_number(aptek, parsed.document_type, depo)
        )
        if is_official and parsed.number:
            if Qaime.objects.filter(
                depo=depo,
                aptek=aptek,
                number=qaime_number,
                document_type=parsed.document_type,
            ).exists():
                qaime_number = _next_qaime_number(aptek, parsed.document_type, depo)

        movement_date = parsed.doc_date

        qaime = Qaime.objects.create(
            depo=depo,
            aptek=aptek,
            number=qaime_number,
            document_type=parsed.document_type,
            total=parsed.total,
            doc_date=movement_date,
            is_official=is_official,
        )

        missing_drugs = []
        movement_count = 0
        total_qty = Decimal('0')

        for item in parsed.items:
            drug = find_drug(item.name)
            if not drug:
                missing_drugs.append(item.name)
                continue

            AnbarHereket.objects.create(
                depo=depo,
                drug=drug,
                movement_type=movement_type,
                quantity=item.quantity,
                date=movement_date,
                aptek=aptek,
                qaime=qaime,
                note=f'{doc_label} №{qaime_number} ({kind_label})',
            )
            movement_count += 1
            total_qty += item.quantity

        if movement_count == 0:
            qaime.delete()
            raise QaimeParseError(
                'Heç bir dərman bazada tapılmadı: ' + ', '.join(missing_drugs[:5])
            )

        # Default: PDF diskdə saxlanılmır — yalnız məlumat DB-də qalır
        if _should_keep_pdf():
            uploaded_file.seek(0)
            qaime.pdf.save(uploaded_file.name, uploaded_file, save=True)

        qaime.total = parsed.total if parsed.total else total_qty
        qaime.save(update_fields=['total'])

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
            'is_official': is_official,
            'message': (
                f'{doc_label} ({kind_label}) — {aptek.name} ({depo.name}) əlavə olundu. '
                f'{movement_count} dərman {warehouse_action}.'
            ),
        }
    finally:
        clear_drug_cache()
        gc.collect()
