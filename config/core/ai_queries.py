"""
Database query functions for AI assistant
These functions are called by OpenAI function calling feature
"""
from doctors.models import Doctors, Recipe, RecipeDrug
from regions.models import Region, City, Hospital
from medicine.models import Medical
from payment.models import Payment_doctor, Sale, MonthlyDoctorReport
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from decimal import Decimal


def get_recent_doctors(limit=10):
    """Get most recently added doctors"""
    doctors = Doctors.objects.select_related('bolge', 'city', 'klinika').order_by('-created_at')[:limit]
    result = []
    for doctor in doctors:
        result.append({
            'id': doctor.id,
            'ad': doctor.ad,
            'barkod': doctor.barkod or 'Yoxdur',
            'bolge': doctor.bolge.region_name if doctor.bolge else 'Yoxdur',
            'city': doctor.city.city_name if doctor.city else 'Yoxdur',
            'klinika': doctor.klinika.hospital_name if doctor.klinika else 'Yoxdur',
            'ixtisas': doctor.get_ixtisas_display(),
            'derece': doctor.get_derece_display(),
            'created_at': doctor.created_at.strftime('%Y-%m-%d %H:%M') if doctor.created_at else 'Yoxdur'
        })
    return result


def get_doctor_statistics():
    """Get overall doctor statistics"""
    total = Doctors.objects.count()
    by_degree = Doctors.objects.values('derece').annotate(count=Count('id'))
    by_specialty = Doctors.objects.values('ixtisas').annotate(count=Count('id'))[:10]
    by_region = Doctors.objects.values('bolge__region_name').annotate(count=Count('id'))
    
    # This month's new doctors
    today = datetime.now()
    this_month = Doctors.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    
    return {
        'total_doctors': total,
        'new_this_month': this_month,
        'by_degree': {item['derece']: item['count'] for item in by_degree},
        'by_specialty': {item['ixtisas']: item['count'] for item in by_specialty},
        'by_region': {item['bolge__region_name']: item['count'] for item in by_region}
    }


def get_region_statistics():
    """Get region statistics"""
    regions = Region.objects.annotate(
        doctor_count=Count('doctors'),
        city_count=Count('cities'),
        hospital_count=Count('hospital_set')
    )
    
    result = []
    for region in regions:
        result.append({
            'region_name': region.region_name,
            'region_type': region.get_region_type_display() or 'Yoxdur',
            'doctor_count': region.doctor_count,
            'city_count': region.city_count,
            'hospital_count': region.hospital_count
        })
    
    return result


def search_doctors(query, limit=10):
    """Search doctors by name, barcode, or region"""
    doctors = Doctors.objects.filter(
        Q(ad__icontains=query) |
        Q(barkod__icontains=query) |
        Q(bolge__region_name__icontains=query)
    ).select_related('bolge', 'city', 'klinika')[:limit]
    
    result = []
    for doctor in doctors:
        result.append({
            'id': doctor.id,
            'ad': doctor.ad,
            'barkod': doctor.barkod or 'Yoxdur',
            'bolge': doctor.bolge.region_name if doctor.bolge else 'Yoxdur',
            'ixtisas': doctor.get_ixtisas_display(),
            'derece': doctor.get_derece_display()
        })
    return result


def get_financial_summary():
    """Get financial summary statistics"""
    total_debt = Doctors.objects.aggregate(
        total=Sum('yekun_borc', default=Decimal('0'))
    )['total'] or Decimal('0')
    
    total_previous_debt = Doctors.objects.aggregate(
        total=Sum('previous_debt', default=Decimal('0'))
    )['total'] or Decimal('0')
    
    doctors_with_debt = Doctors.objects.filter(yekun_borc__gt=0).count()
    
    return {
        'total_debt': float(total_debt),
        'total_previous_debt': float(total_previous_debt),
        'doctors_with_debt': doctors_with_debt,
        'total_doctors': Doctors.objects.count()
    }


def get_doctors_by_region(region_name, limit=20):
    """Get doctors by region name"""
    doctors = Doctors.objects.filter(
        bolge__region_name__icontains=region_name
    ).select_related('bolge', 'city', 'klinika')[:limit]
    
    result = []
    for doctor in doctors:
        result.append({
            'id': doctor.id,
            'ad': doctor.ad,
            'barkod': doctor.barkod or 'Yoxdur',
            'city': doctor.city.city_name if doctor.city else 'Yoxdur',
            'klinika': doctor.klinika.hospital_name if doctor.klinika else 'Yoxdur',
            'ixtisas': doctor.get_ixtisas_display(),
            'yekun_borc': float(doctor.yekun_borc)
        })
    return result


def get_doctor_financial_details(doctor_name: str, limit: int = 5):
    """
    Get detailed financial information for a doctor by (partial) name.
    - Matches doctors whose name contains the given string (case-insensitive)
    - If multiple doctors match, returns top N for disambiguation
    - Includes current debts, previous debts, and outgoing payments
    """
    # Find matching doctors
    doctors = Doctors.objects.filter(ad__icontains=doctor_name).select_related('bolge', 'city', 'klinika')[:limit]

    result = []
    for doctor in doctors:
        # Current debt fields from Doctors table
        financial = {
            'doctor_id': doctor.id,
            'ad': doctor.ad,
            'barkod': doctor.barkod or '',
            'bolge': doctor.bolge.region_name if doctor.bolge else '',
            'city': doctor.city.city_name if doctor.city else '',
            'klinika': doctor.klinika.hospital_name if doctor.klinika else '',
            'previous_debt': float(doctor.previous_debt or 0),
            'yekun_borc': float(doctor.yekun_borc or 0),
            'borc': float(doctor.borc or 0),
            'hesablanan_miqdar': float(doctor.hesablanan_miqdar or 0),
            'hekimden_silinen': float(doctor.hekimden_silinen or 0),
            'datasiya': float(doctor.datasiya or 0),
            'avans': float(doctor.avans or 0),
            'investisiya': float(doctor.investisiya or 0),
            'geriqaytarma': float(doctor.geriqaytarma or 0),
        }

        # Outgoing payments (open payments)
        payments_qs = doctor.odenisler.filter(is_closed=False).order_by('-date')[:20]
        payments = []
        for p in payments_qs:
            payments.append({
                'payment_type': p.payment_type,
                'pay': float(p.pay or 0),
                'date': p.date.strftime('%Y-%m-%d') if p.date else '',
                'region': p.area.region_name if p.area else '',
            })

        financial['payments'] = payments

        # Monthly reports (last 6 months)
        reports_qs = MonthlyDoctorReport.objects.filter(doctor=doctor).order_by('-report_month')[:6]
        reports = []
        for r in reports_qs:
            reports.append({
                'month': r.report_month.strftime('%Y-%m') if r.report_month else '',
                'borc': float(r.borc or 0),
                'avans': float(r.avans or 0),
                'investisiya': float(r.investisiya or 0),
                'geriqaytarma': float(r.geriqaytarma or 0),
                'hesablanan_miqdar': float(r.hesablanan_miqdar or 0),
                'hekimden_silinen': float(r.hekimden_silinen or 0),
                'yekun_borc': float(r.yekun_borc or 0),
            })

        financial['monthly_reports'] = reports
        result.append(financial)

    return result


def get_doctor_prescription_stats(doctor_name: str, year: int = None, month: int = None, day: int = None):
    """
    Get prescription statistics (recipes and drugs) for a doctor.
    - If year/month/day verilirsə: həmin gün/ay üçün filtrlə
    - Əks halda: cari ay üçün statistikaları qaytar
    """
    today = datetime.now()
    year = year or today.year
    month = month or today.month

    # Həkimi tap (ilk uyğun gələn)
    doctor = Doctors.objects.filter(ad__icontains=doctor_name).first()
    if not doctor:
        return {
            'doctor_found': False,
            'doctor_name': doctor_name,
            'message': 'Bu ada uyğun həkim tapılmadı.'
        }

    # Reseptlər üzrə filter
    recipes = Recipe.objects.filter(dr=doctor, date__year=year)
    if month:
        recipes = recipes.filter(date__month=month)
    if day:
        recipes = recipes.filter(date__day=day)

    total_recipes = recipes.count()

    # Reseptdəki dərmanlar üzrə aqreqasiya
    drugs_qs = RecipeDrug.objects.filter(recipe__in=recipes)\
        .values('drug__med_name')\
        .annotate(total_count=Sum('number'))\
        .order_by('-total_count')

    drugs = []
    for d in drugs_qs:
        drugs.append({
            'name': d['drug__med_name'],
            'count': float(d['total_count'] or 0)
        })

    # Toplam dərman sayı
    total_drug_count = float(sum(d['total_count'] or 0 for d in drugs_qs))

    return {
        'doctor_found': True,
        'doctor': {
            'id': doctor.id,
            'ad': doctor.ad,
            'bolge': doctor.bolge.region_name if doctor.bolge else '',
        },
        'year': year,
        'month': month,
        'day': day,
        'total_recipes': total_recipes,
        'total_drug_count': total_drug_count,
        'drugs': drugs,
    }


# Function definitions for OpenAI
FUNCTIONS = [
    {
        "name": "get_recent_doctors",
        "description": "Ən son əlavə olunan həkimləri göstərir. Limit parametri ilə neçə həkim göstəriləcəyini təyin edə bilərsiniz.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Göstəriləcək həkimlərin sayı (default: 10)",
                    "default": 10
                }
            }
        }
    },
    {
        "name": "get_doctor_statistics",
        "description": "Ümumi həkim statistikalarını göstərir: ümumi say, dərəcə üzrə, ixtisas üzrə, bölgə üzrə paylanma və bu ay əlavə olunanlar.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_region_statistics",
        "description": "Bütün bölgələrin statistikalarını göstərir: həkim sayı, şəhər sayı, xəstəxana sayı.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_doctors",
        "description": "Həkimləri ad, barkod və ya bölgə adına görə axtarır.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Axtarış sorğusu (həkim adı, barkod və ya bölgə adı)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nəticələrin maksimum sayı (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_financial_summary",
        "description": "Maliyyə ümumi məlumatlarını göstərir: ümumi borc, əvvəlki borc, borclu həkimlərin sayı.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_doctor_financial_details",
        "description": "Həkimin fərdi borclarını, aylıq hesabatlarını və kənara çıxan vəsaitləri (ödənişləri) göstərir.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {
                    "type": "string",
                    "description": "Həkimin adı (tam və ya bir hissəsi). Məs: 'Əhməd' və ya 'Əhməd Məmmədov'."
                },
                "limit": {
                    "type": "integer",
                    "description": "Əgər bir neçə həkim uyğun gəlirsə, maksimum neçə həkim göstərilsin (default: 5).",
                    "default": 5
                }
            },
            "required": ["doctor_name"]
        }
    },
    {
        "name": "get_doctor_prescription_stats",
        "description": "Həkimin müəyyən dövr üçün (gün/ay) yazdığı reseptlərin və dərmanların statistikasını göstərir.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {
                    "type": "string",
                    "description": "Həkimin adı (tam və ya bir hissəsi). Məs: 'Vüsalə' və ya 'Əli Məmmədov'."
                },
                "year": {
                    "type": "integer",
                    "description": "İl (default: cari il)"
                },
                "month": {
                    "type": "integer",
                    "description": "Ay (1-12, default: cari ay)"
                },
                "day": {
                    "type": "integer",
                    "description": "Gün (1-31, optional). Əgər verilsə, yalnız həmin gün üçün nəticə."
                }
            },
            "required": ["doctor_name"]
        }
    },
    {
        "name": "get_doctors_by_region",
        "description": "Müəyyən bölgəyə aid həkimləri göstərir.",
        "parameters": {
            "type": "object",
            "properties": {
                "region_name": {
                    "type": "string",
                    "description": "Bölgə adı"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nəticələrin maksimum sayı (default: 20)",
                    "default": 20
                }
            },
            "required": ["region_name"]
        }
    }
]

# Function mapping
FUNCTION_MAP = {
    "get_recent_doctors": get_recent_doctors,
    "get_doctor_statistics": get_doctor_statistics,
    "get_region_statistics": get_region_statistics,
    "search_doctors": search_doctors,
    "get_financial_summary": get_financial_summary,
    "get_doctors_by_region": get_doctors_by_region,
    "get_doctor_financial_details": get_doctor_financial_details,
    "get_doctor_prescription_stats": get_doctor_prescription_stats,
}

