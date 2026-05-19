# ================================================================
# KƏNAR SERVERƏ GÖNDƏR — Django tərəfindən əlavə edilməli kod
# ================================================================
# Məqsəd: Solvey Pharma vizit sisteminin həkim datasını çəkməsi üçün
#         sadə bir JSON API endpoint-i açmaq.
#
# 2 fayla əlavə lazımdır: views.py və urls.py
# ================================================================


# ── views.py-a əlavə et ─────────────────────────────────────────
from django.http import JsonResponse
from .models import Doctors  # öz app adınla dəyiş

def hekim_api(request):
    """
    Solvey Pharma Vizit Sistemi üçün həkim API-si.
    Yalnız gizli açar ilə əlçatan olur.
    """
    # Təhlükəsizlik açarı
    if request.GET.get('key', '') != 'SolveyApi2024':
        return JsonResponse({'error': 'forbidden'}, status=403)

    hekimler = (
        Doctors.objects
        .filter(is_active=True)
        .select_related('bolge', 'city', 'klinika')
        .values(
            'id',
            'ad',
            'ixtisas',
            'kategoriya',
            'derece',
            'cinsiyyet',
            'bolge__region_name',
            'city__city_name',
            'klinika__hospital_name',
        )
        .order_by('bolge__region_name', 'ad')
    )

    return JsonResponse(list(hekimler), safe=False, json_dumps_params={'ensure_ascii': False})


# ── urls.py-a əlavə et ──────────────────────────────────────────
# (project/urls.py və ya app/urls.py - hansı uyğundursa)

from django.urls import path
from . import views

urlpatterns = [
    # ... mövcud url-lər ...
    path('api/hekimler/', views.hekim_api, name='hekim_api'),
]


# ── Yoxlama ─────────────────────────────────────────────────────
# Server işlədikdən sonra brauzerdən yoxla:
#   http://64.226.72.85/api/hekimler/?key=SolveyApi2024
#
# Gözlənilən cavab formatı:
# [
#   {
#     "id": 1,
#     "ad": "Əliyev Kamran",
#     "ixtisas": "UR",
#     "kategoriya": "A",
#     "derece": "VIP",
#     "cinsiyyet": "Kişi",
#     "bolge__region_name": "Bakı",
#     "city__city_name": "Sumqayıt",
#     "klinika__hospital_name": "Şəhər Xəstəxanası"
#   },
#   ...
# ]
