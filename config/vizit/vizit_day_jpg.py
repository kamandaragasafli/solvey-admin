from datetime import date
import re
from urllib.parse import quote

from django.core import signing
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import Istifadeci, Vizit
from .utils import vizit_login_required

_SHARE_SALT = "vizit-day-vizit-jpg"
_SHARE_MAX_AGE = 60 * 60 * 24 * 30


def _safe_filename(name):
    safe = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    safe = re.sub(r"\s+", " ", safe) or "Istifadeci"
    return safe


def _jpg_content_disposition(filename, disposition="inline"):
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "vizit.jpg"
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
    # Bu gün JPG: nümayəndə / menecer / rəhbər yalnız öz qeydləri
    if user_rol in (
        Istifadeci.ROL_NUMAYENDE,
        Istifadeci.ROL_MENECER,
        Istifadeci.ROL_REHBER,
    ):
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
                "hekim": v.hekim_ad_goster,
                "ixtisas": v.hekim_ixtisas_goster or "—",
                "kat": v.hekim_kat_goster or "—",
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


@vizit_login_required
def vizit_day_jpg(request):
    """Birbaşa JPG faylı yükləyir (paylaş üçün)"""
    if request.session.get("rol") not in (
        Istifadeci.ROL_NUMAYENDE,
        Istifadeci.ROL_MENECER,
        Istifadeci.ROL_REHBER,
    ):
        return HttpResponse("İcazə yoxdur", status=403)

    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    user_rol = request.session.get("rol")
    day = timezone.localdate()
    rows = _day_rows_for_user(user_id, day, user_rol)

    # HTML template render et
    html_content = render(
        request,
        'vizit/vizit_day_jpg_view.html',
        {
            'user_ad': user_ad,
            'day': day,
            'rows': rows,
        }
    ).content.decode('utf-8')

    # HTML-yə müvəqqəti CSS əlavə et - sabit genişlik
    extra_css = """
    <style>
    body, .vizit-container {
        width: 1400px !important;
        max-width: 1400px !important;
        min-width: 1400px !important;
    }
    </style>
    """
    html_content = html_content.replace('</head>', extra_css + '</head>')

    # html2image ilə JPG-ə çevir
    try:
        from html2image import Html2Image

        hti = Html2Image(size=(1400, 1400), browser='chrome')
        output_path = "vizit_temp.jpg"
        hti.screenshot(html_str=html_content, save_as=output_path)

        with open(output_path, 'rb') as f:
            jpg_bytes = f.read()

        import os
        if os.path.exists(output_path):
            os.remove(output_path)

        filename = f"{_safe_filename(user_ad)} Vizit.jpg"
        response = HttpResponse(jpg_bytes, content_type="image/jpeg")
        as_attachment = request.GET.get("download") == "1"
        disp = "attachment" if as_attachment else "inline"
        response["Content-Disposition"] = _jpg_content_disposition(filename, disp)
        return response
    except Exception as e:
        return HttpResponse(f"Xəta baş verdi: {str(e)}", status=500)


@vizit_login_required
def vizit_day_jpg_data(request):
    """JPG screenshot almaq üçün lazım olan məlumatları qaytarır"""
    if request.session.get("rol") not in (
        Istifadeci.ROL_NUMAYENDE,
        Istifadeci.ROL_MENECER,
        Istifadeci.ROL_REHBER,
    ):
        return JsonResponse({"success": False, "message": "İcazə yoxdur"}, status=403)

    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    user_rol = request.session.get("rol")
    day = timezone.localdate()
    rows = _day_rows_for_user(user_id, day, user_rol)

    return JsonResponse({
        "success": True,
        "user_ad": user_ad,
        "day": day.strftime("%d.%m.%Y"),
        "rows": rows,
    })


def vizit_day_shared_jpg(request, token):
    """Paylaşım linki ilə JPG göstərən view"""
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

    return render(
        request,
        'vizit/vizit_day_jpg_view.html',
        {
            'user_ad': user_ad,
            'day': day,
            'rows': rows,
        }
    )


def vizit_day_share_jpg_context(request):
    user_id = request.session.get("istifadeci_id")
    user_ad = request.session.get("ad") or "İstifadəçi"
    today = timezone.localdate()
    token = signing.dumps({"uid": user_id, "day": today.isoformat()}, salt=_SHARE_SALT)
    share_url = request.build_absolute_uri(
        reverse("vizit:vizit_day_shared_jpg", args=[token])
    )
    # Birbaşa JPG yükləmək üçün URL
    jpg_download_url = request.build_absolute_uri(
        reverse("vizit:vizit_day_jpg")
    )
    return {
        "user_ad": user_ad,
        "share_jpg_url": share_url,
        "jpg_download_url": jpg_download_url,
        "jpg_filename": f"{_safe_filename(user_ad)} Vizit.jpg",
        "today": today,
    }
