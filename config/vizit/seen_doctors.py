from io import BytesIO
from pathlib import Path
from datetime import date
import re
from urllib.parse import quote

from django.core import signing
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from doctors.models import Doctors
from regions.models import Region

from .models import GorulenHekim, Istifadeci
from .utils import vizit_login_required

_PDF_FONTS_READY = False
_SHARE_SALT = "vizit-seen-doctors-pdf"
_SHARE_MAX_AGE = 60 * 60 * 24 * 30  # 30 gün


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
    pdfmetrics.registerFont(TTFont("SD", str(regular)))
    pdfmetrics.registerFont(TTFont("SD-Bold", str(bold if bold.exists() else regular)))
    _PDF_FONTS_READY = True


def _safe_filename(name):
    safe = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    safe = re.sub(r"\s+", " ", safe) or "Istifadeci"
    return safe


def _pdf_content_disposition(filename, disposition="inline"):
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "gorulen_hekimler.pdf"
    return (
        f'{disposition}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


def _bolgeler_for_user(user_rol, user_bolge_ids):
    if user_rol in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        return Region.objects.order_by("region_name")
    return Region.objects.filter(pk__in=user_bolge_ids).order_by("region_name")


def _can_access_bolge(user_rol, user_bolge_ids, bolge_id):
    if user_rol in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        return True
    return bolge_id in (user_bolge_ids or [])


def _doctor_payload(doctor):
    return {
        "id": doctor.id,
        "ad": doctor.ad,
        "ixtisas": doctor.get_ixtisas_display() if doctor.ixtisas else "",
        "klinika": doctor.klinika.hospital_name if doctor.klinika_id else "",
        "bolge": doctor.bolge.region_name if doctor.bolge_id else "",
    }


def _seen_rows_for_user(user_id, day):
    seen_qs = (
        GorulenHekim.objects.filter(istifadeci_id=user_id, seen_date=day)
        .select_related("hekim", "hekim__klinika", "bolge")
        .order_by("seen_at")
    )
    return [
        {
            "id": g.hekim_id,
            "ad": g.hekim.ad if g.hekim_id else "—",
            "ixtisas": g.hekim.get_ixtisas_display() if g.hekim_id and g.hekim.ixtisas else "",
            "klinika": (
                g.hekim.klinika.hospital_name
                if g.hekim_id and g.hekim.klinika_id
                else ""
            ),
            "bolge": g.bolge.region_name if g.bolge_id else "",
            "vaxt": timezone.localtime(g.seen_at).strftime("%H:%M"),
        }
        for g in seen_qs
    ]


def _build_seen_doctors_pdf(user_ad, day, rows):
    _ensure_pdf_fonts()
    navy = HexColor("#1A5276")
    header_bg = HexColor("#1A5276")
    row_alt = HexColor("#F0F7FF")
    line = HexColor("#DCE6F0")
    ink = HexColor("#1C2833")

    buffer = BytesIO()
    page_w, page_h = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    margin_x = 14 * mm
    margin_y = 14 * mm

    title = f"{user_ad} Görülən həkimlər"
    subtitle = f"Tarix: {day:%d.%m.%Y}  ·  Cəmi: {len(rows)}"

    def draw_header(y_top):
        c.setFillColor(navy)
        c.setFont("SD-Bold", 14)
        c.drawString(margin_x, y_top, title)
        c.setFont("SD", 10)
        c.setFillColor(HexColor("#64748B"))
        c.drawString(margin_x, y_top - 6 * mm, subtitle)
        return y_top - 14 * mm

    def draw_table_header(y):
        col_x = [
            margin_x,
            margin_x + 10 * mm,
            margin_x + 55 * mm,
            margin_x + 78 * mm,
            margin_x + 118 * mm,
            margin_x + 155 * mm,
        ]
        headers = ["#", "Həkim", "İxtisas", "Klinika", "Bölgə", "Vaxt"]
        widths = [10 * mm, 45 * mm, 23 * mm, 40 * mm, 37 * mm, 18 * mm]
        row_h = 8 * mm
        c.setFillColor(header_bg)
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
        c.setFont("SD-Bold", 8)
        for i, h in enumerate(headers):
            c.drawString(col_x[i], y - 4.5 * mm, h)
        return y - row_h - 1 * mm, col_x, widths

    y = draw_header(page_h - margin_y)
    y, col_x, widths = draw_table_header(y)

    if not rows:
        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("SD", 10)
        c.drawString(margin_x, y - 8 * mm, "Bu gün görülən həkim yoxdur.")
    else:
        c.setFont("SD", 8)
        row_h = 7.2 * mm
        for idx, r in enumerate(rows, 1):
            if y < margin_y + 20 * mm:
                c.showPage()
                y = draw_header(page_h - margin_y)
                y, col_x, widths = draw_table_header(y)
                c.setFont("SD", 8)

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
                r["ad"] or "—",
                r["ixtisas"] or "—",
                r["klinika"] or "—",
                r["bolge"] or "—",
                r["vaxt"] or "",
            ]
            c.setFillColor(ink)
            for i, val in enumerate(vals):
                text = val
                max_w = widths[i] - 1 * mm
                while c.stringWidth(text, "SD", 8) > max_w and len(text) > 3:
                    text = text[:-2] + "…"
                c.drawString(col_x[i], y - 3.8 * mm, text)
            y -= row_h

    c.save()
    buffer.seek(0)
    filename = f"{_safe_filename(user_ad)} Görülən həkimlər.pdf"
    return buffer.getvalue(), filename


@vizit_login_required
def seen_doctors_page(request):
    user_id = request.session.get("istifadeci_id")
    user_rol = request.session.get("rol")
    user_bolge_ids = request.session.get("bolge_ids", [])
    user_ad = request.session.get("ad") or "İstifadəçi"
    bolgeler = _bolgeler_for_user(user_rol, user_bolge_ids)

    today = timezone.localdate()
    bolge_id = (request.GET.get("bolge_id") or "").strip()
    selected_bolge = None
    doctors = []
    seen_ids = set()

    if bolge_id.isdigit():
        bolge_id_int = int(bolge_id)
        if _can_access_bolge(user_rol, user_bolge_ids, bolge_id_int):
            selected_bolge = Region.objects.filter(pk=bolge_id_int).first()
            if selected_bolge:
                doctors = list(
                    Doctors.objects.filter(bolge_id=bolge_id_int, is_active=True)
                    .select_related("klinika", "bolge")
                    .order_by("ad")
                )
                seen_ids = set(
                    GorulenHekim.objects.filter(
                        istifadeci_id=user_id,
                        bolge_id=bolge_id_int,
                        seen_date=today,
                    ).values_list("hekim_id", flat=True)
                )

    rows = [
        {
            **_doctor_payload(d),
            "seen": d.id in seen_ids,
        }
        for d in doctors
    ]

    seen_rows_raw = (
        GorulenHekim.objects.filter(istifadeci_id=user_id, seen_date=today)
        .select_related("hekim", "hekim__klinika", "bolge")
        .order_by("-seen_at")
    )
    seen_rows = [
        {
            "id": g.hekim_id,
            "ad": g.hekim.ad if g.hekim_id else "—",
            "ixtisas": g.hekim.get_ixtisas_display() if g.hekim_id and g.hekim.ixtisas else "",
            "klinika": (
                g.hekim.klinika.hospital_name
                if g.hekim_id and g.hekim.klinika_id
                else ""
            ),
            "bolge": g.bolge.region_name if g.bolge_id else "",
            "vaxt": g.seen_at,
        }
        for g in seen_rows_raw
    ]

    token = signing.dumps(
        {"uid": user_id, "day": today.isoformat()},
        salt=_SHARE_SALT,
    )
    share_url = request.build_absolute_uri(
        reverse("vizit:seen_doctors_shared_pdf", args=[token])
    )
    pdf_filename = f"{_safe_filename(user_ad)} Görülən həkimlər.pdf"

    return render(
        request,
        "vizit/seen-doctors.html",
        {
            "bolgeler": bolgeler,
            "selected_bolge_id": selected_bolge.id if selected_bolge else "",
            "selected_bolge": selected_bolge,
            "doctors": rows,
            "seen_count": len(seen_ids) if selected_bolge else len(seen_rows),
            "total_count": len(rows),
            "today": today,
            "user_ad": user_ad,
            "seen_rows": seen_rows,
            "seen_total": len(seen_rows),
            "share_url": share_url,
            "pdf_filename": pdf_filename,
        },
    )


@vizit_login_required
def seen_doctors_pdf(request):
    """Bugünkü görülən həkimlər siyahısının PDF-i."""
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    today = timezone.localdate()
    rows = _seen_rows_for_user(user_id, today)
    pdf_bytes, filename = _build_seen_doctors_pdf(user_ad, today, rows)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    as_attachment = request.GET.get("download") == "1"
    disp = "attachment" if as_attachment else "inline"
    response["Content-Disposition"] = _pdf_content_disposition(filename, disp)
    return response


def seen_doctors_shared_pdf(request, token):
    """Login olmadan açılan müvəqqəti paylaşım linki (30 gün)."""
    try:
        data = signing.loads(token, salt=_SHARE_SALT, max_age=_SHARE_MAX_AGE)
        user_id = int(data["uid"])
        day = date.fromisoformat(data["day"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError):
        raise Http404("Paylaşım linki etibarsızdır və ya müddəti bitib.")

    user = Istifadeci.objects.filter(pk=user_id).first()
    user_ad = (user.ad if user else "") or "İstifadəçi"
    rows = _seen_rows_for_user(user_id, day)
    pdf_bytes, filename = _build_seen_doctors_pdf(user_ad, day, rows)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = _pdf_content_disposition(filename, "inline")
    return response


@vizit_login_required
@require_POST
def seen_doctors_toggle(request):
    user_id = request.session.get("istifadeci_id")
    user_rol = request.session.get("rol")
    user_bolge_ids = request.session.get("bolge_ids", [])
    hekim_id = (request.POST.get("hekim_id") or "").strip()
    bolge_id = (request.POST.get("bolge_id") or "").strip()

    if not hekim_id.isdigit() or not bolge_id.isdigit():
        return JsonResponse({"ok": False, "error": "Yanlış sorğu"}, status=400)

    hekim_id_int = int(hekim_id)
    bolge_id_int = int(bolge_id)

    if not _can_access_bolge(user_rol, user_bolge_ids, bolge_id_int):
        return JsonResponse({"ok": False, "error": "İcazə yoxdur"}, status=403)

    doctor = (
        Doctors.objects.filter(pk=hekim_id_int, bolge_id=bolge_id_int, is_active=True)
        .select_related("klinika", "bolge")
        .first()
    )
    if not doctor:
        return JsonResponse({"ok": False, "error": "Həkim tapılmadı"}, status=404)

    today = timezone.localdate()
    existing = GorulenHekim.objects.filter(
        istifadeci_id=user_id,
        hekim_id=hekim_id_int,
        seen_date=today,
    ).first()

    if existing:
        existing.delete()
        return JsonResponse({"ok": True, "seen": False, "doctor": _doctor_payload(doctor)})

    rec = GorulenHekim.objects.create(
        istifadeci_id=user_id,
        hekim_id=hekim_id_int,
        bolge_id=bolge_id_int,
        seen_date=today,
    )
    payload = _doctor_payload(doctor)
    payload["vaxt"] = timezone.localtime(rec.seen_at).strftime("%H:%M")
    return JsonResponse({"ok": True, "seen": True, "doctor": payload})
