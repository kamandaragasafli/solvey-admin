import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pdfplumber

from medicine.models import Medical

NAME_ALIASES = {
    'peynstop': 'painstop',
    'moksivista': 'moxivista',
    'ropsol': 'ropsol',
    'fesola': 'fesola',
    'speraktiv': 'speraktiv',
    'lipomaq+': 'lipomaq+',
    'feelon': 'feelon',
    'provital': 'provital',
}


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


def find_drug(label: str):
    base = _extract_drug_first_word(label)
    if not base:
        return None

    candidates = [base]
    alias = NAME_ALIASES.get(base.lower())
    if alias:
        candidates.append(alias)

    for name in candidates:
        drug = Medical.objects.filter(med_name__iexact=name).first()
        if drug:
            return drug
        drug = Medical.objects.filter(med_full_name__iexact=name).first()
        if drug:
            return drug

    drug = (
        Medical.objects.filter(med_name__istartswith=base)
        .order_by('med_name')
        .first()
    )
    if drug:
        return drug

    return Medical.objects.filter(med_full_name__istartswith=base).order_by('med_full_name').first()


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
            name=_extract_drug_first_word(name),
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


def _single_form_page(page):
    """PDF-də iki qaimə yan-yana olanda yalnız sol nüsxəni götür."""
    full_text = page.extract_text() or ''
    if _page_has_duplicate_forms(full_text):
        return page.crop((0, 0, page.width / 2, page.height))
    return page


def _extract_page_content(page):
    full_text = page.extract_text() or ''
    form_page = _single_form_page(page)
    page_text = form_page.extract_text() or ''
    table_items = []
    for table in form_page.extract_tables() or []:
        table_items.extend(_extract_items_from_table(table))
    return full_text, page_text, table_items


def parse_qaime_pdf(uploaded_file) -> ParsedDocument:
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
                full_page_text, page_text, page_tables = _extract_page_content(page)
                if full_page_text:
                    full_text_parts.append(full_page_text)
                if page_text:
                    form_text_parts.append(page_text)
                table_items.extend(page_tables)

        full_text = '\n'.join(full_text_parts)
        form_text = '\n'.join(form_text_parts) or full_text
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
            raw_text=full_text,
        )
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
