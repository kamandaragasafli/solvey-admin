from datetime import date
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import quote

from django.core import signing
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import AptekVizit, Istifadeci
from .utils import vizit_login_required

_PDF_FONTS_READY = False
_SHARE_SALT = "vizit-aptek-vizit-pdf"
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
    pdfmetrics.registerFont(TTFont("AV", str(regular)))
    pdfmetrics.registerFont(TTFont("AV-Bold", str(bold if bold.exists() else regular)))
    _PDF_FONTS_READY = True


def _safe_filename(name):
    safe = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    safe = re.sub(r"\s+", " ", safe) or "Istifadeci"
    return safe


def _pdf_content_disposition(filename, disposition="inline"):
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "aptek_vizit.pdf"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


def _ref_for_vizit(vizit):
    prep = vizit.preparatlar.first()
    return (prep.ref_vez if prep else "") or "—"


def _aptek_rows_for_user(user_id, day, user_rol=None):
    qs = (
        AptekVizit.objects.filter(tarix=day)
        .select_related("rayon", "bolge", "user")
        .prefetch_related("preparatlar")
        .order_by("vaxt", "id")
    )
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        qs = qs.filter(user_id=user_id)

    rows = []
    for v in qs:
        rows.append(
            {
                "aptek": v.aptek_ad or "—",
                "nomre": v.aptek_nomre or "—",
                "bolge": v.bolge.region_name if v.bolge_id else "—",
                "rayon": v.rayon.city_name if v.rayon_id else "—",
                "ref": _ref_for_vizit(v),
                "vaxt": v.vaxt.strftime("%H:%M") if v.vaxt else "",
                "user": v.user.ad if v.user_id else "—",
            }
        )
    return rows


def _build_aptek_vizit_pdf(user_ad, day, rows):
    _ensure_pdf_fonts()
    navy = HexColor("#1A5276")
    row_alt = HexColor("#F0F7FF")
    line = HexColor("#DCE6F0")
    ink = HexColor("#1C2833")

    buffer = BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    margin_x = 12 * mm
    margin_y = 12 * mm

    title = f"{user_ad} Aptek Viziti"
    subtitle = f"Tarix: {day:%d.%m.%Y}  ·  Cəmi: {len(rows)}"

    def draw_header(y_top):
        c.setFillColor(navy)
        c.setFont("AV-Bold", 14)
        c.drawString(margin_x, y_top, title)
        c.setFont("AV", 10)
        c.setFillColor(HexColor("#64748B"))
        c.drawString(margin_x, y_top - 6 * mm, subtitle)
        return y_top - 14 * mm

    headers = ["#", "Aptek", "Nömrə", "Bölgə", "Rayon", "Rəf", "Vaxt"]
    widths = [10 * mm, 55 * mm, 28 * mm, 45 * mm, 40 * mm, 45 * mm, 18 * mm]

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
        c.setFont("AV-Bold", 8)
        for i, h in enumerate(headers):
            col_x.append(x)
            c.drawString(x, y - 4.5 * mm, h)
            x += widths[i]
        return y - row_h - 1 * mm, col_x

    y = draw_header(page_h - margin_y)
    y, col_x = draw_table_header(y)

    if not rows:
        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("AV", 10)
        c.drawString(margin_x, y - 8 * mm, "Bu gün aptek viziti yoxdur.")
    else:
        c.setFont("AV", 8)
        row_h = 7.2 * mm
        for idx, r in enumerate(rows, 1):
            if y < margin_y + 16 * mm:
                c.showPage()
                y = draw_header(page_h - margin_y)
                y, col_x = draw_table_header(y)
                c.setFont("AV", 8)

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

            vals = [
                str(idx),
                r["aptek"],
                r["nomre"],
                r["bolge"],
                r["rayon"],
                r["ref"],
                r["vaxt"],
            ]
            c.setFillColor(ink)
            for i, val in enumerate(vals):
                text = val or "—"
                max_w = widths[i] - 1.5 * mm
                while c.stringWidth(text, "AV", 8) > max_w and len(text) > 3:
                    text = text[:-2] + "…"
                c.drawString(col_x[i], y - 3.8 * mm, text)
            y -= row_h

    c.save()
    buffer.seek(0)
    filename = f"{_safe_filename(user_ad)} Aptek Viziti.pdf"
    return buffer.getvalue(), filename


def _pdf_for_request_user(request, day=None):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    user_rol = request.session.get("rol")
    day = day or timezone.localdate()
    rows = _aptek_rows_for_user(user_id, day, user_rol)
    return _build_aptek_vizit_pdf(user_ad, day, rows)


@vizit_login_required
def aptek_vizit_pdf(request):
    pdf_bytes, filename = _pdf_for_request_user(request)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    as_attachment = request.GET.get("download") == "1"
    disp = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = _pdf_content_disposition(filename, disp)
    return response


def aptek_vizit_shared_pdf(request, token):
    try:
        data = signing.loads(token, salt=_SHARE_SALT, max_age=_SHARE_MAX_AGE)
        user_id = int(data["uid"])
        day = date.fromisoformat(data["day"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError):
        raise Http404("Paylaşım linki etibarsızdır və ya müddəti bitib.")

    user = Istifadeci.objects.filter(pk=user_id).first()
    user_ad = (user.ad if user else "") or "İstifadəçi"
    user_rol = user.rol if user else Istifadeci.ROL_NUMAYENDE
    rows = _aptek_rows_for_user(user_id, day, user_rol)
    pdf_bytes, filename = _build_aptek_vizit_pdf(user_ad, day, rows)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = _pdf_content_disposition(filename, "inline")
    return response


def aptek_vizit_share_context(request):
    """Səhifə üçün share_url / pdf_filename."""
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    today = timezone.localdate()
    token = signing.dumps({"uid": user_id, "day": today.isoformat()}, salt=_SHARE_SALT)
    share_url = request.build_absolute_uri(
        reverse("vizit:aptek_vizit_shared_pdf", args=[token])
    )
    return {
        "user_ad": user_ad,
        "share_url": share_url,
        "pdf_filename": f"{_safe_filename(user_ad)} Aptek Viziti.pdf",
    }
