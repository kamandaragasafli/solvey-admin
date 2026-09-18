from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import quote

from django.core import signing
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import DayRecipe, DayRecipeDrug, Istifadeci
from .utils import vizit_login_required

_PDF_FONTS_READY = False
_SHARE_SALT = "vizit-day-recipe-pdf"
_SHARE_MAX_AGE = 60 * 60 * 24 * 30

NAVY = HexColor("#1A5276")
HEADER_BG = HexColor("#1A5276")
ROW_ALT = HexColor("#F0F7FF")
GRID = HexColor("#B0C4DE")
INK = HexColor("#1C2833")
MUTED = HexColor("#64748B")


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
    pdfmetrics.registerFont(TTFont("DR", str(regular)))
    pdfmetrics.registerFont(TTFont("DR-Bold", str(bold if bold.exists() else regular)))
    _PDF_FONTS_READY = True


def _safe_filename(name):
    safe = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    safe = re.sub(r"\s+", " ", safe) or "Istifadeci"
    return safe


def _pdf_content_disposition(filename, disposition="inline"):
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "gunluk_qeydiyyat.pdf"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


def _fmt_qty(n):
    n = float(n)
    if n == int(n):
        return f"{int(n)}"
    return f"{n:g}"


def _esc(text):
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _day_recipe_qs_for_user(user_id, day, user_rol=None):
    qs = (
        DayRecipe.objects.filter(date=day)
        .select_related("dr", "region", "created_by")
        .prefetch_related(
            Prefetch(
                "drugs",
                queryset=DayRecipeDrug.objects.select_related("drug").order_by("id"),
            )
        )
        .order_by("created_at", "id")
    )
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        qs = qs.filter(created_by_id=user_id)
    return qs


def _day_recipe_rows(user_id, day, user_rol=None):
    rows = []
    total_qty = Decimal("0")
    for recipe in _day_recipe_qs_for_user(user_id, day, user_rol):
        drugs = []
        row_qty = Decimal("0")
        for line in recipe.drugs.all():
            if line.number and float(line.number) > 0:
                name = line.drug.med_full_name or line.drug.med_name
                qty = Decimal(str(line.number))
                row_qty += qty
                drugs.append(f"{name} ({_fmt_qty(qty)})")
        total_qty += row_qty
        rows.append(
            {
                "hekim": recipe.dr.ad if recipe.dr_id else "—",
                "ixtisas": (recipe.dr.ixtisas if recipe.dr_id else "") or "—",
                "bolge": recipe.region.region_name if recipe.region_id else "—",
                "dermanlar": ", ".join(drugs) if drugs else "—",
                "say": _fmt_qty(row_qty) if row_qty else "—",
                "vaxt": (
                    timezone.localtime(recipe.created_at).strftime("%H:%M")
                    if recipe.created_at
                    else ""
                ),
            }
        )
    return rows, total_qty


def _build_day_recipe_pdf(user_ad, day, rows, total_qty):
    _ensure_pdf_fonts()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    style_title = ParagraphStyle(
        "DRTitle",
        fontName="DR-Bold",
        fontSize=15,
        textColor=NAVY,
        spaceAfter=2 * mm,
        leading=18,
    )
    style_sub = ParagraphStyle(
        "DRSub",
        fontName="DR",
        fontSize=10,
        textColor=MUTED,
        spaceAfter=6 * mm,
        leading=13,
    )
    style_th = ParagraphStyle(
        "DRTh",
        fontName="DR-Bold",
        fontSize=8,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=11,
    )
    style_td = ParagraphStyle(
        "DRTd",
        fontName="DR",
        fontSize=8,
        textColor=INK,
        alignment=TA_LEFT,
        leading=11,
    )
    style_td_c = ParagraphStyle(
        "DRTdC",
        fontName="DR",
        fontSize=8,
        textColor=INK,
        alignment=TA_CENTER,
        leading=11,
    )
    style_foot = ParagraphStyle(
        "DRFoot",
        fontName="DR-Bold",
        fontSize=9,
        textColor=NAVY,
        alignment=TA_LEFT,
        leading=12,
    )

    story = []
    story.append(Paragraph(_esc(f"{user_ad} Günlük Qeydiyyat"), style_title))
    story.append(
        Paragraph(
            _esc(
                f"Tarix: {day:%d.%m.%Y}  ·  Cəmi resept: {len(rows)}  ·  "
                f"Ümumi dərman sayı: {_fmt_qty(total_qty)}"
            ),
            style_sub,
        )
    )

    col_widths = [
        10 * mm,   # #
        42 * mm,   # Həkim
        18 * mm,   # İxtisas
        36 * mm,   # Bölgə
        120 * mm,  # Dərmanlar
        18 * mm,   # Say
        16 * mm,   # Vaxt
    ]

    header = [
        Paragraph("#", style_th),
        Paragraph("Həkim", style_th),
        Paragraph("İxtisas", style_th),
        Paragraph("Bölgə", style_th),
        Paragraph("Dərmanlar", style_th),
        Paragraph("Say", style_th),
        Paragraph("Vaxt", style_th),
    ]
    data = [header]

    if not rows:
        data.append(
            [
                Paragraph("—", style_td_c),
                Paragraph("Bu gün qeydiyyat yoxdur.", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
            ]
        )
    else:
        for idx, r in enumerate(rows, 1):
            data.append(
                [
                    Paragraph(str(idx), style_td_c),
                    Paragraph(_esc(r["hekim"]), style_td),
                    Paragraph(_esc(r["ixtisas"]), style_td_c),
                    Paragraph(_esc(r["bolge"]), style_td),
                    Paragraph(_esc(r["dermanlar"]), style_td),
                    Paragraph(_esc(r["say"]), style_td_c),
                    Paragraph(_esc(r["vaxt"]), style_td_c),
                ]
            )
        # Cəm sətiri
        data.append(
            [
                Paragraph("", style_td),
                Paragraph("CƏMİ", style_foot),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph(
                    _esc(f"{len(rows)} resept"),
                    style_foot,
                ),
                Paragraph(_esc(_fmt_qty(total_qty)), style_foot),
                Paragraph("", style_td),
            ]
        )

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DR-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.6, GRID),
        ("BOX", (0, 0), (-1, -1), 1.2, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
    ]
    # Alternating rows (skip header and last total row)
    last_data = len(data) - 1
    for i in range(1, last_data if rows else 2):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    if rows:
        style_cmds.append(("BACKGROUND", (0, -1), (-1, -1), HexColor("#E8F1FA")))

    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            _esc(
                f"Yekun: {len(rows)} qeydiyyat · Ümumi dərman sayı: {_fmt_qty(total_qty)}"
            ),
            style_sub,
        )
    )

    doc.build(story)
    buffer.seek(0)
    filename = f"{_safe_filename(user_ad)} Günlük Qeydiyyat.pdf"
    return buffer.getvalue(), filename


def _pdf_for_request_user(request, day=None):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    user_rol = request.session.get("rol")
    day = day or timezone.localdate()
    rows, total_qty = _day_recipe_rows(user_id, day, user_rol)
    return _build_day_recipe_pdf(user_ad, day, rows, total_qty)


@vizit_login_required
def day_recipe_pdf(request):
    pdf_bytes, filename = _pdf_for_request_user(request)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    as_attachment = request.GET.get("download") == "1"
    disp = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = _pdf_content_disposition(filename, disp)
    return response


def day_recipe_shared_pdf(request, token):
    try:
        data = signing.loads(token, salt=_SHARE_SALT, max_age=_SHARE_MAX_AGE)
        user_id = int(data["uid"])
        day = date.fromisoformat(data["day"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError):
        raise Http404("Paylaşım linki etibarsızdır və ya müddəti bitib.")

    user = Istifadeci.objects.filter(pk=user_id).first()
    user_ad = (user.ad if user else "") or "İstifadəçi"
    user_rol = user.rol if user else Istifadeci.ROL_NUMAYENDE
    rows, total_qty = _day_recipe_rows(user_id, day, user_rol)
    pdf_bytes, filename = _build_day_recipe_pdf(user_ad, day, rows, total_qty)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = _pdf_content_disposition(filename, "inline")
    return response


def day_recipe_share_context(request):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    today = timezone.localdate()
    token = signing.dumps({"uid": user_id, "day": today.isoformat()}, salt=_SHARE_SALT)
    share_url = request.build_absolute_uri(
        reverse("vizit:day_recipe_shared_pdf", args=[token])
    )
    return {
        "user_ad": user_ad,
        "share_url": share_url,
        "pdf_filename": f"{_safe_filename(user_ad)} Günlük Qeydiyyat.pdf",
        "today": today,
    }
