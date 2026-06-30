from doctors.models import Doctors, Recipe, RecipeDrug
from regions.models import Region
from payment.models import MonthlyDoctorReport
from django.db.models import Count, Sum, Q
from datetime import datetime
from decimal import Decimal
import uuid as _uuid
from django.core.cache import cache as _cache
from django.utils import timezone


# ====================== DATABASE QUERY FUNKSIYALARI ======================

def get_recent_doctors(limit=10):
    doctors = Doctors.objects.select_related('bolge', 'city', 'klinika').order_by('-created_at')[:limit]
    return [
        {
            'id': d.id,
            'ad': d.ad,
            'barkod': d.barkod or 'Yoxdur',
            'bolge': getattr(d.bolge, 'region_name', 'Yoxdur'),
            'city': getattr(d.city, 'city_name', 'Yoxdur'),
            'klinika': getattr(d.klinika, 'hospital_name', 'Yoxdur'),
            'ixtisas': d.get_ixtisas_display(),
            'derece': d.get_derece_display(),
            'created_at': d.created_at.strftime('%Y-%m-%d') if d.created_at else None
        }
        for d in doctors
    ]


def get_doctor_statistics():
    today = datetime.now()
    total = Doctors.objects.count()
    this_month = Doctors.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    by_degree = dict(Doctors.objects.values('derece').annotate(count=Count('id')).values_list('derece', 'count'))
    by_region = dict(Doctors.objects.values('bolge__region_name').annotate(count=Count('id')).values_list('bolge__region_name', 'count'))
    return {
        'total_doctors': total,
        'new_this_month': this_month,
        'by_degree': by_degree,
        'by_region': by_region,
    }


def get_region_statistics():
    regions = Region.objects.annotate(
        doctor_count=Count('doctors'),
        city_count=Count('cities'),
        hospital_count=Count('hospital_set')
    )
    return [
        {
            'region_name': r.region_name,
            'region_type': r.get_region_type_display() or 'Yoxdur',
            'doctor_count': r.doctor_count,
            'city_count': r.city_count,
            'hospital_count': r.hospital_count
        }
        for r in regions
    ]


def search_doctors(query: str, limit=10):
    doctors = Doctors.objects.filter(
        Q(ad__icontains=query) |
        Q(barkod__icontains=query) |
        Q(bolge__region_name__icontains=query)
    ).select_related('bolge')[:limit]
    return [
        {
            'id': d.id,
            'ad': d.ad,
            'barkod': d.barkod or 'Yoxdur',
            'bolge': getattr(d.bolge, 'region_name', 'Yoxdur'),
            'ixtisas': d.get_ixtisas_display(),
        }
        for d in doctors
    ]


def get_financial_summary():
    total_debt = Doctors.objects.aggregate(total=Sum('yekun_borc', default=Decimal('0')))['total'] or 0
    doctors_with_debt = Doctors.objects.filter(yekun_borc__gt=0).count()
    return {
        'total_debt': float(total_debt),
        'doctors_with_debt': doctors_with_debt,
        'total_doctors': Doctors.objects.count()
    }


def get_doctors_by_region(region_name: str, limit=20):
    doctors = Doctors.objects.filter(bolge__region_name__icontains=region_name).select_related('bolge', 'city', 'klinika')[:limit]
    return [
        {
            'id': d.id,
            'ad': d.ad,
            'barkod': d.barkod or 'Yoxdur',
            'bolge': getattr(d.bolge, 'region_name', ''),
            'ixtisas': d.get_ixtisas_display(),
            'yekun_borc': float(getattr(d, 'yekun_borc', 0))
        }
        for d in doctors
    ]


def get_doctor_financial_details(doctor_name: str, limit: int = 5):
    doctors = Doctors.objects.filter(ad__icontains=doctor_name).select_related('bolge', 'city', 'klinika')[:limit]
    result = []
    for doctor in doctors:
        financial = {
            'doctor_id': doctor.id,
            'ad': doctor.ad,
            'barkod': doctor.barkod or '',
            'bolge': getattr(doctor.bolge, 'region_name', ''),
            'previous_debt': float(getattr(doctor, 'previous_debt', 0)),
            'yekun_borc': float(getattr(doctor, 'yekun_borc', 0)),
            'borc': float(getattr(doctor, 'borc', 0)),
        }
        payments_qs = doctor.odenisler.filter(is_closed=False).order_by('-date')[:10]
        financial['payments'] = [{'pay': float(p.pay or 0), 'date': p.date.strftime('%Y-%m-%d') if p.date else ''} for p in payments_qs]
        result.append(financial)
    return result


def get_doctor_prescription_stats(doctor_name: str, year: int = None, month: int = None, day: int = None):
    today = datetime.now()
    year = year or today.year
    month = month or today.month
    doctor = Doctors.objects.filter(ad__icontains=doctor_name).first()
    if not doctor:
        return {'doctor_found': False, 'message': 'Bu ada uyğun həkim tapılmadı.'}
    recipes = Recipe.objects.filter(dr=doctor, date__year=year)
    if month:
        recipes = recipes.filter(date__month=month)
    if day:
        recipes = recipes.filter(date__day=day)
    total_recipes = recipes.count()
    drugs_qs = RecipeDrug.objects.filter(recipe__in=recipes).values('drug__med_name').annotate(total_count=Sum('number')).order_by('-total_count')
    drugs = [{'name': d['drug__med_name'], 'count': float(d['total_count'] or 0)} for d in drugs_qs]
    return {
        'doctor_found': True,
        'doctor': {'id': doctor.id, 'ad': doctor.ad},
        'total_recipes': total_recipes,
        'total_drug_count': sum(d['count'] for d in drugs),
        'drugs': drugs[:15],
    }


# ====================== İCAZƏ SİSTEMİ ======================

PERMISSION_TTL = 300


def request_permission(action_type: str, action_data: dict, description: str) -> dict:
    action_id = str(_uuid.uuid4())[:8]
    _cache.set(f"pending_action:{action_id}", {
        "type": action_type,
        "data": action_data,
        "description": description,
        "requested_at": timezone.now().isoformat(),
    }, timeout=PERMISSION_TTL)
    return {
        "action_id": action_id,
        "status": "awaiting_approval",
        "message": f"Təsdiq tələb olunur!\n\nƏməliyyat: {description}\n\nDavam etmək üçün: bəli #{action_id}\nLəğv etmək üçün: xeyr #{action_id}"
    }


def confirm_action(action_id: str) -> dict:
    pending = _cache.get(f"pending_action:{action_id}")
    if not pending:
        return {"success": False, "error": f"#{action_id} tapılmadı və ya vaxtı keçib."}
    try:
        result = _execute_approved_action(pending["type"], pending["data"])
        _cache.delete(f"pending_action:{action_id}")
        return {"success": True, "result": result}
    except Exception as e:
        _cache.delete(f"pending_action:{action_id}")
        return {"success": False, "error": str(e)}


def cancel_action(action_id: str) -> dict:
    if _cache.get(f"pending_action:{action_id}"):
        _cache.delete(f"pending_action:{action_id}")
        return {"success": True, "message": f"#{action_id} ləğv edildi."}
    return {"success": False, "error": f"#{action_id} tapılmadı."}


def _execute_approved_action(action_type: str, action_data: dict):
    if action_type == "add_doctor":
        from doctors.models import Doctors
        from regions.models import Region, City, Hospital

        bolge = Region.objects.get(id=action_data["bolge_id"])
        klinika = Hospital.objects.get(id=action_data["klinika_id"])
        city = City.objects.filter(id=action_data.get("city_id")).first() if action_data.get("city_id") else None

        doctor = Doctors.objects.create(
            ad=action_data.get("ad", ""),
            ixtisas=action_data.get("ixtisas", ""),
            kategoriya=action_data.get("kategoriya", ""),
            derece=action_data.get("derece", "II"),
            cinsiyyet=action_data.get("cinsiyyet", "Kişi"),
            bolge=bolge,
            city=city,
            klinika=klinika,
            number=action_data.get("number", ""),
        )
        return {"message": f"Həkim uğurla əlavə edildi. ID: {doctor.id}", "doctor_id": doctor.id}

    raise ValueError(f"Bilinməyən əməliyyat: {action_type}")

# ====================== OPENAI ÜÇÜN FUNKSIYA TƏRİFLƏRİ ======================

FUNCTIONS = [
    {"name": "get_recent_doctors", "description": "Ən son əlavə olunan həkimləri göstərir.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}},
    {"name": "get_doctor_statistics", "description": "Ümumi həkim statistikalarını göstərir.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_region_statistics", "description": "Bütün bölgələrin statistikasını göstərir.", "parameters": {"type": "object", "properties": {}}},
    {"name": "search_doctors", "description": "Həkim axtarışı (ad, barkod, bölgə).", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]}},
    {"name": "get_financial_summary", "description": "Ümumi maliyyə xülasəsi.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_doctors_by_region", "description": "Bölgə üzrə həkimlər.", "parameters": {"type": "object", "properties": {"region_name": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["region_name"]}},
    {"name": "get_doctor_financial_details", "description": "Həkimin maliyyə detallarını göstərir.", "parameters": {"type": "object", "properties": {"doctor_name": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["doctor_name"]}},
    {"name": "get_doctor_prescription_stats", "description": "Həkimin resept və dərman statistikasını göstərir.", "parameters": {"type": "object", "properties": {"doctor_name": {"type": "string"}, "year": {"type": "integer"}, "month": {"type": "integer"}, "day": {"type": "integer"}}, "required": ["doctor_name"]}},
    {"name": "request_permission", "description": "DB-yə yazma əməliyyatlarından əvvəl istifadəçidən icazə alır.", "parameters": {"type": "object", "properties": {"action_type": {"type": "string"}, "action_data": {"type": "object"}, "description": {"type": "string"}}, "required": ["action_type", "action_data", "description"]}},
    {"name": "confirm_action", "description": "İstifadəçi bəli dedikdən sonra əməliyyatı icra edir.", "parameters": {"type": "object", "properties": {"action_id": {"type": "string"}}, "required": ["action_id"]}},
    {"name": "cancel_action", "description": "İstifadəçi xeyr dedikdə əməliyyatı ləğv edir.", "parameters": {"type": "object", "properties": {"action_id": {"type": "string"}}, "required": ["action_id"]}},
]

FUNCTION_MAP = {
    "get_recent_doctors": get_recent_doctors,
    "get_doctor_statistics": get_doctor_statistics,
    "get_region_statistics": get_region_statistics,
    "search_doctors": search_doctors,
    "get_financial_summary": get_financial_summary,
    "get_doctors_by_region": get_doctors_by_region,
    "get_doctor_financial_details": get_doctor_financial_details,
    "get_doctor_prescription_stats": get_doctor_prescription_stats,
    "request_permission": request_permission,
    "confirm_action": confirm_action,
    "cancel_action": cancel_action,
}