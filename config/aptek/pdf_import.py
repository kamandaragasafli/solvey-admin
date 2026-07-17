import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pdfplumber

from medicine.models import Medical

NAME_ALIASES = {
    'peynstop': 'painstop',
    'painstop': 'painstop',
    'moksivista': 'moxivista',
    'moxivista': 'moxivista',
    'ropsol': 'ropsol',
    'fesola': 'fesola',
    'speraktiv': 'speraktiv',
    'lipomaq': 'lipomaq',
    'lipomag': 'lipomaq',
    'lipomaq+': 'lipomaq',
    'feelon': 'feelon',
    'provital': 'provital',
    'opeblok': 'opeblock',
    'opeblock': 'opeblock',
    'heptrazol': 'heptrazol',
    'levostrong': 'levostrong',
    'litasol': 'litasol',
    'fensavin': 'fensavin',
    'prostagold': 'prostagold',
}


def _fold_az(value: str) -> str:
    """Böyük/kiçik və AZ hərflərini müqayisə üçün normallaşdır."""
    text = (value or '').lower().strip()
    for src, dst in (
        ('ə', 'e'), ('ı', 'i'), ('ö', 'o'), ('ü', 'u'),
        ('ş', 's'), ('ç', 'c'), ('ğ', 'g'), ('+', ' '),
    ):
        text = text.replace(src, dst)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_drug_first_word(label: str) -> str:
    """PDF: «Betasol N30 kapsul (12.26)» → «Betasol»"""
    clean = _clean_drug_label(label)
    if not clean:
        return ''
    match = re.match(r'^(\S+)', clean)
    return match.group(1) if match else clean.split()[0]


@dataclass
class ParsedLineItem:
    name: str
    quantity: Decimal
    amount: Decimal = Decimal('0')


@dataclass
class ParsedDocument:
    aptek_name: str = ''
    number: int = 0
    doc_date: date | None = None
    document_type: str = 'qaime'
    items: list[ParsedLineItem] = field(default_factory=list)
    total: Decimal = Decimal('0')
    raw_text: str = ''


class QaimeParseError(Exception):
    pass


def _parse_az_decimal(value) -> Decimal:
    if value is None:
        return Decimal('0')
    text = str(value).strip().replace(' ', '')
    if not text or text in {'-', '—', '–'}:
        return Decimal('0')
    text = text.replace(',', '.')
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal('0')


def _normalize_name(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip())


def _clean_aptek_name(value: str) -> str:
    name = _normalize_name(value)
    # PDF-də iki sütun olanda: "Seymur Aptek Müştəri Seymur Aptek" — birincini saxla
    name = re.split(
        r'\s+(?:Müştəri|Musteri|Mushtəri|Müşteri|Муштери)\s*:?\s*',
        name,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    name = re.sub(
        r'^(?:Müştəri|Musteri|Mushtəri|Müşteri|Муштери)\s*:?\s*',
        '',
        name,
        flags=re.IGNORECASE,
    )
    name = re.split(r'(?:geriqaytarma|Qaim[əe]|Tarix)', name, flags=re.IGNORECASE)[0]
    return name.strip(' :')


def _clean_drug_label(label: str) -> str:
    label = _normalize_name(label)
    label = re.sub(r'\s*\([^)]*\)', '', label)
    return label.strip()


_DRUG_CACHE = None


def clear_drug_cache():
    global _DRUG_CACHE
    _DRUG_CACHE = None


def _cached_drugs():
    global _DRUG_CACHE
    if _DRUG_CACHE is None:
        _DRUG_CACHE = list(
            Medical.objects.filter(status=True).only('id', 'med_name', 'med_full_name')
        )
    return _DRUG_CACHE


def find_drug(label: str):
    """PDF adını Medical ilə uyğunlaşdır (böyük/kiçik, alias, prefiks)."""
    clean = _clean_drug_label(label)
    folded = _fold_az(clean)
    if not folded:
        return None

    first = folded.split()[0]
    key = NAME_ALIASES.get(first, first)

    best = None
    best_score = 0
    for drug in _cached_drugs():
        med_fold = _fold_az(drug.med_name or '')
        full_fold = _fold_az(drug.med_full_name or '')
        if not med_fold and not full_fold:
            continue
        med_first = (med_fold.split()[0] if med_fold else '')
        score = 0

        if med_fold and (folded == med_fold or folded.startswith(med_fold + ' ')):
            score = 120 + len(med_fold)
        elif full_fold and (folded == full_fold or folded.startswith(full_fold + ' ')):
            score = 110 + len(full_fold)
        elif med_fold and med_fold.startswith(folded) and len(folded) >= 4:
            score = 100 + len(folded)
        elif med_first and med_first == key:
            score = 80 + len(med_first)
        elif med_first and key.startswith(med_first) and len(med_first) >= 5:
            score = 50
        elif med_first and med_first.startswith(key) and len(key) >= 5:
            score = 45
        else:
            continue

        if score > best_score:
            best_score = score
            best = drug

    return best


def _parse_doc_date(text: str) -> date | None:
    match = re.search(
        r'(?:Tarix|tarix)\s*:?\s*(\d{2})\.(\d{2})\.(\d{4})',
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_aptek_name(text: str) -> str:
    match = re.search(
        r'(?:Müştəri|Musteri|Mushtəri|Müşteri|Муштери)\s*:?\s*([^\n\r]+)',
        text,
        re.IGNORECASE,
    )
    if match:
        name = _clean_aptek_name(match.group(1))
        if name:
            return name
    return ''


def _parse_number(text: str, is_return: bool) -> int:
    if is_return:
        patterns = [
            r'geriqaytarma[^\d\n]{0,40}(\d+)',
            r'(?:Geri\s*qaytarma|geri\s*qaytarma)\s*[^\d\n]{0,20}(\d+)',
        ]
    else:
        patterns = [
            r'(?:Qaim[əe]|Qaime)\s*n[oö]mr[əe]si\s*[№#Nno°\s.:]*(\d+)',
            r'(?:Qaim[əe]|Qaime)\s*[№#Nno°\s.:]+(\d+)',
            r'n[oö]mr[əe]si\s*[№#Nno°\s.:]*(\d+)',
            r'nomr[əe]si\s*[№#Nno°\s.:]*(\d+)',
        ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    if not is_return:
        match = re.search(r'[№#°]\s*(\d+)', text)
        if match:
            return int(match.group(1))

    return _parse_number_from_header_numbers(text, is_return)


def _parse_number_from_header_numbers(text: str, is_return: bool) -> int:
    """Sol sütunda yalnız rəqəmlər olanda (məs: 10  1  4) — ortadakı qaimə nömrəsi."""
    lines = text.splitlines()
    for line in lines[:12]:
        if re.search(r'geri\s*qaytarma', line, re.IGNORECASE):
            nums = re.findall(r'\d+', line)
            if nums:
                return int(nums[-1])
        if re.search(r'qaim|nomr', line, re.IGNORECASE):
            nums = re.findall(r'\d+', line)
            if nums:
                return int(nums[0])

    for line in lines[:8]:
        stripped = line.strip()
        if not stripped or re.search(r'[a-zA-ZəöüğıçşƏÖÜĞIÇŞ]', stripped):
            continue
        nums = re.findall(r'\d+', stripped)
        if 1 <= len(nums) <= 4:
            # Tipik başlıq: depo/kod, qaimə №, geriqaytarma №
            if is_return and len(nums) >= 2:
                return int(nums[-1])
            if len(nums) >= 2:
                return int(nums[1])
            if len(nums) == 1:
                return int(nums[0])
    return 0


def _is_return_document(text: str) -> bool:
    return bool(re.search(r'geri\s*qaytarma', text, re.IGNORECASE))


def _row_looks_like_header(row) -> bool:
    joined = ' '.join(str(cell or '') for cell in row).lower()
    keywords = ('malın adı', 'malin adi', 'miqdarı', 'miqdari', 'satış', 's.s')
    return any(word in joined for word in keywords)


def _row_looks_like_total(row) -> bool:
    joined = ' '.join(str(cell or '') for cell in row).lower()
    return 'cəmi' in joined or 'cemi' in joined or 'məbləğ' in joined


def _extract_items_from_table(rows) -> list[ParsedLineItem]:
    items = []
    name_idx = None
    qty_idx = None
    amount_idx = None

    for row in rows:
        if not row:
            continue
        cells = [str(cell or '').strip() for cell in row]
        if not any(cells):
            continue

        lower_cells = [c.lower() for c in cells]
        if _row_looks_like_header(row):
            for idx, cell in enumerate(lower_cells):
                if 'mal' in cell and 'ad' in cell:
                    name_idx = idx
                elif 'miqdar' in cell:
                    qty_idx = idx
                elif 'endirimli' in cell or ('məbləğ' in cell and 'satış' not in cell):
                    amount_idx = idx
            continue

        if _row_looks_like_total(row):
            continue

        if name_idx is None:
            if len(cells) >= 3 and cells[0].isdigit():
                name_idx, qty_idx, amount_idx = 1, 2, -1
            else:
                continue

        name = cells[name_idx] if name_idx < len(cells) else ''
        if not name or name.lower() in {'0', '-', '—'}:
            continue

        qty_col = qty_idx if qty_idx is not None and qty_idx < len(cells) else 2
        quantity = _parse_az_decimal(cells[qty_col] if qty_col < len(cells) else '0')
        if quantity <= 0:
            continue

        amount = Decimal('0')
        if amount_idx is not None and abs(amount_idx) < len(cells):
            amount = _parse_az_decimal(cells[amount_idx])
        elif len(cells) >= 2:
            amount = _parse_az_decimal(cells[-1])

        items.append(ParsedLineItem(
            name=_clean_drug_label(name) or _extract_drug_first_word(name),
            quantity=quantity,
            amount=amount,
        ))

    return items


def _extract_items_from_text(text: str) -> list[ParsedLineItem]:
    items = []
    pattern = re.compile(
        r'^\s*(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)',
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        name = _normalize_name(match.group(2))
        quantity = _parse_az_decimal(match.group(3))
        amount = _parse_az_decimal(match.group(4))
        if quantity > 0 and name and 'cəmi' not in name.lower():
            items.append(ParsedLineItem(
                name=_extract_drug_first_word(name),
                quantity=quantity,
                amount=amount,
            ))
    return items


def _dedupe_items(items: list[ParsedLineItem]) -> list[ParsedLineItem]:
    """Yan-yana iki nüsxə olanda eyni dərmanı təkrar yazma — yalnız birincisini saxla."""
    seen = set()
    result = []
    for item in items:
        key = _extract_drug_first_word(item.name).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _page_has_duplicate_forms(text: str) -> bool:
    lower = text.lower()
    if lower.count('solvey pharma') >= 2:
        return True
    if len(re.findall(r'müştəri|musteri|mushtəri', text, re.IGNORECASE)) >= 2:
        return True
    if len(re.findall(r'malın adı|malin adi', text, re.IGNORECASE)) >= 2:
        return True
    return False


def _single_form_page(page, side='left'):
    """PDF-də iki qaimə yan-yana olanda sol (qeyri rəsmi) və ya sağ (rəsmi) nüsxəni götür."""
    full_text = page.extract_text() or ''
    if _page_has_duplicate_forms(full_text):
        mid = page.width / 2
        if side == 'right':
            return page.crop((mid, 0, page.width, page.height))
        return page.crop((0, 0, mid, page.height))
    return page


def _extract_page_content(page, side='left'):
    full_text = page.extract_text() or ''
    form_page = _single_form_page(page, side=side)
    page_text = form_page.extract_text() or ''
    table_items = []
    for table in form_page.extract_tables() or []:
        table_items.extend(_extract_items_from_table(table))
    return full_text, page_text, table_items


def parse_qaime_pdf(uploaded_file, side='left') -> ParsedDocument:
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        full_text_parts = []
        form_text_parts = []
        table_items = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                full_page_text, page_text, page_tables = _extract_page_content(page, side=side)
                if full_page_text:
                    full_text_parts.append(full_page_text)
                if page_text:
                    form_text_parts.append(page_text)
                table_items.extend(page_tables)
                # pdfplumber səhifə keşini boşalt — RAM artımının qarşısı
                page.flush_cache()
                if hasattr(page, 'get_textmap'):
                    try:
                        page.get_textmap.cache_clear()
                    except Exception:
                        pass

        full_text = '\n'.join(full_text_parts)
        form_text = '\n'.join(form_text_parts) or full_text
        del full_text_parts, form_text_parts
        if not full_text.strip() and not table_items:
            raise QaimeParseError('PDF-dən mətn oxunmadı.')

        is_return = _is_return_document(form_text) or _is_return_document(full_text)
        aptek_name = _parse_aptek_name(form_text) or _parse_aptek_name(full_text)
        doc_date = _parse_doc_date(form_text) or _parse_doc_date(full_text)

        items = table_items or _extract_items_from_text(form_text)
        items = _dedupe_items(items)

        if not aptek_name:
            raise QaimeParseError('Aptek adı (Müştəri) tapılmadı.')
        if not doc_date:
            raise QaimeParseError('PDF-də tarix (Tarix) tapılmadı.')
        if not items:
            raise QaimeParseError('Dərman sətirləri tapılmadı.')

        total = sum((item.amount for item in items), Decimal('0'))

        return ParsedDocument(
            aptek_name=aptek_name,
            doc_date=doc_date,
            document_type='geri_qaytarma' if is_return else 'qaime',
            items=items,
            total=total,
            raw_text='',  # tam mətni saxlamırıq — RAM
        )
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _clean_official_party_name(raw: str) -> str:
    raw = (raw or '').strip()
    if not raw:
        return ''
    quoted = re.search(r'[«"„]([^»"“]+)[»"“]', raw)
    if quoted:
        return _normalize_name(quoted.group(1))
    name = re.split(r'\s+(?:VOEN|VÖEN|V[ÖO]EN)\b', raw, maxsplit=1, flags=re.IGNORECASE)[0]
    name = re.sub(
        r'\s*M[ƏE]HDUD\s+M[ƏE]SUL[İI]YY[ƏE]TL[İI].*$',
        '',
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r'\s*MMC\b.*$', '', name, flags=re.IGNORECASE)
    return _normalize_name(name.strip(' "«»'))


def _parse_official_party(text: str, label: str) -> str:
    """Elektron qaimə: Göndərən / Qəbul edən adını çıxar."""
    pattern = rf'{label}\s*:?\s*([^\n\r]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ''
    return _clean_official_party_name(match.group(1))


def _is_solvey_party(name: str) -> bool:
    """Qəbul edən/Göndərən SOLVEY MAXPHARMA-dırsa True."""
    folded = _fold_az(name or '')
    if not folded:
        return False
    return 'solvey' in folded and ('maxpharma' in folded or 'max' in folded or 'pharma' in folded)


def _resolve_official_direction(text: str) -> tuple[str, str]:
    """
    Qaimə: Göndərən=SOLVEY, Qəbul edən=aptek → document_type=qaime
    Geri qaytarma: Göndərən=aptek, Qəbul edən=SOLVEY → document_type=geri_qaytarma
    """
    sender = _parse_official_party(text, r'G[öo]nd[əe]r[əe]n')
    receiver = _parse_official_party(text, r'Q[əe]bul\s+ed[əe]n')

    if _is_solvey_party(receiver) and sender:
        return sender, 'geri_qaytarma'
    if _is_solvey_party(sender) and receiver:
        return receiver, 'qaime'
    if receiver and not _is_solvey_party(receiver):
        return receiver, 'qaime'
    if sender and not _is_solvey_party(sender):
        return sender, 'geri_qaytarma'
    return receiver or sender, 'qaime'


def _parse_official_date(text: str) -> date | None:
    match = re.search(
        r'Tarix\s*:?\s*(\d{2})\.(\d{2})\.(\d{4})',
        text,
        re.IGNORECASE,
    )
    if not match:
        return _parse_doc_date(text)
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_official_number(text: str) -> int:
    match = re.search(r'N[öo]mr[əe]\s*:?\s*(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def _extract_official_items_from_table(rows) -> list[ParsedLineItem]:
    """Yalnız Malın adı + Miqdarı (həcmi)."""
    items = []
    name_idx = None
    qty_idx = None

    for row in rows:
        if not row:
            continue
        cells = [str(cell or '').strip() for cell in row]
        if not any(cells):
            continue

        lower = [c.lower() for c in cells]
        joined = ' '.join(lower)
        if 'mal' in joined and 'ad' in joined and ('miqdar' in joined or name_idx is None):
            for idx, cell in enumerate(lower):
                if name_idx is None and 'mal' in cell and 'ad' in cell:
                    name_idx = idx
                if qty_idx is None and 'miqdar' in cell:
                    qty_idx = idx
            if name_idx is not None:
                continue

        if 'yekun' in joined or 'cəmi' in joined or 'cemi' in joined:
            continue

        # Header tapılmayıbsa: № | ad | kod | ... | miqdar(6-cı sütun)
        if name_idx is None:
            if len(cells) >= 6 and re.match(r'^\d+$', cells[0]):
                name_idx, qty_idx = 1, 5
            else:
                continue

        name = cells[name_idx] if name_idx < len(cells) else ''
        if not name or re.match(r'^\d+$', name):
            continue
        if 'malın' in name.lower() or 'malin' in name.lower():
            continue

        qty_col = qty_idx if qty_idx is not None else 5
        quantity = _parse_az_decimal(cells[qty_col] if qty_col < len(cells) else '0')
        if quantity <= 0:
            # Bəzən miqdar başqa yerdə olur — rəqəm sütunlarından axtar
            for cell in cells[2:]:
                val = _parse_az_decimal(cell)
                if val > 0 and '.' not in str(cell).replace(',', '.')[:1]:
                    # kodlar uzun olur (2106909800) — miqdar adətən kiçik
                    if val < Decimal('100000'):
                        quantity = val
                        break
        if quantity <= 0:
            continue

        items.append(ParsedLineItem(
            name=_clean_drug_label(name),
            quantity=quantity,
            amount=Decimal('0'),
        ))

    return items


def _extract_official_items_from_text(text: str) -> list[ParsedLineItem]:
    """Sətir: 1  Prostagold N10  3307900000  ...  80  ..."""
    items = []
    # № + ad (koddan əvvəl) + uzun HS kod + miqdar
    pattern = re.compile(
        r'(?m)^\s*(\d{1,3})\s+(.+?)\s+(\d{8,12})\b.*?(\d+(?:[.,]\d+)?)\s',
    )
    for match in pattern.finditer(text):
        name = _clean_drug_label(match.group(2))
        quantity = _parse_az_decimal(match.group(4))
        if not name or quantity <= 0:
            continue
        if 'yekun' in name.lower() or 'malın' in name.lower():
            continue
        # HS kodundan sonra gələn ilk «kiçik» ədəd bəzən ölçü vahidi ola bilər;
        # əgər quantity çox böyükdürsə (qiymət), növbəti rəqəmə bax
        if quantity >= Decimal('100000'):
            continue
        items.append(ParsedLineItem(name=name, quantity=quantity, amount=Decimal('0')))
    return _dedupe_items(items)


def parse_official_qaime_pdf(uploaded_file) -> ParsedDocument:
    """
    Rəsmi elektron qaimə-faktura:
    - Qaimə: Göndərən=SOLVEY, Qəbul edən=aptek → anbardan çıxış
    - Geri qaytarma: Göndərən=aptek, Qəbul edən=SOLVEY → anbara giriş
    Oxunanlar: aptek, Malın adı, Miqdarı (həcmi).
    """
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        text_parts = []
        table_items = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                if page_text:
                    text_parts.append(page_text)
                for table in page.extract_tables() or []:
                    table_items.extend(_extract_official_items_from_table(table))
                page.flush_cache()

        full_text = '\n'.join(text_parts)
        del text_parts
        if not full_text.strip() and not table_items:
            raise QaimeParseError('Rəsmi PDF-dən mətn oxunmadı.')

        aptek_name, document_type = _resolve_official_direction(full_text)
        doc_date = _parse_official_date(full_text)
        number = _parse_official_number(full_text)

        items = _dedupe_items(table_items) or _extract_official_items_from_text(full_text)
        del full_text

        if not aptek_name:
            raise QaimeParseError(
                'Aptek adı tapılmadı (Qaimə: Qəbul edən · Geri qaytarma: Göndərən).'
            )
        if _is_solvey_party(aptek_name):
            raise QaimeParseError(
                'Aptek adı SOLVEY kimi oxundu — Göndərən/Qəbul edən sahələrini yoxlayın.'
            )
        if not doc_date:
            raise QaimeParseError('Rəsmi PDF-də tarix tapılmadı.')
        if not items:
            raise QaimeParseError('Rəsmi PDF-də mal/miqdar sətirləri tapılmadı.')

        return ParsedDocument(
            aptek_name=aptek_name,
            number=number,
            doc_date=doc_date,
            document_type=document_type,
            items=items,
            total=Decimal('0'),
            raw_text='',
        )
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
