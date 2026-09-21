from datetime import date
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import quote

from django.core import signing
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import Istifadeci, Vizit
from .utils import vizit_login_required

_PDF_FONTS_READY = False
_SHARE_SALT = "vizit-day-vizit-pdf"
_SHARE_MAX_AGE = 60 * 60 * 24 * 30


def _ensure_pdf_fonts():
    global _PDF_FONTS_READY
    if _PDF_FONTS_READY:
        return
    fonts = Path(r"C:\Windows\Fonts")
    regular = fonts / "arial.ttf"
    bold = fonts / "arialbd.ttf"
    if not regular.exists():
        regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    pdfmetrics.registerFont(TTFont("VD", str(regular)))
    pdfmetrics.registerFont(TTFont("VD-Bold", str(bold if bold.exists() else regular)))
    _PDF_FONTS_READY = True


def _safe_filename(name):
    safe = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    safe = re.sub(r"\s+", " ", safe) or "Istifadeci"
    return safe


def _pdf_content_disposition(filename, disposition="inline"):
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "vizit.pdf"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


def _day_rows_for_user(user_id, day, user_rol=None):
    qs = (
        Vizit.objects.filter(tarix=day)
        .select_related("hekim", "rayon", "bolge", "istifadeci")
        .prefetch_related("preparatlar__preparat")
        .order_by("vaxt", "id")
    )
    # Bu gün PDF: menecer və rəhbər yalnız öz qeydləri
    if user_rol in (Istifadeci.ROL_MENECER, Istifadeci.ROL_REHBER):
        qs = qs.filter(istifadeci_id=user_id)
    else:
        qs = qs.none()

    rows = []
    for v in qs:
        preps = [
            (vp.preparat.med_full_name or vp.preparat.med_name)
            for vp in v.preparatlar.all()
            if vp.preparat_id
        ]
        rows.append(
            {
                "hekim": v.hekim.ad if v.hekim_id else "—",
                "ixtisas": (v.hekim.ixtisas if v.hekim_id else "") or "—",
                "kat": (v.hekim.kategoriya if v.hekim_id else "") or "—",
                "rayon": (
                    v.rayon.get_city_name_display()
                    if v.rayon_id
                    else "—"
                ),
                "munasibat": v.munasibat or "—",
                "dermanlar": ", ".join(preps) if preps else "—",
                "qeyd": (v.qeyd or "").strip() or "—",
                "vaxt": v.vaxt.strftime("%H:%M") if v.vaxt else "",
                "user": v.istifadeci.ad if v.istifadeci_id else "—",
            }
        )
    return rows


def _break_long_token(c, token, font, size, max_w):
    """Enə sığmayan tək parçanı hərflərlə sətirlərə bölür."""
    if not token:
        return []
    if c.stringWidth(token, font, size) <= max_w:
        return [token]
    parts = []
    rest = token
    while rest:
        if c.stringWidth(rest, font, size) <= max_w:
            parts.append(rest)
            break
        lo, hi = 1, len(rest)
        cut = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if c.stringWidth(rest[:mid], font, size) <= max_w:
                cut = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if cut < 1:
            cut = 1
        parts.append(rest[:cut])
        rest = rest[cut:]
    return parts


def _wrap_text(c, text, font, size, max_w):
    """Mətni enə görə sətirlərə bölür (boşluqsuz uzun sözlər də)."""
    text = (text or "—").replace("\r", "\n").strip() or "—"
    # Əvvəlcə əl ilə yazılmış sətir sonlarını da nəzərə al
    raw_parts = []
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if chunk:
            raw_parts.extend(chunk.split())
        else:
            raw_parts.append("")
    if not raw_parts:
        return ["—"]

    lines = []
    current = ""
    for word in raw_parts:
        if word == "":
            if current:
                lines.append(current)
                current = ""
            continue
        # Əvvəlcə söz özü enə sığmırsa parçala
        pieces = _break_long_token(c, word, font, size, max_w)
        for piece in pieces:
            if not current:
                current = piece
                continue
            trial = f"{current} {piece}"
            if c.stringWidth(trial, font, size) <= max_w:
                current = trial
            else:
                lines.append(current)
                current = piece
    if current:
        lines.append(current)
    return lines or ["—"]


def _build_day_vizit_pdf(user_ad, day, rows):
    _ensure_pdf_fonts()
    navy = HexColor("#1A5276")
    row_alt = HexColor("#F0F7FF")
    line = HexColor("#DCE6F0")
    ink = HexColor("#1C2833")
    font_size = 7.5
    line_h = 3.6 * mm
    pad_y = 2.2 * mm

    buffer = BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    margin_x = 10 * mm
    margin_y = 10 * mm

    title = f"{user_ad} Vizit"
    subtitle = f"Tarix: {day:%d.%m.%Y}  ·  Cəmi: {len(rows)}"

    def draw_header(y_top):
        c.setFillColor(navy)
        c.setFont("VD-Bold", 14)
        c.drawString(margin_x, y_top, title)
        c.setFont("VD", 10)
        c.setFillColor(HexColor("#64748B"))
        c.drawString(margin_x, y_top - 6 * mm, subtitle)
        return y_top - 14 * mm

    # Rayon və Kateqoriya yoxdur; İxtisas qalır
    headers = ["#", "Həkim", "İxtisas", "Münasibət", "Dərmanlar", "Qeyd", "Vaxt"]
    widths = [8 * mm, 42 * mm, 18 * mm, 28 * mm, 95 * mm, 70 * mm, 16 * mm]

    def draw_table_header(y):
        x = margin_x
        col_x = []
        row_h = 8 * mm
        c.setFillColor(navy)
        c.roundRect(
            margin_x - 1 * mm,
            y - row_h + 2 * mm,
            page_w - 2 * margin_x + 2 * mm,
            row_h,
            3,
            stroke=0,
            fill=1,
        )
        c.setFillColor(white)
        c.setFont("VD-Bold", font_size)
        for i, h in enumerate(headers):
            col_x.append(x)
            c.drawString(x, y - 4.5 * mm, h)
            x += widths[i]
        return y - row_h - 1 * mm, col_x

    y = draw_header(page_h - margin_y)
    y, col_x = draw_table_header(y)

    if not rows:
        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("VD", 10)
        c.drawString(margin_x, y - 8 * mm, "Bu gün vizit yoxdur.")
    else:
        for idx, r in enumerate(rows, 1):
            vals = [
                str(idx),
                r["hekim"],
                r["ixtisas"],
                r["munasibat"],
                r["dermanlar"],
                r["qeyd"],
                r["vaxt"],
            ]
            wrapped = [
                _wrap_text(c, val, "VD", font_size, widths[i] - 1.5 * mm)
                for i, val in enumerate(vals)
            ]
            n_lines = max(len(lines) for lines in wrapped)
            row_h = max(7.2 * mm, n_lines * line_h + pad_y)

            if y - row_h < margin_y + 8 * mm:
                c.showPage()
                y = draw_header(page_h - margin_y)
                y, col_x = draw_table_header(y)

            if idx % 2 == 0:
                c.setFillColor(row_alt)
                c.rect(
                    margin_x - 1 * mm,
                    y - row_h + 2 * mm,
                    page_w - 2 * margin_x + 2 * mm,
                    row_h,
                    stroke=0,
                    fill=1,
                )

            c.setStrokeColor(line)
            c.setLineWidth(0.3)
            c.line(
                margin_x - 1 * mm,
                y - row_h + 2 * mm,
                page_w - margin_x + 1 * mm,
                y - row_h + 2 * mm,
            )

            c.setFillColor(ink)
            c.setFont("VD", font_size)
            for i, lines in enumerate(wrapped):
                text_y = y - 3.2 * mm
                for line_text in lines:
                    c.drawString(col_x[i], text_y, line_text)
                    text_y -= line_h
            y -= row_h

    c.save()
    buffer.seek(0)
    filename = f"{_safe_filename(user_ad)} Vizit.pdf"
    return buffer.getvalue(), filename


def _pdf_for_request_user(request, day=None):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    user_rol = request.session.get("rol")
    day = day or timezone.localdate()
    rows = _day_rows_for_user(user_id, day, user_rol)
    return _build_day_vizit_pdf(user_ad, day, rows)


@vizit_login_required
def vizit_day_pdf(request):
    if request.session.get("rol") not in (Istifadeci.ROL_MENECER, Istifadeci.ROL_REHBER):
        return redirect("vizit:index")
    pdf_bytes, filename = _pdf_for_request_user(request)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    as_attachment = request.GET.get("download") == "1"
    disp = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = _pdf_content_disposition(filename, disp)
    return response


def vizit_day_shared_pdf(request, token):
    try:
        data = signing.loads(token, salt=_SHARE_SALT, max_age=_SHARE_MAX_AGE)
        user_id = int(data["uid"])
        day = date.fromisoformat(data["day"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError):
        raise Http404("Paylaşım linki etibarsızdır və ya müddəti bitib.")

    user = Istifadeci.objects.filter(pk=user_id).first()
    user_ad = (user.ad if user else "") or "İstifadəçi"
    user_rol = user.rol if user else Istifadeci.ROL_NUMAYENDE
    rows = _day_rows_for_user(user_id, day, user_rol)
    pdf_bytes, filename = _build_day_vizit_pdf(user_ad, day, rows)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = _pdf_content_disposition(filename, "inline")
    return response


def vizit_day_share_context(request):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    today = timezone.localdate()
    token = signing.dumps({"uid": user_id, "day": today.isoformat()}, salt=_SHARE_SALT)
    share_url = request.build_absolute_uri(
        reverse("vizit:vizit_day_shared_pdf", args=[token])
    )
    return {
        "user_ad": user_ad,
        "share_url": share_url,
        "pdf_filename": f"{_safe_filename(user_ad)} Vizit.pdf",
        "today": today,
    }
