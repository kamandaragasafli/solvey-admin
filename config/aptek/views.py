from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from medicine.models import Medical

from .models import AnbarHereket, Aptek, Qaime
from .pdf_import import QaimeParseError, _clean_aptek_name
from .services import import_qaime_pdf

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

AZ_MONTHS = {
    1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
    5: 'May', 6: 'İyun', 7: 'İyul', 8: 'Avqust',
    9: 'Sentyabr', 10: 'Oktyabr', 11: 'Noyabr', 12: 'Dekabr',
}


def _parse_date(value, fallback):
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _excel_qty(value):
    num = Decimal(str(value))
    if num == num.to_integral_value():
        return int(num), '0'
    return float(num), '0.########'


def _default_date_range(today=None):
    today = today or timezone.localdate()
    date_from = date(today.year, today.month, 1)
    _, last_day = monthrange(today.year, today.month)
    date_to = date(today.year, today.month, last_day)
    return date_from, date_to


def _ledger_filters(request):
    today = timezone.localdate()
    default_from, default_to = _default_date_range(today)

    date_from = _parse_date(request.GET.get('from'), default_from)
    date_to = _parse_date(request.GET.get('to'), default_to)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    aptek_id = request.GET.get('aptek') or None
    if aptek_id in (None, '', 'all'):
        aptek_id = None

    status_filter = request.GET.get('status') or None
    if status_filter in (None, '', 'all'):
        status_filter = None

    return date_from, date_to, aptek_id, status_filter


def _return_filters(request):
    today = timezone.localdate()
    default_from, default_to = _default_date_range(today)

    date_from = _parse_date(request.GET.get('from'), default_from)
    date_to = _parse_date(request.GET.get('to'), default_to)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    aptek_id = request.GET.get('aptek') or None
    if aptek_id in (None, '', 'all'):
        aptek_id = None

    search = (request.GET.get('q') or '').strip()

    return date_from, date_to, aptek_id, search


def _aptekler_filters(request):
    """Apteklər səhifəsi üçün daha geniş default aralıq."""
    today = timezone.localdate()
    default_from = date(today.year, today.month, 1)
    _, last_day = monthrange(today.year, today.month)
    default_to = date(today.year, today.month, last_day)

    date_from = _parse_date(request.GET.get('from'), default_from)
    date_to = _parse_date(request.GET.get('to'), default_to)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    aptek_id = request.GET.get('aptek') or None
    if aptek_id in (None, '', 'all'):
        aptek_id = None

    search = (request.GET.get('q') or '').strip()
    return date_from, date_to, aptek_id, search


def _date_range_label(date_from, date_to):
    if date_from.month == date_to.month and date_from.year == date_to.year:
        return AZ_MONTHS.get(date_from.month, '')
    return f'{date_from.strftime("%d.%m.%Y")} — {date_to.strftime("%d.%m.%Y")}'


def _document_movement_context(request, *, doc_type, movement_type, note_prefix):
    date_from, date_to, aptek_id, search = _return_filters(request)

    movements = (
        AnbarHereket.objects.filter(
            movement_type=movement_type,
            date__gte=date_from,
            date__lte=date_to,
        )
        .filter(
            Q(qaime__document_type=doc_type)
            | Q(note__istartswith=note_prefix)
            | Q(note__istartswith='Qaime')
        )
        .exclude(note=EVVEL_NOTE)
        .select_related('drug', 'aptek', 'qaime')
    )

    if aptek_id:
        movements = movements.filter(aptek_id=aptek_id)
    if search:
        movements = movements.filter(
            Q(drug__med_name__icontains=search)
            | Q(drug__med_full_name__icontains=search)
        )

    movements = movements.order_by('-date', 'aptek__name', 'drug__med_name')

    rows = []
    total_qty = Decimal('0')
    qaime_ids = set()
    for movement in movements:
        total_qty += movement.quantity
        if movement.qaime_id:
            qaime_ids.add(movement.qaime_id)
        rows.append({
            'date': movement.date,
            'aptek': movement.aptek.name if movement.aptek else '—',
            'qaime_number': movement.qaime.number if movement.qaime else '—',
            'drug': movement.drug.med_name,
            'drug_full': movement.drug.med_full_name or '',
            'quantity': movement.quantity,
            'pdf_url': movement.qaime.pdf.url if movement.qaime and movement.qaime.pdf else '',
        })

    return {
        'rows': rows,
        'aptekler': Aptek.objects.all(),
        'selected_aptek': str(aptek_id) if aptek_id else '',
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'search': search,
        'period_label': _date_range_label(date_from, date_to),
        'record_count': len(rows),
        'doc_count': len(qaime_ids),
        'total_qty': total_qty,
    }


def _qaimeler_context(request):
    date_from, date_to, aptek_id, search = _return_filters(request)

    hereket_qs = (
        AnbarHereket.objects.filter(movement_type=AnbarHereket.MOVEMENT_OUT)
        .select_related('drug')
        .order_by('id')
    )
    qaime_qs = (
        Qaime.objects.filter(
            document_type=Qaime.DOC_QAIME,
            doc_date__gte=date_from,
            doc_date__lte=date_to,
        )
        .select_related('aptek')
        .prefetch_related(Prefetch('hereketler', queryset=hereket_qs))
        .order_by('-doc_date', '-id')
    )

    if aptek_id:
        qaime_qs = qaime_qs.filter(aptek_id=aptek_id)
    if search:
        qaime_qs = qaime_qs.filter(
            Q(hereketler__drug__med_name__icontains=search)
            | Q(hereketler__drug__med_full_name__icontains=search)
        ).distinct()

    rows = []
    total_qty = Decimal('0')
    for qaime in qaime_qs:
        hereketler = list(qaime.hereketler.all())
        qty = sum((h.quantity for h in hereketler), Decimal('0'))
        total_qty += qty

        names = []
        for hereket in hereketler:
            name = hereket.drug.med_name
            if name not in names:
                names.append(name)
        if not names:
            drug_label = '—'
        elif len(names) <= 2:
            drug_label = ', '.join(names)
        else:
            drug_label = f"{', '.join(names[:2])} +{len(names) - 2}"

        rows.append({
            'date': qaime.doc_date,
            'aptek': qaime.aptek.name,
            'qaime_number': qaime.number,
            'drug_label': drug_label,
            'drug_count': len(names),
            'quantity': qty,
            'pdf_url': qaime.pdf.url if qaime.pdf else '',
        })

    return {
        'rows': rows,
        'aptekler': Aptek.objects.all(),
        'selected_aptek': str(aptek_id) if aptek_id else '',
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'search': search,
        'period_label': _date_range_label(date_from, date_to),
        'record_count': len(rows),
        'doc_count': len(rows),
        'total_qty': total_qty,
    }


def _anbara_elave_context(request):
    date_from, date_to, aptek_id, search = _return_filters(request)

    movements = (
        AnbarHereket.objects.filter(
            movement_type=AnbarHereket.MOVEMENT_IN,
            date__gte=date_from,
            date__lte=date_to,
        )
        .exclude(
            Q(qaime__document_type=Qaime.DOC_RETURN)
            | Q(note__istartswith='Geri qaytarma')
        )
        .select_related('drug', 'aptek', 'qaime')
    )

    if aptek_id:
        movements = movements.filter(aptek_id=aptek_id)
    if search:
        movements = movements.filter(
            Q(drug__med_name__icontains=search)
            | Q(drug__med_full_name__icontains=search)
            | Q(note__icontains=search)
        )

    movements = movements.order_by('-date', 'note', 'drug__med_name')

    rows = []
    total_qty = Decimal('0')
    sources = set()
    for movement in movements:
        total_qty += movement.quantity
        source = movement.note or 'Anbara əlavə'
        sources.add(source)
        rows.append({
            'date': movement.date,
            'source': source,
            'aptek': movement.aptek.name if movement.aptek else '—',
            'drug': movement.drug.med_name,
            'drug_full': movement.drug.med_full_name or '',
            'quantity': movement.quantity,
        })

    return {
        'rows': rows,
        'aptekler': Aptek.objects.all(),
        'selected_aptek': str(aptek_id) if aptek_id else '',
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'search': search,
        'period_label': _date_range_label(date_from, date_to),
        'record_count': len(rows),
        'source_count': len(sources),
        'total_qty': total_qty,
    }


def _sum_qty(qs):
    return qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0')


def _build_ledger(date_from, date_to, aptek_id=None, status_filter=None):
    drugs = Medical.objects.filter(status=True).order_by('position', 'med_name')
    rows = []
    totals = {
        'evvel': Decimal('0'),
        'gelen': Decimal('0'),
        'cixan': Decimal('0'),
        'qalan': Decimal('0'),
    }

    for drug in drugs:
        base_qs = AnbarHereket.objects.filter(drug=drug)

        evvel = _sum_qty(
            base_qs.filter(movement_type=AnbarHereket.MOVEMENT_IN, date__lt=date_from)
        ) - _sum_qty(
            base_qs.filter(movement_type=AnbarHereket.MOVEMENT_OUT, date__lt=date_from)
        )

        gelen = _sum_qty(
            base_qs.filter(
                movement_type=AnbarHereket.MOVEMENT_IN,
                date__gte=date_from,
                date__lte=date_to,
            )
        )

        out_qs = base_qs.filter(
            movement_type=AnbarHereket.MOVEMENT_OUT,
            date__gte=date_from,
            date__lte=date_to,
        )
        if aptek_id:
            out_qs = out_qs.filter(aptek_id=aptek_id)
        cixan = _sum_qty(out_qs)

        qalan = evvel + gelen - cixan
        low = qalan <= 5

        if status_filter == 'low' and not low:
            continue
        if status_filter == 'ok' and low:
            continue

        rows.append({
            'ad': drug.med_name,
            'evvel': evvel,
            'gelen': gelen,
            'cixan': cixan,
            'qalan': qalan,
            'low': low,
        })

        totals['evvel'] += evvel
        totals['gelen'] += gelen
        totals['cixan'] += cixan
        totals['qalan'] += qalan

    return rows, totals


EVVEL_NOTE = 'Əvvələ qalıq'
ANBARA_ELAVE_NOTE = 'Anbara əlavə'


def _opening_date_for_month(year: int, month: int) -> date:
    return date(year, month, 1) - timedelta(days=1)


def _parse_month(value, fallback_year, fallback_month):
    if not value:
        return fallback_year, fallback_month
    try:
        parts = value.split('-')
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return fallback_year, fallback_month


def _user_context(request):
    today = timezone.localdate()
    user = request.user
    user_label = user.get_full_name() or user.username
    if user.email:
        user_label = user.email
    return {
        'today': today.strftime('%d.%m.%Y'),
        'user_label': user_label,
    }


@login_required
def evvele_qaliq(request):
    today = timezone.localdate()
    year, month = _parse_month(request.GET.get('month') or request.POST.get('month'), today.year, today.month)
    opening_date = _opening_date_for_month(year, month)
    selected_month = f'{year:04d}-{month:02d}'
    month_label = AZ_MONTHS.get(month, '')

    if request.method == 'POST':
        with transaction.atomic():
            AnbarHereket.objects.filter(
                note=EVVEL_NOTE,
                date=opening_date,
                movement_type=AnbarHereket.MOVEMENT_IN,
            ).delete()

            saved = 0
            for drug in Medical.objects.filter(status=True):
                raw = request.POST.get(f'qty_{drug.id}', '').strip().replace(',', '.')
                if not raw:
                    continue
                try:
                    qty = Decimal(raw)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                AnbarHereket.objects.create(
                    drug=drug,
                    movement_type=AnbarHereket.MOVEMENT_IN,
                    quantity=qty,
                    date=opening_date,
                    note=EVVEL_NOTE,
                )
                saved += 1

        messages.success(
            request,
            f'{month_label} {year} — əvvələ qalıq yadda saxlanıldı ({saved} dərman).',
        )
        return redirect(f"{reverse('aptek:evvele_qaliq')}?month={selected_month}")

    existing = {
        row['drug_id']: row['quantity']
        for row in AnbarHereket.objects.filter(
            note=EVVEL_NOTE,
            date=opening_date,
            movement_type=AnbarHereket.MOVEMENT_IN,
        ).values('drug_id', 'quantity')
    }

    drugs = []
    for drug in Medical.objects.filter(status=True).order_by('position', 'med_name'):
        drug.qty = existing.get(drug.id, Decimal('0'))
        drugs.append(drug)

    context = {
        'drugs': drugs,
        'selected_month': selected_month,
        'month_label': month_label,
        'opening_date': opening_date,
        **_user_context(request),
    }
    return render(request, 'evvele_qaliq.html', context)


@login_required
def anbara_elave_form(request):
    today = timezone.localdate()
    selected_date = _parse_date(
        request.GET.get('date') or request.POST.get('date'),
        today,
    )
    note = (request.GET.get('note') or request.POST.get('note') or ANBARA_ELAVE_NOTE).strip()
    if not note:
        note = ANBARA_ELAVE_NOTE

    if request.method == 'POST':
        with transaction.atomic():
            AnbarHereket.objects.filter(
                movement_type=AnbarHereket.MOVEMENT_IN,
                date=selected_date,
                note=note,
                qaime__isnull=True,
            ).delete()

            saved = 0
            for drug in Medical.objects.filter(status=True):
                raw = request.POST.get(f'qty_{drug.id}', '').strip().replace(',', '.')
                if not raw:
                    continue
                try:
                    qty = Decimal(raw)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                AnbarHereket.objects.create(
                    drug=drug,
                    movement_type=AnbarHereket.MOVEMENT_IN,
                    quantity=qty,
                    date=selected_date,
                    note=note,
                )
                saved += 1

        messages.success(
            request,
            f'{selected_date.strftime("%d.%m.%Y")} — anbara əlavə yadda saxlanıldı ({saved} dərman).',
        )
        params = urlencode({'date': selected_date.isoformat(), 'note': note})
        return redirect(f"{reverse('aptek:anbara_elave_form')}?{params}")

    existing = {
        row['drug_id']: row['quantity']
        for row in AnbarHereket.objects.filter(
            movement_type=AnbarHereket.MOVEMENT_IN,
            date=selected_date,
            note=note,
            qaime__isnull=True,
        ).values('drug_id', 'quantity')
    }

    drugs = []
    for drug in Medical.objects.filter(status=True).order_by('position', 'med_name'):
        drug.qty = existing.get(drug.id, Decimal('0'))
        drugs.append(drug)

    context = {
        'drugs': drugs,
        'selected_date': selected_date.isoformat(),
        'note': note,
        **_user_context(request),
    }
    return render(request, 'anbara_elave_form.html', context)


@login_required
def geri_qaytarma(request):
    context = _document_movement_context(
        request,
        doc_type=Qaime.DOC_RETURN,
        movement_type=AnbarHereket.MOVEMENT_IN,
        note_prefix='Geri qaytarma',
    )
    context.update(_user_context(request))
    return render(request, 'geri_qaytarma.html', context)


@login_required
def anbara_elave_siyahi(request):
    context = _anbara_elave_context(request)
    context.update(_user_context(request))
    return render(request, 'anbara_elave.html', context)


@login_required
def qaimeler(request):
    context = _qaimeler_context(request)
    context.update(_user_context(request))
    return render(request, 'qaimeler.html', context)


@login_required
def aptekler(request):
    date_from, date_to, _, search_from_filters = _aptekler_filters(request)
    search = (request.GET.get('q') or search_from_filters or '').strip()

    date_filter = Q(
        anbar_hereketleri__date__gte=date_from,
        anbar_hereketleri__date__lte=date_to,
    )

    aptek_qs = (
        Aptek.objects.annotate(
            qaime_count=Count(
                'anbar_hereketleri__qaime',
                filter=date_filter
                & Q(
                    anbar_hereketleri__movement_type=AnbarHereket.MOVEMENT_OUT,
                    anbar_hereketleri__qaime__document_type=Qaime.DOC_QAIME,
                ),
                distinct=True,
            ),
            return_count=Count(
                'anbar_hereketleri__qaime',
                filter=date_filter
                & Q(
                    anbar_hereketleri__movement_type=AnbarHereket.MOVEMENT_IN,
                    anbar_hereketleri__qaime__document_type=Qaime.DOC_RETURN,
                ),
                distinct=True,
            ),
            last_activity=Max(
                'anbar_hereketleri__date',
                filter=date_filter,
            ),
            out_qty=Sum(
                'anbar_hereketleri__quantity',
                filter=date_filter
                & Q(anbar_hereketleri__movement_type=AnbarHereket.MOVEMENT_OUT),
            ),
            in_return_qty=Sum(
                'anbar_hereketleri__quantity',
                filter=date_filter
                & Q(
                    anbar_hereketleri__movement_type=AnbarHereket.MOVEMENT_IN,
                    anbar_hereketleri__qaime__document_type=Qaime.DOC_RETURN,
                ),
            ),
        )
        .order_by('name')
    )

    if search:
        aptek_qs = aptek_qs.filter(name__icontains=search)

    rows = []
    total_qaime = 0
    total_return = 0
    for aptek in aptek_qs:
        clean_name = _clean_aptek_name(aptek.name)
        if aptek.name != clean_name:
            aptek.name = clean_name
            aptek.save(update_fields=['name'])

        qaime_count = aptek.qaime_count or 0
        return_count = aptek.return_count or 0
        total_qaime += qaime_count
        total_return += return_count
        rows.append({
            'id': aptek.id,
            'name': aptek.name,
            'qaime_count': qaime_count,
            'return_count': return_count,
            'last_activity': aptek.last_activity,
            'out_qty': aptek.out_qty or Decimal('0'),
            'in_return_qty': aptek.in_return_qty or Decimal('0'),
        })

    context = {
        'rows': rows,
        'search': search,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'period_label': _date_range_label(date_from, date_to),
        'aptek_count': len(rows),
        'total_qaime': total_qaime,
        'total_return': total_return,
        **_user_context(request),
    }
    return render(request, 'aptekler.html', context)


@login_required
def export_ledger_excel(request):
    date_from, date_to, aptek_id, status_filter = _ledger_filters(request)
    rows, totals = _build_ledger(date_from, date_to, aptek_id, status_filter)

    aptek_label = 'Bütün apteklər'
    if aptek_id:
        aptek = Aptek.objects.filter(pk=aptek_id).first()
        if aptek:
            aptek_label = aptek.name

    wb = Workbook()
    ws = wb.active
    ws.title = 'Anbar qalığı'

    title_font = Font(bold=True, size=14, color='1F2937')
    subtitle_font = Font(size=10, italic=True, color='6B7280')
    header_font = Font(bold=True, size=11, color='1F2937')

    # Şəkildəki kimi hər sütun üçün fərqli rəng
    header_fills = {
        1: PatternFill('solid', start_color='E2E8F0'),  # #
        2: PatternFill('solid', start_color='E2E8F0'),  # Malın adı
        3: PatternFill('solid', start_color='FBE54D'),  # Əvvələ qalıq - sarı
        4: PatternFill('solid', start_color='86EFC0'),  # Gələn - yaşıl
        5: PatternFill('solid', start_color='F8B4B4'),  # Çıxan - qırmızı
        6: PatternFill('solid', start_color='A9C7F5'),  # Anbarda qalıq - mavi
        7: PatternFill('solid', start_color='D3C4F0'),  # Vəziyyət - bənövşəyi
    }

    thin = Side(style='thin', color='D1D5DB')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws['A1'] = f'Anbar qalığı — {date_from.strftime("%d.%m.%Y")} – {date_to.strftime("%d.%m.%Y")}'
    ws['A1'].font = title_font
    ws['A2'] = f'Aptek: {aptek_label}'
    ws['A2'].font = subtitle_font
    ws.merge_cells('A1:G1')
    ws.merge_cells('A2:G2')

    headers = ['#', 'Malın adı', 'Əvvələ qalıq', 'Gələn', 'Çıxan', 'Anbarda qalıq', 'Vəziyyət']
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col, value=title)
        cell.font = header_font
        cell.fill = header_fills[col]
        cell.border = border
        cell.alignment = Alignment(horizontal='center' if col != 2 else 'left', vertical='center')
    ws.row_dimensions[4].height = 22

    normal_fill = PatternFill('solid', start_color='DCFCE7')
    normal_font = Font(color='15803D', bold=True, size=10)
    low_fill = PatternFill('solid', start_color='FEE2E2')
    low_font = Font(color='B91C1C', bold=True, size=10)

    row_idx = 5
    for i, row in enumerate(rows, start=1):
        ws.cell(row=row_idx, column=1, value=i)
        ws.cell(row=row_idx, column=2, value=row['ad'])
        for col, key in enumerate(['evvel', 'gelen', 'cixan', 'qalan'], start=3):
            qty_val, qty_fmt = _excel_qty(row[key])
            qty_cell = ws.cell(row=row_idx, column=col, value=qty_val)
            qty_cell.number_format = qty_fmt

        status_cell = ws.cell(row=row_idx, column=7, value='Azalır' if row['low'] else 'Normal')
        if row['low']:
            status_cell.fill = low_fill
            status_cell.font = low_font
        else:
            status_cell.fill = normal_fill
            status_cell.font = normal_font
        status_cell.alignment = Alignment(horizontal='center', vertical='center')

        for col in range(1, 8):
            cell = ws.cell(row=row_idx, column=col)
            cell.border = border
            if col == 1:
                cell.alignment = Alignment(horizontal='center')
            elif col == 2:
                cell.alignment = Alignment(horizontal='left')
            elif 3 <= col <= 6:
                cell.alignment = Alignment(horizontal='right')

        # Sətir zolaqlı (zebra) fon — oxunaqlılıq üçün
        if i % 2 == 0:
            for col in (1, 2, 3, 4, 5, 6):
                ws.cell(row=row_idx, column=col).fill = PatternFill('solid', start_color='F9FAFB')

        row_idx += 1

    ws.cell(row=row_idx, column=2, value='Cəmi').font = Font(bold=True)
    for col, key in enumerate(['evvel', 'gelen', 'cixan', 'qalan'], start=3):
        qty_val, qty_fmt = _excel_qty(totals[key])
        cell = ws.cell(row=row_idx, column=col, value=qty_val)
        cell.font = Font(bold=True)
        cell.number_format = qty_fmt
        cell.alignment = Alignment(horizontal='right')
        cell.border = Border(top=Side(style='thin', color='9CA3AF'))

    widths = {'A': 6, 'B': 28, 'C': 14, 'D': 10, 'E': 10, 'F': 14, 'G': 12}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:G{row_idx - 1}'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f'anbar_qaligi_{date_from.isoformat()}_{date_to.isoformat()}.xlsx'
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def aptek_list(request):
    if request.method == 'POST':
        if request.FILES.get('pdf_file'):
            pdf_file = request.FILES['pdf_file']
            try:
                result = import_qaime_pdf(pdf_file)
                messages.success(request, result['message'])
                if result['missing_drugs']:
                    messages.warning(
                        request,
                        'Tapılmayan dərmanlar: ' + ', '.join(result['missing_drugs']),
                    )
                doc_date = result['doc_date']
                month_start = date(doc_date.year, doc_date.month, 1)
                _, month_last = monthrange(doc_date.year, doc_date.month)
                month_end = date(doc_date.year, doc_date.month, month_last)
                params = urlencode({
                    'from': month_start.isoformat(),
                    'to': month_end.isoformat(),
                    'aptek': result['aptek_id'],
                })
                return redirect(f"{reverse('aptek:anbar_dashboard')}?{params}")
            except QaimeParseError as exc:
                messages.error(request, str(exc))
            except Exception:
                messages.error(request, 'PDF emal edilərkən xəta baş verdi.')
            return redirect('aptek:anbar_dashboard')

        if request.POST.get('manual_qaime') == '1':
            aptek_id = request.POST.get('manual_aptek') or ''
            doc_date_raw = request.POST.get('manual_doc_date') or ''
            doc_date = _parse_date(doc_date_raw, None)
            aptek = Aptek.objects.filter(pk=aptek_id).first() if aptek_id else None

            if not aptek:
                messages.error(request, 'Aptek seçilməyib.')
                return redirect('aptek:anbar_dashboard')
            if not doc_date:
                messages.error(request, 'Tarix düzgün deyil.')
                return redirect('aptek:anbar_dashboard')

            drug_ids = request.POST.getlist('manual_drug_id')
            qty_values = request.POST.getlist('manual_qty')
            items = []
            for drug_id, qty_raw in zip(drug_ids, qty_values):
                if not drug_id:
                    continue
                qty_txt = (qty_raw or '').strip().replace(',', '.')
                if not qty_txt:
                    continue
                try:
                    qty = Decimal(qty_txt)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                drug = Medical.objects.filter(pk=drug_id, status=True).first()
                if not drug:
                    continue
                items.append((drug, qty))

            if not items:
                messages.error(request, 'Ən azı bir dərman və miqdar daxil edin.')
                return redirect('aptek:anbar_dashboard')

            with transaction.atomic():
                qaime_number = (
                    Qaime.objects.filter(aptek=aptek, document_type=Qaime.DOC_QAIME)
                    .order_by('-number')
                    .values_list('number', flat=True)
                    .first() or 0
                ) + 1

                qaime = Qaime.objects.create(
                    aptek=aptek,
                    number=qaime_number,
                    document_type=Qaime.DOC_QAIME,
                    doc_date=doc_date,
                    total=Decimal('0'),
                )

                total_qty = Decimal('0')
                for drug, qty in items:
                    AnbarHereket.objects.create(
                        drug=drug,
                        movement_type=AnbarHereket.MOVEMENT_OUT,
                        quantity=qty,
                        date=doc_date,
                        aptek=aptek,
                        qaime=qaime,
                        note=f'Qaimə №{qaime_number}',
                    )
                    total_qty += qty

                qaime.total = total_qty
                qaime.save(update_fields=['total'])

            messages.success(
                request,
                f'Manuel qaimə №{qaime_number} əlavə olundu ({len(items)} dərman).',
            )
            month_start = date(doc_date.year, doc_date.month, 1)
            _, month_last = monthrange(doc_date.year, doc_date.month)
            month_end = date(doc_date.year, doc_date.month, month_last)
            params = urlencode({
                'from': month_start.isoformat(),
                'to': month_end.isoformat(),
                'aptek': aptek.id,
            })
            return redirect(f"{reverse('aptek:anbar_dashboard')}?{params}")

    date_from, date_to, aptek_id, status_filter = _ledger_filters(request)
    today = timezone.localdate()
    rows, totals = _build_ledger(date_from, date_to, aptek_id, status_filter)
    aptekler = Aptek.objects.all()
    for aptek in aptekler:
        clean_name = _clean_aptek_name(aptek.name)
        if aptek.name != clean_name:
            aptek.name = clean_name
            aptek.save(update_fields=['name'])
    last_qaime_qs = Qaime.objects.filter(document_type=Qaime.DOC_QAIME)
    if aptek_id:
        last_qaime_qs = last_qaime_qs.filter(aptek_id=aptek_id)
    last_qaime = last_qaime_qs.select_related('aptek').order_by('-doc_date', '-id').first()

    month_label = AZ_MONTHS.get(date_from.month, '')
    if date_from.month != date_to.month or date_from.year != date_to.year:
        month_label = (
            f'{date_from.strftime("%d.%m.%Y")} — {date_to.strftime("%d.%m.%Y")}'
        )

    user = request.user
    user_label = user.get_full_name() or user.username
    if user.email:
        user_label = user.email

    context = {
        'rows': rows,
        'totals': totals,
        'aptekler': aptekler,
        'selected_aptek': str(aptek_id) if aptek_id else '',
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'status_filter': status_filter or 'all',
        'month_label': month_label,
        'record_count': len(rows),
        'last_qaime': last_qaime,
        'manual_drugs': Medical.objects.filter(status=True).order_by('position', 'med_name'),
        'manual_default_date': today.isoformat(),
        'today': today.strftime('%d.%m.%Y'),
        'user_label': user_label,
    }
    return render(request, 'anbar_dashboard.html', context)
