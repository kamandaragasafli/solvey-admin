import json
from datetime import datetime as dt, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from medicine.models import Medical

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from doctors.models import Doctors
from medicine.models import Medical
from regions.models import City, Hospital, Region

from .models import (
    Istifadeci,
    Vizit,
    VizitPreparat,
    AptekVizit,
    AptekVizitPreparat,
    DayRecipe,
    DayRecipeDrug,
    WeeklySchedule,
    WeeklyScheduleDay,
    WeeklyScheduleVisit,
)
from medicine.models import Medical
from .utils import (
    menecer_rehber_required,
    rehber_required,
    vizit_giris_yoxla,
    vizit_login_required,
    vizit_session_temizle,
    vizit_session_yaz,
)

MUNASIBAT_SECIMLERI = [c[0] for c in Vizit.MUNASIBAT_CHOICES]

# PDF Styles
from reportlab.lib.styles import getSampleStyleSheet
pdf_styles = getSampleStyleSheet()
pdf_styles.add(ParagraphStyle(name='Header', fontSize=18, spaceAfter=12, textColor=colors.HexColor('#1F5F5B'), alignment=1))
pdf_styles.add(ParagraphStyle(name='Bold', fontSize=12, spaceAfter=6, textColor=colors.black))
pdf_styles['Normal'].fontSize = 10
pdf_styles['Normal'].spaceAfter = 6
pdf_styles['Normal'].textColor = colors.black

ROL_BASLIQLARI = {
    Istifadeci.ROL_NUMAYENDE: 'Tibbi Nümayəndə',
    Istifadeci.ROL_MENECER: 'Menecer',
    Istifadeci.ROL_REHBER: 'Diviziya Rəhbər',
}

EXCEL_PREP_ORDER = [
    drug.med_name for drug in Medical.objects.filter(status=True).order_by('med_name')
]


def _admin_redirect(tab):    return redirect(f"{reverse('vizit:admin_panel')}?tab={tab}")


def _ixtisas_secimleri():
    return [{'id': kod, 'kod': kod, 'ad': ad} for kod, ad in Doctors.İXTİSAS_SECIMI]


def _kateqoriya_secimleri():
    return [{'id': kod, 'ad': ad} for kod, ad in Doctors.KATEQORIYA_SECIMI]


def _klinika_tap(city):
    return (
        Hospital.objects.filter(city=city).first()
        or Hospital.objects.filter(region_net=city.region).first()
    )


def _bolgeler_for_user(user_rol, user_bolge_ids):
    # Rəhbər və Diviziya Rəhbəri hər şeyi görür
    if user_rol in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        return Region.objects.order_by('region_name')
    
    # Nümayəndə/Menecer üçün filter tətbiq edirik
    return Region.objects.filter(pk__in=user_bolge_ids).order_by('region_name')

def _api_bolge_icazesi(request, bolge_id):
    """
    Rəhbər və Diviziya rəhbərinə hər yerə giriş icazəsi verilir.
    Digərləri yalnız öz siyahısında olan bölgəyə baxa bilər.
    """
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', []) # İndi siyahı gəlir

    # Rəhbər və Diviziya rəhbəri üçün tam giriş
    if user_rol in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        return True

    # Nümayəndə və Menecer üçün yoxlanış
    try:
        return int(bolge_id) in [int(b_id) for b_id in user_bolge_ids]
    except (TypeError, ValueError):
        return False

def _api_rayon_icazesi(request, rayon_id):
    city = City.objects.filter(pk=rayon_id).values_list('region_id', flat=True).first()
    if city is None:
        return False
    return _api_bolge_icazesi(request, city)


def _filtered_vizit_qs(request):
    user_id = request.session['istifadeci_id']
    user_rol = request.session.get('rol')
    user_bolge_id = request.session.get('bolge_id')
    bugun = timezone.localdate()

    filter_bolge = request.GET.get('bolge_id', '')
    if not filter_bolge and user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER) and user_bolge_id:
        filter_bolge = str(user_bolge_id)

    filter_rayon = request.GET.get('rayon_id', '')
    filter_tarix_bas = request.GET.get('tarix_bas') or bugun.isoformat()
    filter_tarix_son = request.GET.get('tarix_son') or bugun.isoformat()
    filter_munasibat = request.GET.get('munasibat', '')

    filter_bolge_id = int(filter_bolge) if filter_bolge else None
    filter_rayon_id = int(filter_rayon) if filter_rayon else None

    qs = Vizit.objects.filter(
        tarix__gte=filter_tarix_bas,
        tarix__lte=filter_tarix_son,
    ).select_related('hekim', 'rayon', 'bolge', 'istifadeci').prefetch_related('preparatlar__preparat')

    if user_rol == Istifadeci.ROL_NUMAYENDE:
        qs = qs.filter(istifadeci_id=user_id)
    if filter_bolge_id:
        qs = qs.filter(bolge_id=filter_bolge_id)
    if filter_rayon_id:
        qs = qs.filter(rayon_id=filter_rayon_id)
    if filter_munasibat:
        qs = qs.filter(munasibat=filter_munasibat)

    return {
        'user_id': user_id,
        'user_rol': user_rol,
        'user_bolge_id': user_bolge_id,
        'filter_bolge': filter_bolge,
        'filter_rayon': filter_rayon,
        'filter_tarix_bas': filter_tarix_bas,
        'filter_tarix_son': filter_tarix_son,
        'filter_munasibat': filter_munasibat,
        'filter_bolge_id': filter_bolge_id,
        'filter_rayon_id': filter_rayon_id,
        'bugun': bugun,
        'qs': qs,
    }


def _format_tarix_aralig(tarix_bas, tarix_son):
    try:
        bas = dt.strptime(tarix_bas, '%Y-%m-%d')
        son = dt.strptime(tarix_son, '%Y-%m-%d')
        araliq = bas.strftime('%d.%m.%Y')
        if tarix_bas != tarix_son:
            araliq += f' — {son.strftime("%d.%m.%Y")}'
        return araliq
    except ValueError:
        return tarix_bas


def _excel_prep_sira():
    db_names = set(Medical.objects.filter(status=True).values_list('med_name', flat=True))
    sira = [name for name in EXCEL_PREP_ORDER if name in db_names]
    extras = sorted(db_names - set(EXCEL_PREP_ORDER))
    return sira + extras


def _excel_export_rows(vizitler_qs):
    rows = []
    for vizit in vizitler_qs.order_by('tarix', 'vaxt'):
        rows.append({
            'hekim': vizit.hekim_ad_goster if vizit.hekim_ad_goster != '—' else '',
            'ixtisas_kod': vizit.hekim_ixtisas_goster,
            'kateqoriya': vizit.hekim_kat_goster,
            'rayon': vizit.rayon.get_city_name_display() if vizit.rayon else '',
            'munasibat': vizit.munasibat,
            'qeyd': (vizit.qeyd or '').strip(),
            'preps_list': [vp.preparat.med_name for vp in vizit.preparatlar.all()],
        })
    return rows


def login_view(request):
    if request.session.get('istifadeci_id'):
        if request.session.get('rol') == Istifadeci.ROL_REHBER:
            return redirect('vizit:admin_panel')
        return redirect('vizit:index')

    xeta = ''
    login_deyeri = ''

    if request.method == 'POST':
        login = request.POST.get('login', '').strip()
        sifre = request.POST.get('sifre', '').strip()
        login_deyeri = login

        if login and sifre:
            istifadeci = Istifadeci.authenticate(login, sifre)
            if istifadeci:
                # Köhnə sessiya cookie-ni təzələ, məlumatı saxla
                request.session.cycle_key()
                vizit_session_yaz(request, istifadeci)
                if istifadeci.rol == Istifadeci.ROL_REHBER:
                    return redirect('vizit:admin_panel')
                return redirect('vizit:index')
            xeta = 'Login və ya şifrə yanlışdır!'
        else:
            xeta = 'Bütün sahələri doldurun!'

    return render(
        request,
        'vizit/login.html',
        {'xeta': xeta, 'login_deyeri': login_deyeri},
    )


def logout_view(request):
    vizit_session_temizle(request)
    request.session.flush()
    return redirect('vizit:login')


@csrf_exempt
@ensure_csrf_cookie
def mobile_login_view(request):
    """Mobil tətbiq üçün JSON login — eyni Istifadeci.authenticate istifadə edir."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'xeta': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = request.POST.dict() if request.POST else {}

    login = str(data.get('login', '')).strip()
    sifre = str(data.get('sifre', '')).strip()

    if not login or not sifre:
        return JsonResponse({'ok': False, 'xeta': 'Bütün sahələri doldurun!'}, status=400)

    istifadeci = Istifadeci.authenticate(login, sifre)
    if not istifadeci:
        return JsonResponse({'ok': False, 'xeta': 'Login və ya şifrə yanlışdır!'}, status=401)

    request.session.cycle_key()
    vizit_session_yaz(request, istifadeci)
    csrftoken = get_token(request)

    # Mobil tətbiqlər üçün session cookie-nin qalması üçün
    request.session.save()

    return JsonResponse({
        'ok': True,
        'sessionid': request.session.session_key,
        'csrftoken': csrftoken,
        'token': custom_token.key,
        'user': {
            'id': istifadeci.pk,
            'ad': istifadeci.ad,
            'login': istifadeci.login,
            'rol': istifadeci.rol,
            'rol_ad': istifadeci.get_rol_display(),
            'qrup': istifadeci.qrup,
            'bolge_ad': ', '.join([b.region_name for b in istifadeci.bolgeler.all()]) if istifadeci.bolgeler.exists() else '',
        },
    })

    # Token yarat və ya yenilə
    from rest_framework.authtoken.models import Token
    from django.contrib.auth.models import User
    dummy_user, _ = User.objects.get_or_create(username=f'vizit_{istifadeci.pk}')
    custom_token, _ = Token.objects.get_or_create(user=dummy_user)

    return JsonResponse({
        'ok': True,
        'sessionid': request.session.session_key,
        'csrftoken': csrftoken,
        'token': custom_token.key,
        'user': {
            'id': istifadeci.pk,
            'ad': istifadeci.ad,
            'login': istifadeci.login,
            'rol': istifadeci.rol,
            'rol_ad': istifadeci.get_rol_display(),
            'qrup': istifadeci.qrup,
            'bolge_ad': ', '.join([b.region_name for b in istifadeci.bolgeler.all()]) if istifadeci.bolgeler.exists() else '',
        },
    })


@vizit_login_required
def mobile_logout_view(request):
    vizit_session_temizle(request)
    request.session.flush()
    return JsonResponse({'ok': True})


# ========== MOBILE DASHBOARD API ==========
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication


class VizitTokenPermission:
    """Custom permission: Token ilə yoxla (session lazım deyil)."""
    def has_permission(self, request, view):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header:
            return False
        token = auth_header.replace('Token ', '').replace('Bearer ', '')
        if not token:
            return False
        from rest_framework.authtoken.models import Token
        try:
            Token.objects.get(key=token)
            return True
        except Token.DoesNotExist:
            return False


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_doctors_api(request):
    """Ən çox vizit görən top 5 istifadəçi siyahısı — son 7 gün (bütün userlər)."""
    bugun = timezone.localdate()
    bir_hevte_once = bugun - timedelta(days=7)

    # Bütün vizitlər (filter yoxdur)
    qs = Vizit.objects.filter(
        tarix__gte=bir_hevte_once,
        tarix__lte=bugun,
    ).select_related('istifadeci', 'rayon', 'bolge')

    # İstifadəçilər üzrə vizit sayı
    from django.db.models import Count
    user_stats = qs.values('istifadeci__ad', 'istifadeci__login', 'rayon__city_name', 'bolge__region_name').annotate(
        visit_count=Count('id')
    ).order_by('-visit_count')[:5]

    doctors = []
    for u in user_stats:
        doctors.append({
            'id': len(doctors) + 1,
            'full_name': u['istifadeci__ad'] or u['istifadeci__login'] or 'İstifadeci',
            'specialty': 'Nümayəndə',
            'category': '',
            'visit_date': f"{u['visit_count']} vizit",
            'region': u['bolge__region_name'] or '',
            'rayon': u['rayon__city_name'] or '',
            'munasibat': '',
        })

    return JsonResponse({'ok': True, 'doctors': doctors})


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_weekly_stats_api(request):
    """Həftəlik vizit statistikası — aylıq əsasda həftələr üzrə."""
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    if not user_id:
        return JsonResponse({'ok': False, 'xeta': 'Giriş tələb olunur'}, status=401)

    bugun = timezone.localdate()
    ay_basi = date(bugun.year, bugun.month, 1)

    # Həftələr üzrə vizit sayı
    from django.db.models import Count
    from django.db.models.functions import TruncWeek

    qs = Vizit.objects.filter(tarix__gte=ay_basi, tarix__lte=bugun)

    if user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER, Istifadeci.ROL_REHBER):
        qs = qs.filter(istifadeci_id=user_id)
    elif user_rol == Istifadeci.ROL_DIVIZIYA_REHB:
        pass
    elif user_bolge_ids:
        qs = qs.filter(bolge_id__in=user_bolge_ids)

    # Həftələr üzrə qruplaşdır
    weekly_data = qs.annotate(week=TruncWeek('tarix')).values('week').annotate(
        count=Count('id')
    ).order_by('week')

    labels = []
    values = []
    for w in weekly_data:
        week_num = w['week'].isocalendar()[1]
        labels.append(f'H.{week_num}')
        values.append(w['count'])

    return JsonResponse({
        'ok': True,
        'labels': labels,
        'values': values,
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_bolgeler_api(request):
    """İstifadəçinin icazəsi olan bölgələr."""
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    if user_rol in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        qs = Region.objects.order_by('region_name')
    elif user_bolge_ids:
        qs = Region.objects.filter(pk__in=user_bolge_ids).order_by('region_name')
    else:
        qs = Region.objects.none()

    return JsonResponse({
        'ok': True,
        'bolgeler': [{'id': r.id, 'ad': r.region_name} for r in qs],
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_hekimler_api(request):
    """Bölgə (və ya rayon) üzrə həkimlər."""
    bolge_id = request.GET.get('bolge_id')
    rayon_id = request.GET.get('rayon_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    # İcazə yoxla
    if bolge_id:
        if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
            if int(bolge_id) not in [int(b) for b in user_bolge_ids]:
                return JsonResponse({'ok': False, 'xeta': 'İcazə yoxdur'}, status=403)
        qs = Doctors.objects.filter(bolge_id=bolge_id, is_active=True)
    elif rayon_id:
        city = City.objects.filter(pk=rayon_id).values_list('region_id', flat=True).first()
        if city is None:
            return JsonResponse({'ok': False, 'xeta': 'Rayon tapılmadı'}, status=404)
        if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
            if city not in [int(b) for b in user_bolge_ids]:
                return JsonResponse({'ok': False, 'xeta': 'İcazə yoxdur'}, status=403)
        qs = Doctors.objects.filter(city_id=rayon_id, is_active=True)
    else:
        return JsonResponse({'ok': False, 'xeta': 'bolge_id və ya rayon_id tələb olunur'}, status=400)

    return JsonResponse({
        'ok': True,
        'hekimler': [
            {
                'id': d.id,
                'ad': d.ad,
                'ixtisas': d.ixtisas or '',
                'kategoriya': d.kategoriya or '',
                'bolge_id': d.bolge_id,
                'rayon_id': d.city_id,
                'borc': float(d.previous_debt) if d.previous_debt else 0,
            }
            for d in qs.order_by('ad')
        ],
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_hekim_detail_api(request, hekim_id):
    """Həkim detalları — payments, recipe, real_sales, monthly_reports."""
    from doctors.models import Doctors
    from django.db.models import Sum

    hekim = get_object_or_404(Doctors, id=hekim_id, is_active=True)

    # İcazə yoxla
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        if hekim.bolge_id not in [int(b) for b in user_bolge_ids]:
            return JsonResponse({'ok': False, 'xeta': 'İcazə yoxdur'}, status=403)

    # Payments (son 10)
    from payment.models import Payment_doctor
    payments = Payment_doctor.objects.filter(doctor=hekim).order_by('-date')[:10]

    # Recipe (tarix filter ilə)
    from doctors.models import RecipeDrug
    recipe_date_from = request.GET.get('recipe_date_from', '').strip()
    recipe_date_to = request.GET.get('recipe_date_to', '').strip()
    recipe_qs = RecipeDrug.objects.filter(recipe__dr=hekim).select_related('recipe', 'drug', 'recipe__region')
    if recipe_date_from:
        try:
            df = date.fromisoformat(recipe_date_from)
            recipe_qs = recipe_qs.filter(recipe__date__gte=df)
        except ValueError:
            pass
    if recipe_date_to:
        try:
            dt_obj = date.fromisoformat(recipe_date_to)
            recipe_qs = recipe_qs.filter(recipe__date__lte=dt_obj)
        except ValueError:
            pass
    recipe_qs = recipe_qs.order_by('recipe__date')

    # Real sales
    from doctors.models import RealSalesDrug
    real_sales_lines = list(
        RealSalesDrug.objects.filter(real_sale__dr_name=hekim)
        .select_related('real_sale', 'real_sale__region_n', 'drug_name')
        .order_by('-real_sale__date_sale', '-id')
    )

    # Recipe total
    recibe_total = RecipeDrug.objects.filter(recipe__dr=hekim).aggregate(total=Sum('number'))['total'] or 0

    # Monthly reports (silinme_list)
    from payment.models import MonthlyDoctorReport
    monthly_reports = MonthlyDoctorReport.objects.filter(doctor=hekim).order_by('-report_month')
    silinme_list = [
        {
            'month': report.report_month.strftime('%B %Y'),
            'hekimden_silinen': report.hekimden_silinen,
        }
        for report in monthly_reports
    ]

    return JsonResponse({
        'ok': True,
        'hekim': {
            'id': hekim.id,
            'ad': hekim.ad,
            'ixtisas': hekim.ixtisas or '',
            'kategoriya': hekim.kategoriya or '',
            'bolge': hekim.bolge.region_name if hekim.bolge else '',
            'rayon': hekim.city.get_city_name_display() if hekim.city else '',
        },
        'payments': [
            {
                'id': p.id,
                'amount': str(p.amount),
                'date': p.date.strftime('%d.%m.%Y') if p.date else '',
                'note': p.note or '',
            }
            for p in payments
        ],
        'recipe': [
            {
                'id': r.id,
                'drug_ad': r.drug.med_name if r.drug else '',
                'number': r.number,
                'date': r.recipe.date.strftime('%d.%m.%Y') if r.recipe.date else '',
                'region': r.recipe.region.region_name if r.recipe.region else '',
            }
            for r in recipe_qs
        ],
        'real_sales': [
            {
                'id': rs.id,
                'drug_ad': rs.drug_name.med_name if rs.drug_name else '',
                'number': rs.number,
                'date': rs.real_sale.date_sale.strftime('%d.%m.%Y') if rs.real_sale.date_sale else '',
                'region': rs.real_sale.region_n.region_name if rs.real_sale.region_n else '',
            }
            for rs in real_sales_lines
        ],
        'recibe_total': recibe_total,
        'silinme_list': silinme_list,
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_preparations_api(request):
    """Mobil tətbiq üçün preparatlar siyahısı."""
    preparations = Medical.objects.filter(status=True).order_by('med_name')
    return JsonResponse({
        'ok': True,
        'preparations': [
            {
                'id': p.id,
                'med_name': p.med_name,
                'med_full_name': p.med_full_name or '',
            }
            for p in preparations
        ],
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_report_api(request):
    """Mobil tətbiq üçün aylıq hesabat API."""
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    if not user_id:
        return JsonResponse({'ok': False, 'xeta': 'Giriş tələb olunur'}, status=401)

    # Tarix filter
    year = int(request.GET.get('year', timezone.localdate().year))
    month = int(request.GET.get('month', timezone.localdate().month))

    try:
        ay_basi = date(year, month, 1)
        ay_sonu = (ay_basi.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    except ValueError:
        return JsonResponse({'ok': False, 'xeta': 'Düzgün tarix daxil edin'}, status=400)

    # Vizitlər
    qs = Vizit.objects.filter(tarix__gte=ay_basi, tarix__lte=ay_sonu)

    if user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER, Istifadeci.ROL_REHBER):
        qs = qs.filter(istifadeci_id=user_id)
    elif user_rol == Istifadeci.ROL_DIVIZIYA_REHB:
        pass
    elif user_bolge_ids:
        qs = qs.filter(bolge_id__in=user_bolge_ids)

    umumi_vizit = qs.count()
    yeni_hekim_sayi = qs.filter(hekim_id__isnull=True).count()

    # Həkimlər üzrə statistika
    hekim_stats = []
    for vizit in qs.select_related('hekim', 'bolge', 'rayon').order_by('-tarix'):
        hekim_stats.append({
            'id': vizit.pk,
            'title': vizit.hekim_ad_goster,
            'meta': f"{vizit.bolge.region_name if vizit.bolge else ''} · {vizit.rayon.get_city_name_display() if vizit.rayon else ''}",
            'value': vizit.tarix.strftime('%d.%m.%Y'),
        })

    return JsonResponse({
        'ok': True,
        'summary': [
            {'label': 'Ümumi vizit', 'value': str(umumi_vizit)},
            {'label': 'Yeni həkim', 'value': str(yeni_hekim_sayi)},
        ],
        'rows': hekim_stats[:50],  # Maksimum 50
    })


@api_view(['GET'])
@permission_classes([VizitTokenPermission])
def mobile_report_pdf_api(request):
    """Mobil tətbiq üçün PDF export API."""
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    if not user_id:
        return JsonResponse({'ok': False, 'xeta': 'Giriş tələb olunur'}, status=401)

    # İstifadeci məlumatlarını al
    try:
        istifadeci = Istifadeci.objects.get(pk=user_id)
        user_ad = istifadeci.ad
    except Istifadeci.DoesNotExist:
        user_ad = 'İstifadeci'

    # Tarix filter
    year = int(request.GET.get('year', timezone.localdate().year))
    month = int(request.GET.get('month', timezone.localdate().month))

    try:
        ay_basi = date(year, month, 1)
        ay_sonu = (ay_basi.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    except ValueError:
        return JsonResponse({'ok': False, 'xeta': 'Düzgün tarix daxil edin'}, status=400)

    # Vizitlər
    qs = Vizit.objects.filter(tarix__gte=ay_basi, tarix__lte=ay_sonu)

    if user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER, Istifadeci.ROL_REHBER):
        qs = qs.filter(istifadeci_id=user_id)
    elif user_rol == Istifadeci.ROL_DIVIZIYA_REHB:
        pass
    elif user_bolge_ids:
        qs = qs.filter(bolge_id__in=user_bolge_ids)

    vizitler = qs.select_related('hekim', 'bolge', 'rayon').prefetch_related('preparatlar__preparat').order_by('tarix', 'vaxt')

    # PDF yarat
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="vizit_{year}_{month}.pdf"'

    # PDF hazırla
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

    elements = []

    # Başlıq
    elements.append(Paragraph(f"{user_ad} Vizit", pdf_styles['Header']))
    elements.append(Paragraph(f"{ay_basi.strftime('%d.%m.%Y')} - {ay_sonu.strftime('%d.%m.%Y')}", pdf_styles['Normal']))
    elements.append(Paragraph(f"Cəmi: {vizitler.count()}", pdf_styles['Bold']))
    elements.append(Spacer(1, 0.2*inch))

    # Cədvəl
    data = [['#', 'Həkim', 'İxtisas', 'Münasibət', 'Dərmanlar', 'Qeyd', 'Vaxt']]
    for idx, vizit in enumerate(vizitler, 1):
        dermanlar = ', '.join([p.preparat.med_name for p in vizit.preparatlar.all()])
        data.append([
            str(idx),
            vizit.hekim_ad_goster,
            vizit.hekim_ixtisas_goster,
            vizit.munasibat,
            dermanlar,
            vizit.qeyd or '-',
            f"{vizit.vaxt.strftime('%H:%M')}" if vizit.vaxt else '-',
        ])

    table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1*inch, 1.5*inch, 1*inch, 0.6*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.grey),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
    ]))

    elements.append(table)
    doc.build(elements)

    return response


@api_view(['POST'])
@permission_classes([VizitTokenPermission])
def mobile_create_vizit_api(request):
    """Mobil tətbiq üçün vizit yaratma API."""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = request.POST.dict() if request.POST else {}

    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    if not user_id:
        return JsonResponse({'ok': False, 'xeta': 'Giriş tələb olunur'}, status=401)

    hekim_id = data.get('hekim_id')
    hekim_adi = data.get('hekim_adi', '')
    hekim_ixtisas = data.get('hekim_ixtisas', '')
    bolge_id = data.get('bolge_id')
    rayon_id = data.get('rayon_id')
    munasibat = data.get('munasibat', '')
    qeyd = data.get('qeyd', '')
    preparatlar = data.get('preparatlar', [])

    # Validation
    hekim_ok = (hekim_id and str(hekim_id).isdigit()) or bool(hekim_adi)
    if not hekim_ok or not bolge_id or not preparatlar:
        return JsonResponse({'ok': False, 'xeta': 'Bütün sahələri doldurun'}, status=400)

    # İcazə yoxla - bölgənin istifadəçiyə aid olub olmadığını
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        if int(bolge_id) not in [int(b) for b in user_bolge_ids]:
            return JsonResponse({'ok': False, 'xeta': 'İcazə yoxdur'}, status=403)

    try:
        with transaction.atomic():
            vizit = Vizit.objects.create(
                istifadeci_id=user_id,
                hekim_id=int(hekim_id) if hekim_id and str(hekim_id).isdigit() else None,
                hekim_adi=hekim_adi[:150] if (not hekim_id or not str(hekim_id).isdigit()) and hekim_adi else '',
                hekim_ixtisas=hekim_ixtisas[:50] if (not hekim_id or not str(hekim_id).isdigit()) and hekim_ixtisas else '',
                bolge_id=int(bolge_id),
                rayon_id=int(rayon_id) if rayon_id and str(rayon_id).isdigit() else None,
                munasibat=munasibat,
                qeyd=qeyd or None,
                tarix=timezone.localdate(),
                vaxt=timezone.localtime().time().replace(second=0, microsecond=0),
            )

            VizitPreparat.objects.bulk_create([
                VizitPreparat(vizit=vizit, preparat_id=int(pid)) for pid in preparatlar
            ])

        return JsonResponse({
            'ok': True,
            'vizit_id': vizit.pk,
            'message': 'Vizit uğurla qeydə alındı',
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'xeta': f'Xəta baş verdi: {str(e)}'}, status=500)


def register_view(request):
    if request.session.get('istifadeci_id'):
        return redirect('vizit:index')

    xeta = ''
    login_deyeri = ''
    ad_deyeri = ''

    if request.method == 'POST':
        login = request.POST.get('login', '').strip()
        sifre = request.POST.get('sifre', '').strip()
        sifre_tekrar = request.POST.get('sifre_tekrar', '').strip()
        ad = request.POST.get('ad', '').strip()
        login_deyeri = login
        ad_deyeri = ad

        if not login or not sifre or not sifre_tekrar or not ad:
            xeta = 'Bütün sahələri doldurun!'
        elif sifre != sifre_tekrar:
            xeta = 'Şifrələr uyğun gəlmir!'
        elif len(sifre) < 4:
            xeta = 'Şifrə ən az 4 simvol olmalıdır!'
        else:
            try:
                istifadeci = Istifadeci(
                    login=login,
                    ad=ad,
                    rol=Istifadeci.ROL_NUMAYENDE,
                    aktiv=True
                )
                istifadeci.set_password(sifre)
                istifadeci.save()
                messages.success(request, 'Qeydiyyat uğurla tamamlandı! Zəhmət olmasa daxil olun.')
                return redirect('vizit:login')
            except IntegrityError:
                xeta = 'Bu login artıq istifadə olunur! Başqa login seçin.'

    return render(
        request,
        'vizit/login.html',
        {'xeta': xeta, 'login_deyeri': login_deyeri, 'ad_deyeri': ad_deyeri, 'register': True},
    )


@rehber_required
def admin_panel_view(request):
    tab = request.GET.get('tab', 'istifadeciler')

    if request.method == 'POST':
        # 1. İSTİFADƏÇİ ƏLAVƏ ETMƏ
        if 'add_user' in request.POST:
            login = request.POST.get('login', '').strip()
            sifre = request.POST.get('sifre', '').strip()
            ad = request.POST.get('ad', '').strip()
            rol = request.POST.get('rol', Istifadeci.ROL_NUMAYENDE)
            
            # Seçilmiş bölgələri alırıq
            bolge_ids = request.POST.getlist('bolge_ids')
            valid_bolge_ids = [int(b_id) for b_id in bolge_ids if b_id]

            if login and sifre and ad:
                try:
                    istifadeci = Istifadeci(login=login, ad=ad, rol=rol, aktiv=True)
                    istifadeci.set_password(sifre)
                    istifadeci.save()
                    
                    if valid_bolge_ids:
                        istifadeci.bolgeler.set(valid_bolge_ids)
                    
                    messages.success(request, '✅ İstifadəçi uğurla əlavə edildi.')
                except IntegrityError:
                    messages.error(request, '❌ Xəta: login artıq mövcuddur.')
            else:
                messages.error(request, '❌ Bütün sahələri doldurun.')
            return _admin_redirect(tab)

        # 1b. İSTİFADƏÇİ REDAKTƏ
        elif 'save_user' in request.POST:
            try:
                uid = int(request.POST.get('user_id') or 0)
            except (TypeError, ValueError):
                uid = 0
            user = Istifadeci.objects.filter(pk=uid).first()
            if not user:
                messages.error(request, '❌ İstifadəçi tapılmadı.')
                return _admin_redirect('istifadeciler')

            login = request.POST.get('login', '').strip()
            sifre = request.POST.get('sifre', '').strip()
            ad = request.POST.get('ad', '').strip()
            rol = request.POST.get('rol', user.rol)
            aktiv = request.POST.get('aktiv') == '1'
            bolge_ids = request.POST.getlist('bolge_ids')
            valid_bolge_ids = [int(b_id) for b_id in bolge_ids if b_id]

            if not login or not ad:
                messages.error(request, '❌ Login və ad mütləqdir.')
                return redirect(f"{reverse('vizit:admin_panel')}?tab=istifadeciler&edit_user={uid}")

            if Istifadeci.objects.filter(login=login).exclude(pk=user.pk).exists():
                messages.error(request, '❌ Bu login artıq mövcuddur.')
                return redirect(f"{reverse('vizit:admin_panel')}?tab=istifadeciler&edit_user={uid}")

            user.login = login
            user.ad = ad
            user.rol = rol
            user.aktiv = aktiv
            if sifre:
                user.set_password(sifre)
            user.save()
            user.bolgeler.set(valid_bolge_ids)
            messages.success(request, f'✅ İstifadəçi yeniləndi: {user.ad}')
            return _admin_redirect('istifadeciler')

        # 2. HƏKİM ƏLAVƏ ETMƏ
        elif 'add_hekim' in request.POST:
            ad_soyad = request.POST.get('ad_soyad', '').strip()
            rayon_id = request.POST.get('rayon_id', '')
            ixtisas = request.POST.get('ixtisas_id', '').strip() or 'TE'
            kategoriya = request.POST.get('kateqoriya_id', '').strip() or 'B'

            if ad_soyad and rayon_id:
                city = City.objects.select_related('region').filter(pk=int(rayon_id)).first()
                if not city:
                    messages.error(request, '❌ Rayon tapılmadı.')
                else:
                    klinika = _klinika_tap(city)
                    if not klinika:
                        messages.error(request, '❌ Bu rayon/bölgə üçün xəstəxana tapılmadı.')
                    else:
                        Doctors.objects.create(
                            ad=ad_soyad[:100],
                            bolge=city.region,
                            city=city,
                            klinika=klinika,
                            ixtisas=ixtisas,
                            kategoriya=kategoriya,
                            is_active=True,
                        )
                        messages.success(request, '✅ Həkim əlavə edildi.')
            else:
                messages.error(request, '❌ Ad/soyad və rayon mütləqdir.')
            return _admin_redirect(tab)

    # 3. İSTİFADƏÇİ SİLMƏ — əlaqəli vizit/aptek qeydləri ilə birlikdə
    if 'del_user' in request.GET:
        try:
            uid = int(request.GET['del_user'])
        except (TypeError, ValueError):
            messages.error(request, '❌ Yanlış istifadəçi.')
            return _admin_redirect('istifadeciler')

        user = Istifadeci.objects.filter(pk=uid).first()
        if not user:
            messages.error(request, '❌ İstifadəçi tapılmadı.')
            return _admin_redirect('istifadeciler')

        if request.session.get('istifadeci_id') == user.pk:
            messages.error(request, '❌ Öz hesabınızı silə bilməzsiniz.')
            return _admin_redirect('istifadeciler')

        ad = user.ad
        try:
            with transaction.atomic():
                # PROTECT olan əlaqələr əvvəl silinir
                Vizit.objects.filter(istifadeci=user).delete()
                AptekVizit.objects.filter(user=user).delete()
                user.delete()
            messages.success(request, f'✅ İstifadəçi silindi: {ad}')
        except ProtectedError:
            messages.error(
                request,
                f'❌ {ad} silinə bilmədi — əlaqəli qorunan qeydlər var.',
            )
        return _admin_redirect('istifadeciler')

    # Əvvəl deaktiv edilmiş (__silindi_) istifadəçiləri təmizlə
    if tab == 'istifadeciler':
        for stale in list(Istifadeci.objects.filter(login__contains='__silindi_')):
            if request.session.get('istifadeci_id') == stale.pk:
                continue
            try:
                with transaction.atomic():
                    Vizit.objects.filter(istifadeci=stale).delete()
                    AptekVizit.objects.filter(user=stale).delete()
                    stale.delete()
            except ProtectedError:
                pass

    # 4. SƏHİFƏNİ YÜKLƏMƏ
    edit_user = None
    edit_user_bolge_ids = set()
    edit_user_id = request.GET.get('edit_user')
    if tab == 'istifadeciler' and edit_user_id:
        try:
            edit_user = (
                Istifadeci.objects.prefetch_related('bolgeler')
                .filter(pk=int(edit_user_id))
                .first()
            )
            if edit_user:
                edit_user_bolge_ids = set(edit_user.bolgeler.values_list('id', flat=True))
        except (TypeError, ValueError):
            edit_user = None

    return render(
        request,
        'vizit/admin_panel.html',
        {
            'tab': tab,
            'edit_user': edit_user,
            'edit_user_bolge_ids': edit_user_bolge_ids,
            'istifadeciler': (
                Istifadeci.objects.exclude(login__contains='__silindi_')
                .prefetch_related('bolgeler')
                .order_by('rol', 'ad')
            ),
            'bolgeler': Region.objects.order_by('region_name'),
            'rayonlar': City.objects.select_related('region').order_by('region__region_name', 'city_name'),
            'ixtisaslar': _ixtisas_secimleri(),
            'kateqoriyalar': _kateqoriya_secimleri(),
            'hekimler': (
                Doctors.objects.filter(is_active=True)
                .select_related('city', 'bolge')
                .annotate(
                    rayon_ad=Coalesce(F('city__city_name'), Value('—')),
                    ix_kod=F('ixtisas'),
                    kat=F('kategoriya'),
                )
                .order_by('city__city_name', 'ad')
            ),
        },
    )
@vizit_login_required
def yeni_vizit_view(request):
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])
    bugun = timezone.localdate()

    # POST sorğusu: Viziti qeyd et
    if request.method == 'POST' and 'vizit_bagla' in request.POST:
        hekim_id = (request.POST.get('hekim_id') or '').strip()
        hekim_adi = (request.POST.get('hekim_adi') or '').strip()
        hekim_ixtisas = (request.POST.get('hekim_ixtisas') or '').strip()
        bolge_id = request.POST.get('bolge_id')
        rayon_id = (request.POST.get('rayon_id') or '').strip()
        munasibat = request.POST.get('munasibat', '')
        qeyd = (request.POST.get('qeyd') or '').strip()
        preparatlar = request.POST.getlist('preparatlar[]')

        # Seçimi sessiyada yadda saxlayırıq ki, növbəti dəfə avtomatik seçilsin
        if bolge_id:
            request.session['son_bolge_id'] = bolge_id

        hekim_ok = (hekim_id.isdigit()) or bool(hekim_adi)
        if not hekim_ok or not bolge_id or not preparatlar:
            messages.error(request, '❌ Bütün sahələri düzgün doldurun.')
            return redirect('vizit:index')

        try:
            with transaction.atomic():
                vizit = Vizit.objects.create(
                    istifadeci_id=user_id,
                    hekim_id=int(hekim_id) if hekim_id.isdigit() else None,
                    hekim_adi=hekim_adi[:150] if (not hekim_id.isdigit() and hekim_adi) else '',
                    hekim_ixtisas=hekim_ixtisas[:50] if (not hekim_id.isdigit() and hekim_ixtisas) else '',
                    bolge_id=int(bolge_id),
                    rayon_id=int(rayon_id) if rayon_id.isdigit() else None,
                    munasibat=munasibat,
                    qeyd=qeyd or None,
                    tarix=bugun,
                    vaxt=timezone.localtime().time().replace(second=0, microsecond=0),
                )
                
                VizitPreparat.objects.bulk_create([
                    VizitPreparat(vizit=vizit, preparat_id=int(pid)) for pid in preparatlar
                ])
            
            messages.success(request, '✅ Vizit uğurla qeydə alındı!')
        except Exception as e:
            messages.error(request, f'❌ Xəta baş verdi: {e}')
        
        return redirect('vizit:index')

    # GET: «Bu gün» — nümayəndə / menecer / rəhbər yalnız öz qeydləri
    vizitler_query = Vizit.objects.none()
    _own_day_roles = (
        Istifadeci.ROL_NUMAYENDE,
        Istifadeci.ROL_MENECER,
        Istifadeci.ROL_REHBER,
    )
    if user_rol in _own_day_roles and user_id:
        vizitler_query = (
            Vizit.objects.filter(tarix=bugun, istifadeci_id=user_id)
            .select_related('hekim', 'rayon', 'istifadeci')
            .prefetch_related('preparatlar__preparat')
        )

    # Son seçilən bölgəni sessiyadan oxuyuruq
    selected_bolge_id = request.session.get('son_bolge_id')

    from .vizit_day_pdf import vizit_day_share_context
    share_ctx = (
        vizit_day_share_context(request)
        if user_rol in _own_day_roles
        else {
            'share_url': '',
            'pdf_filename': '',
            'user_ad': request.session.get('ad') or '',
            'today': bugun,
        }
    )

    return render(request, 'vizit/create-vizit.html', {
        'bolgeler': _bolgeler_for_user(user_rol, user_bolge_ids),
        'selected_bolge_id': int(selected_bolge_id) if selected_bolge_id else None,
        'preparatlar_siyahisi': Medical.objects.filter(status=True).order_by('med_name'),
        'bugun_vizitler': vizitler_query.order_by('-id'),
        'user_rol': user_rol,
        'bugun_tarix': bugun,
        'ixtisas_choices': Doctors.İXTİSAS_SECIMI,
        **share_ctx,
    })


@vizit_login_required
def del_vizit(request, pk):
    """Bugünkü viziti sil — nümayəndə / menecer / rəhbər yalnız özünü."""
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    vizit = get_object_or_404(Vizit, pk=pk)

    if user_rol not in (
        Istifadeci.ROL_NUMAYENDE,
        Istifadeci.ROL_MENECER,
        Istifadeci.ROL_REHBER,
    ):
        messages.error(request, '❌ Bu viziti silmək üçün icazəniz yoxdur.')
        return redirect('vizit:index')

    if vizit.istifadeci_id != user_id:
        messages.error(request, '❌ Yalnız öz vizitinizi silə bilərsiniz.')
        return redirect('vizit:index')

    hekim_ad = vizit.hekim_ad_goster if vizit.hekim_ad_goster != '—' else 'Vizit'
    vizit.delete()
    messages.success(request, f'✅ Vizit silindi: {hekim_ad}')
    return redirect('vizit:index')


def _rayonlar_list(request, bolge_id):
    if not bolge_id or not _api_bolge_icazesi(request, bolge_id):
        return []
    return [
        {'id': c.id, 'ad': c.get_city_name_display()}
        for c in City.objects.filter(region_id=bolge_id).order_by('city_name')
    ]


def _hekimler_list(request, bolge_id=None, rayon_id=None):
    if bolge_id:
        if not _api_bolge_icazesi(request, bolge_id):
            return []
        qs = Doctors.objects.filter(bolge_id=bolge_id, is_active=True)
    elif rayon_id:
        if not _api_rayon_icazesi(request, rayon_id):
            return []
        qs = Doctors.objects.filter(city_id=rayon_id, is_active=True)
    else:
        return []
    return [
        {
            'id': d.id,
            'ad_soyad': d.ad,
            'ixtisas_kod': d.ixtisas or '',
            'ixtisas': d.ixtisas or '',
            'kateqoriya': d.kategoriya or '',
            'kategoriya': d.kategoriya or '',
            'derece': d.derece or '',
            'previous_debt': str(d.previous_debt or 0),
        }
        for d in qs.order_by('ad')
    ]


@vizit_login_required
def get_rayonlar_api(request):
    return JsonResponse({'rayonlar': _rayonlar_list(request, request.GET.get('bolge_id'))})


@vizit_login_required
def get_hekimler_api(request):
    return JsonResponse({
        'hekimler': _hekimler_list(
            request,
            bolge_id=request.GET.get('bolge_id'),
            rayon_id=request.GET.get('rayon_id'),
        )
    })


@vizit_login_required
def ajax_compat_view(request):
    """Köhnə vizit/ajax.php ilə eyni ?action= parametrləri (JSON massiv)."""
    action = request.GET.get('action', '')
    if action == 'rayonlar':
        return JsonResponse(
            _rayonlar_list(request, request.GET.get('bolge_id')),
            safe=False,
        )
    if action == 'hekimler':
        return JsonResponse(
            _hekimler_list(
                request,
                bolge_id=request.GET.get('bolge_id'),
                rayon_id=request.GET.get('rayon_id'),
            ),
            safe=False,
        )
    return JsonResponse([], safe=False)

@vizit_login_required
def hesabat_view(request):
    f = _filtered_vizit_qs(request)
    user_rol = f['user_rol']
    user_bolge_id = f['user_bolge_id']
    vizitler_qs = f['qs']

    # --- TƏHLÜKƏSİZLİK YOXLAMASI: None xətasını aradan qaldırırıq ---
    # Əgər user_bolge_id tək bir dəyərdirsə siyahıya çeviririk, None-dursa boş siyahı edirik
    if user_bolge_id is None:
        bolge_list = []
    elif isinstance(user_bolge_id, (list, tuple)):
        bolge_list = user_bolge_id
    else:
        bolge_list = [user_bolge_id]

    # Bölgələri və rayonları təyin edirik
    bolgeler = _bolgeler_for_user(user_rol, bolge_list)
    
    rayonlar = (
        City.objects.filter(region_id=f['filter_bolge_id']).order_by('city_name')
        if f['filter_bolge_id']
        else City.objects.none()
    )

    # Vizitləri sıralayırıq
    vizitler = vizitler_qs.order_by('-tarix', '-vaxt')
    total_vizit = vizitler.count()

    # Preparat statistikası
    try:
        prep_stat = [
            {'ad': row['preparat__med_name'], 'c': row['c']}
            for row in (
                VizitPreparat.objects.filter(vizit__in=vizitler_qs.values('pk'))
                .values('preparat__med_name')
                .annotate(c=Count('id'))
                .order_by('-c')[:8]
            )
        ]
    except Exception:
        prep_stat = []

    return render(
        request,
        'vizit/hesabat.html',
        {
            'bolgeler': bolgeler,
            'rayonlar': rayonlar,
            'vizitler': vizitler,
            'total_vizit': total_vizit,
            'prep_stat': prep_stat,
            'munasibatler': MUNASIBAT_SECIMLERI,
            'user_rol': user_rol,
            'user_bolge_id': user_bolge_id,
            'filter_bolge': f['filter_bolge'],
            'filter_rayon': f['filter_rayon'],
            'filter_tarix_bas': f['filter_tarix_bas'],
            'filter_tarix_son': f['filter_tarix_son'],
            'filter_munasibat': f['filter_munasibat'],
            'excel_url_params': urlencode(request.GET),
        },
    )


@vizit_login_required
def excel_export_view(request):
    f = _filtered_vizit_qs(request)
    vizitler = _excel_export_rows(f['qs'])
    # Yalnız hesabatda işarələnmiş (işlənilən) dərman sütunları
    used_preps = set()
    for row in vizitler:
        used_preps.update(row['preps_list'])
    prep_sira = [name for name in _excel_prep_sira() if name in used_preps]

    tarix_aralig = _format_tarix_aralig(f['filter_tarix_bas'], f['filter_tarix_son'])
    rol_basliq = ROL_BASLIQLARI.get(f['user_rol'], 'Vizit')

    clean_tarix = tarix_aralig.replace(' ', '_').replace('.', '_').replace('—', '-')
    file_name = f'Vizit_Hesabat_{clean_tarix}.xls'

    response = render(
        request,
        'vizit/export_excel.html',
        {
            'rol_basliq': rol_basliq,
            'tarix_aralig': tarix_aralig,
            'prep_sira': prep_sira,
            'vizitler': vizitler,
            'colspan_count': 7 + len(prep_sira),
        },
    )
    response['Content-Type'] = 'application/vnd.ms-excel; charset=utf-8'
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response['Cache-Control'] = 'max-age=0'
    response.content = b'\xef\xbb\xbf' + response.content
    return response


def _bolge_stat_data(bolge_id, tarix_bas, tarix_son):
    vizitler = Vizit.objects.filter(
        bolge_id=bolge_id,
        tarix__gte=tarix_bas,
        tarix__lte=tarix_son,
    ).select_related('istifadeci', 'rayon')

    by_user = {}
    for vizit in vizitler:
        uid = vizit.istifadeci_id
        if uid not in by_user:
            by_user[uid] = {
                'numayende': vizit.istifadeci.ad,
                'vizit_sayi': 0,
                'rayonlar': set(),
            }
        by_user[uid]['vizit_sayi'] += 1
        if vizit.rayon:
            by_user[uid]['rayonlar'].add(vizit.rayon.get_city_name_display())

    numayende_stat = sorted(
        [
            {
                'numayende': row['numayende'],
                'vizit_sayi': row['vizit_sayi'],
                'rayonlar': ', '.join(sorted(row['rayonlar'])),
            }
            for row in by_user.values()
        ],
        key=lambda row: -row['vizit_sayi'],
    )

    rayon_rows = (
        vizitler.values('rayon_id')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    rayon_ids = [row['rayon_id'] for row in rayon_rows if row['rayon_id']]
    city_map = {
        city.pk: city.get_city_name_display()
        for city in City.objects.filter(pk__in=rayon_ids)
    }
    rayon_stat = [
        {'rayon': city_map.get(row['rayon_id'], '—'), 'c': row['c']}
        for row in rayon_rows
    ]

    return numayende_stat, rayon_stat

@menecer_rehber_required
def bolge_stat_view(request):
    user_rol = request.session.get('rol')
    # SESSİYADAN İD-LƏRİ SİYAHI KİMİ ALIN
    user_bolge_ids = request.session.get('bolge_ids', []) 
    
    today = timezone.localdate()
    default_tarix_bas = today.replace(day=1).isoformat()
    default_tarix_son = today.isoformat()

    filter_bolge = request.GET.get('bolge_id', '')
    
    # Əgər menecerdirsə və filter seçilməyibsə, sessiyadakı ilk bölgəni seçirik
    if not filter_bolge and user_rol == Istifadeci.ROL_MENECER and user_bolge_ids:
        filter_bolge = str(user_bolge_ids[0])

    filter_tarix_bas = request.GET.get('tarix_bas') or default_tarix_bas
    filter_tarix_son = request.GET.get('tarix_son') or default_tarix_son

    # --- TƏHLÜKƏSİZLİK YOXLAMASI ---
    # _bolgeler_for_user mütləq siyahı gözləyir
    bolgeler = _bolgeler_for_user(user_rol, user_bolge_ids if isinstance(user_bolge_ids, list) else [])

    numayende_stat = []
    rayon_stat = []
    
    if filter_bolge:
        try:
            numayende_stat, rayon_stat = _bolge_stat_data(
                int(filter_bolge), filter_tarix_bas, filter_tarix_son
            )
        except (ValueError, TypeError):
            messages.error(request, "❌ Seçilmiş bölgə məlumatları tapılmadı.")

    return render(
        request,
        'vizit/bolge_stat.html',
        {
            'bolgeler': bolgeler,
            'numayende_stat': numayende_stat,
            'rayon_stat': rayon_stat,
            'user_rol': user_rol,
            'filter_bolge': filter_bolge,
            'filter_tarix_bas': filter_tarix_bas,
            'filter_tarix_son': filter_tarix_son,
        },
    )

@vizit_login_required
def aptek_vizit_view(request):
    dermanlar = Medical.objects.filter(status=True).order_by('med_name')
    return render(request, 'vizit/aptek-vizit.html', {
        'dermanlar': dermanlar,
    })


@vizit_login_required
def statistika(request):
    
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])
    
    bolge_id = request.GET.get('bolge_id') or (user_bolge_ids[0] if user_rol != Istifadeci.ROL_REHBER else None)
    tarix_bas = request.GET.get('tarix_bas') or date.today().replace(day=1).isoformat()
    tarix_son = request.GET.get('tarix_son') or date.today().isoformat()

    context = {'bolge_id': bolge_id, 'tarix_bas': tarix_bas, 'tarix_son': tarix_son}
    
    if user_rol == Istifadeci.ROL_REHBER:
        context['bolgeler'] = Region.objects.all().order_by('region_name')
    
    if bolge_id:
        # Nümayəndə statistikası
        context['num_stat'] = AptekVizit.objects.filter(bolge_id=bolge_id, tarix__range=[tarix_bas, tarix_son]) \
            .values('user__ad') \
            .annotate(c=Count('id')) \
            .order_by('-c')

        # Rayon statistikası
        context['rayon_stat'] = AptekVizit.objects.filter(bolge_id=bolge_id, tarix__range=[tarix_bas, tarix_son]) \
            .values('rayon__city_name') \
            .annotate(c=Count('id')) \
            .order_by('-c')

        # Top apteklər
        context['aptek_stat'] = AptekVizit.objects.filter(bolge_id=bolge_id, tarix__range=[tarix_bas, tarix_son]) \
            .values('aptek_ad') \
            .annotate(c=Count('aptek_ad')) \
            .order_by('-c')[:10]

    return render(request, 'vizit/aptek-stats.html', context)

@login_required
def ajax_rayonlar(request):
    bolge_id = request.GET.get('bolge_id')
    if not bolge_id:
        return JsonResponse([], safe=False)
    
    rayonlar = City.objects.filter(
        region_id=bolge_id
    ).order_by('city_name').values('id', 'city_name')
    
    data = [{'id': r['id'], 'ad': r['city_name']} for r in rayonlar]
    return JsonResponse(data, safe=False)

@vizit_login_required
def yeni_aptek_vizit(request):
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    # Bakı bölgə ID-lərini təyin et
    baki_bolge_ids = list(
        Region.objects.filter(region_type='Bakı')
        .values_list('id', flat=True)
    )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                bolge_id      = request.POST.get('bolge_id')
                rayon_id      = request.POST.get('rayon_id') or None
                aptek_ad      = request.POST.get('aptek_ad', '').strip()
                aptek_nomre   = request.POST.get('aptek_nomre', '').strip()
                ref_veziyyeti = request.POST.get('ref_veziyyeti', '').strip()
                aptek_iscisi  = request.POST.get('aptek_iscisi', '').strip()
                qeyd          = request.POST.get('qeyd', '').strip()

                # Validasiya — yalnız bölgə mütləqdir, digər sahələr ixtiyaridir
                if not bolge_id:
                    messages.error(request, "Bölgə seçilməyib!")
                    return redirect('vizit:yeni_aptek_vizit')

                bolge = Region.objects.filter(id=bolge_id).first()
                is_baki = bolge and bolge.region_type == 'Bakı'
                if is_baki:
                    rayon_id = None
                elif rayon_id:
                    rayon_id = rayon_id
                else:
                    rayon_id = None

                # AptekVizit yarat
                vizit = AptekVizit.objects.create(
                    user_id=user_id,
                    bolge_id=bolge_id,
                    rayon_id=rayon_id,
                    aptek_ad=aptek_ad or "—",
                    aptek_nomre=aptek_nomre or None,
                    tarix=timezone.now().date(),
                    vaxt=timezone.now().time(),
                    qeyd=qeyd or None,
                )

                # Preparatları saxla
                sorusulub_ids = request.POST.getlist('sorusulub')
                satilib_ids   = request.POST.getlist('satilib')
                yoxdur_ids    = request.POST.getlist('yoxdur')

                all_ids = set(sorusulub_ids + satilib_ids + yoxdur_ids)

                objs = []
                for pid in all_ids:
                    if not pid:
                        continue
                    objs.append(AptekVizitPreparat(
                        aptek_vizit=vizit,
                        preparat_id=int(pid),
                        sorusulub=pid in sorusulub_ids,
                        satilib=pid in satilib_ids,
                        movcuddur=pid not in yoxdur_ids,
                        ref_vez=ref_veziyyeti,
                        aptek_iscisi=aptek_iscisi or None,
                        qeyd=qeyd or None,
                    ))

                AptekVizitPreparat.objects.bulk_create(objs)
                
                messages.success(request, "✅ Aptek viziti uğurla qeydə alındı!")
                return redirect('vizit:yeni_aptek_vizit')

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")
            return redirect('vizit:yeni_aptek_vizit')

    # ✅ GET - Bölgələri rol və user-ə görə filtrələ
    bolgeler = _bolgeler_for_user(user_rol, user_bolge_ids)
    
    # ✅ Yalnız aktiv dərmanları göstər
    preparatlar = Medical.objects.filter(status=True).order_by('med_name')
    
    # ✅ Bugünkü vizitləri filtrələ
    bugun_vizitler = AptekVizit.objects.filter(
        tarix=date.today()
    ).select_related('rayon', 'bolge', 'user').prefetch_related('preparatlar__preparat').order_by('-id')

    # ✅ Rəhbər deyilsə, yalnız öz vizitlərini görsün
    if user_rol not in [Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB]:
        bugun_vizitler = bugun_vizitler.filter(user_id=user_id)

    bugun_list = []
    for v in bugun_vizitler:
        preps = list(v.preparatlar.all())

        def _names(pred):
            names = []
            for p in preps:
                if pred(p) and p.preparat_id:
                    names.append(p.preparat.med_full_name or p.preparat.med_name)
            return ", ".join(names) if names else "—"

        v.display_sorusulan = _names(lambda p: p.sorusulub)
        v.display_satilib = _names(lambda p: p.satilib)
        v.display_yoxdur = _names(lambda p: not p.movcuddur)
        bugun_list.append(v)

    from .aptek_vizit_pdf import aptek_vizit_share_context
    share_ctx = aptek_vizit_share_context(request)

    return render(request, 'vizit/aptek-vizit.html', {
        'bolgeler': bolgeler,
        'preparatlar': preparatlar,
        'bugun_vizitler': bugun_list,
        'today': date.today(),
        'baki_bolge_ids': baki_bolge_ids,
        **share_ctx,
    })
@vizit_login_required
def create_day_recipe(request):
    user_id = request.session.get('istifadeci_id')
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])
    regions = _bolgeler_for_user(user_rol, user_bolge_ids)
    drugs = Medical.objects.filter(status=True).order_by('id')
    bugun = timezone.localdate()

    last_qs = (
        DayRecipeDrug.objects.select_related(
            'recipe__dr', 'recipe__region', 'drug'
        ).order_by('-created_at', '-id')
    )
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        last_qs = last_qs.filter(recipe__created_by_id=user_id)
    last_recipes = last_qs[:5]

    today_recipes = (
        DayRecipe.objects.filter(date=bugun)
        .select_related('dr', 'region')
        .prefetch_related('drugs__drug')
        .order_by('-created_at')
    )
    if user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        today_recipes = today_recipes.filter(created_by_id=user_id)

    from .day_recipe_pdf import day_recipe_share_context
    share_ctx = day_recipe_share_context(request)

    selected_region = ""
    selected_doctor = ""
    selected_date = ""
    doctors = Doctors.objects.none()

    if request.method == "POST":
        region_id = request.POST.get("region", "")
        doctor_id = request.POST.get("doctor", "")
        date_str = request.POST.get("date", "")

        selected_region = region_id
        selected_doctor = doctor_id
        selected_date = date_str

        # Tarixi parse et
        try:
            istifade_olunacaq_tarix = date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, "Zəhmət olmasa düzgün tarix seçin.")
            doctors = Doctors.objects.filter(bolge_id=region_id).order_by("id") if region_id else Doctors.objects.none()
            return render(request, "vizit/add-day-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "last_recipes": last_recipes,
                "today_recipes": today_recipes,
                "today_count": today_recipes.count(),
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_doctor_name": _doctor_display_name(selected_doctor),
                "selected_date": selected_date,
                **share_ctx,
            })

        # Həkimləri göstər
        doctors = Doctors.objects.filter(bolge_id=region_id) if region_id else Doctors.objects.none()

        # Region və həkim yoxdursa
        if not (region_id and doctor_id):
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "vizit/add-day-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "last_recipes": last_recipes,
                "today_recipes": today_recipes,
                "today_count": today_recipes.count(),
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_doctor_name": _doctor_display_name(selected_doctor),
                "selected_date": selected_date,
                **share_ctx,
            })

        # DayRecipe yarat
        recipe = DayRecipe.objects.create(
            region_id=region_id,
            dr_id=doctor_id,
            date=istifade_olunacaq_tarix,
            created_by_id=request.session.get('istifadeci_id')
        )
        doctor = Doctors.objects.get(id=doctor_id)

        # Əlavə olunan dərmanları qeyd et
        for key in request.POST:
            if key.startswith("quantity_"):
                drug_id = key.split("_")[1]
                count = request.POST.get(key)
                if count and float(count) > 0:
                    DayRecipeDrug.objects.create(
                        recipe=recipe,
                        drug_id=drug_id,
                        number=count
                    )

        messages.success(request, f"{doctor.ad} həkimə günlük resept {selected_date} tarixi ilə əlavə olundu.")
        return redirect('vizit:create_day_recipe')

    else:
        doctors = Doctors.objects.none()

    return render(request, "vizit/add-day-recipe.html", {
        "regions": regions,
        "doctors": doctors,
        "last_recipes": last_recipes,
        "today_recipes": today_recipes,
        "today_count": today_recipes.count(),
        "drugs": drugs,
        "selected_region": selected_region,
        "selected_doctor": selected_doctor,
        "selected_doctor_name": _doctor_display_name(selected_doctor),
        "selected_date": selected_date,
        **share_ctx,
    })

def _doctor_display_name(pk):
    if pk is None or pk == "":
        return ""
    try:
        ad = Doctors.objects.filter(pk=int(pk)).values_list("ad", flat=True).first()
        return ad or ""
    except (ValueError, TypeError):
        return ""


def ajax_doctors_by_region(request):
    region_id = request.GET.get('region_id')
    if region_id:
        doctors = Doctors.objects.filter(bolge_id=region_id).values('id', 'ad', 'ixtisas')
        doctors_list = list(doctors)
        print(f"DEBUG: region_id={region_id}, doctors_count={len(doctors_list)}")
        print(f"DEBUG: doctors_list={doctors_list[:3] if doctors_list else 'empty'}")
        return JsonResponse({'doctors': doctors_list})
    else:
        print("DEBUG: No region_id provided")
        return JsonResponse({'doctors': []})


def _day_recipe_filtered_qs(request):
    """Günlük resept statistikası üçün ortaq filtr queryset."""
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])

    filter_region = (request.GET.get('region_id') or '').strip()
    filter_date_from = (request.GET.get('date_from') or '').strip()
    filter_date_to = (request.GET.get('date_to') or '').strip()
    search = (request.GET.get('search') or '').strip()

    recipes = DayRecipe.objects.select_related(
        'dr', 'region', 'created_by'
    ).prefetch_related('drugs__drug')

    if filter_region:
        recipes = recipes.filter(region_id=filter_region)
    elif user_rol not in (Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB):
        recipes = recipes.filter(region_id__in=user_bolge_ids)

    if filter_date_from:
        recipes = recipes.filter(date__gte=filter_date_from)
    if filter_date_to:
        recipes = recipes.filter(date__lte=filter_date_to)

    if search:
        recipes = recipes.filter(
            Q(dr__ad__icontains=search)
            | Q(region__region_name__icontains=search)
            | Q(created_by__login__icontains=search)
            | Q(created_by__ad__icontains=search)
            | Q(drugs__drug__med_name__icontains=search)
            | Q(drugs__drug__med_full_name__icontains=search)
        ).distinct()

    return recipes.order_by('-date', '-created_at'), {
        'filter_region': filter_region,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'search': search,
    }


@rehber_required
def day_recipe_stats(request):
    user_rol = request.session.get('rol')
    user_bolge_ids = request.session.get('bolge_ids', [])
    regions = _bolgeler_for_user(user_rol, user_bolge_ids)

    recipes, filters = _day_recipe_filtered_qs(request)

    total_recipes = recipes.count()
    drug_agg = DayRecipeDrug.objects.filter(recipe__in=recipes).aggregate(
        line_count=Count('id'),
        qty_sum=Sum('number'),
    )
    total_drug_lines = drug_agg['line_count'] or 0
    total_quantity = drug_agg['qty_sum'] or 0

    top_drugs = list(
        DayRecipeDrug.objects.filter(recipe__in=recipes)
        .values('drug__med_name', 'drug__med_full_name')
        .annotate(total=Sum('number'))
        .order_by('-total')[:8]
    )

    recipe_rows = []
    for recipe in recipes[:200]:
        drug_lines = list(recipe.drugs.all())
        row_total = sum(float(line.number or 0) for line in drug_lines)
        recipe_rows.append({
            'recipe': recipe,
            'drugs': drug_lines,
            'row_total': row_total,
        })

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'regions': regions,
        'recipe_rows': recipe_rows,
        'total_recipes': total_recipes,
        'total_drug_lines': total_drug_lines,
        'total_quantity': total_quantity,
        'top_drugs': top_drugs,
        'query_string': query_params.urlencode(),
        **filters,
    }
    return render(request, 'vizit/day-recipe-stats.html', context)


@rehber_required
def export_day_recipe_stats(request):
    recipes, filters = _day_recipe_filtered_qs(request)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Günlük Qeydiyyat"

    header_fill = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")
    header_font = Font(name="Segoe UI", bold=True, color="FFFFFF", size=11)
    thin = Border(
        left=Side(style="thin", color="BFCFDF"),
        right=Side(style="thin", color="BFCFDF"),
        top=Side(style="thin", color="BFCFDF"),
        bottom=Side(style="thin", color="BFCFDF"),
    )
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    headers = [
        "№", "Tarix", "Bölgə", "Həkim", "İstifadəçi",
        "Dərman", "Say", "Yüklənmə",
    ]
    for col, title in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = thin

    row_num = 2
    idx = 1
    for recipe in recipes:
        region_name = recipe.region.region_name if recipe.region_id else ""
        doctor_name = recipe.dr.ad if recipe.dr_id else ""
        user_name = ""
        if recipe.created_by_id:
            user_name = recipe.created_by.ad or recipe.created_by.login or ""
        date_str = recipe.date.strftime("%d.%m.%Y") if recipe.date else ""
        created_str = ""
        if recipe.created_at:
            created_at = recipe.created_at
            if timezone.is_aware(created_at):
                created_at = timezone.localtime(created_at)
            created_str = created_at.strftime("%d.%m.%Y %H:%M")
        drug_lines = list(recipe.drugs.all())
        if not drug_lines:
            values = [idx, date_str, region_name, doctor_name, user_name, "—", 0, created_str]
            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row_num, column=col, value=val)
                cell.border = thin
                cell.alignment = center if col in (1, 2, 7, 8) else left
            row_num += 1
            idx += 1
            continue

        for line in drug_lines:
            drug = line.drug
            drug_name = (drug.med_full_name or drug.med_name) if drug else ""
            values = [
                idx, date_str, region_name, doctor_name, user_name,
                drug_name, float(line.number or 0), created_str,
            ]
            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row_num, column=col, value=val)
                cell.border = thin
                cell.alignment = center if col in (1, 2, 7, 8) else left
            row_num += 1
            idx += 1

    widths = [6, 12, 16, 28, 18, 36, 10, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.auto_filter.ref = f"A1:H{max(row_num - 1, 1)}"
    ws.freeze_panes = "A2"

    # Xülasə sheet
    ws2 = wb.create_sheet("Xülasə")
    ws2["A1"] = "Günlük qeydiyyat xülasəsi"
    ws2["A1"].font = Font(bold=True, size=13, color="1A5276")
    ws2["A3"] = "Bölgə filtri"
    ws2["B3"] = filters["filter_region"] or "Hamısı"
    ws2["A4"] = "Tarixdən"
    ws2["B4"] = filters["filter_date_from"] or "—"
    ws2["A5"] = "Tarixədək"
    ws2["B5"] = filters["filter_date_to"] or "—"
    ws2["A6"] = "Axtarış"
    ws2["B6"] = filters["search"] or "—"
    ws2["A8"] = "Resept sayı"
    ws2["B8"] = recipes.count()
    qty = DayRecipeDrug.objects.filter(recipe__in=recipes).aggregate(s=Sum("number"))["s"] or 0
    ws2["A9"] = "Ümumi qutu/say"
    ws2["B9"] = float(qty)
    ws2.column_dimensions["A"].width = 18
    ws2.column_dimensions["B"].width = 24

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"gunluk_qeydiyyat_{date.today().isoformat()}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def del_day_recipe(request, id):
    rm_recipe = get_object_or_404(DayRecipeDrug, id=id)
    doctor = rm_recipe.recipe.dr
    doctor_id = doctor.id if doctor else None
    rm_recipe.delete()

    next_url = request.GET.get('next')
    if next_url == 'create_day_recipe':
        return redirect('vizit:create_day_recipe')
    if next_url == 'day_recipe_stats':
        return redirect('vizit:day_recipe_stats')
    if doctor_id:
        return redirect('vizit:doctor_detail', doctor_id=doctor_id)
    return redirect('vizit:day_recipe_stats')


def del_day_recipe_record(request, id):
    """Bütün günlük resept qeydini silir."""
    recipe = get_object_or_404(DayRecipe, id=id)
    recipe.delete()
    messages.success(request, "Günlük qeydiyyat silindi.")

    params = request.GET.copy()
    params.pop('next', None)
    url = reverse('vizit:day_recipe_stats')
    if params:
        url = f"{url}?{params.urlencode()}"
    return redirect(url)


def export_to_excel(request):
    # 1. Filtrləri qəbul edirik
    bolge_id = request.GET.get('bolge_id')
    tarix_bas = request.GET.get('tarix_bas') or date.today().replace(day=1).isoformat()
    tarix_son = request.GET.get('tarix_son') or date.today().isoformat()
    
    # 2. Workbook yaradılması və şəbəkə xətləri
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aptek Vizit Blanki"
    ws.views.sheetView[0].showGridLines = True
    
    # Dizayn və Rəng Palitrası (Şəkildəki kimi)
    HEADER_BLUE = "205478"     
    MAIN_TEAL = "1ABC9C"       
    fill_title = PatternFill(start_color=HEADER_BLUE, end_color=HEADER_BLUE, fill_type="solid")
    fill_header = PatternFill(start_color=MAIN_TEAL, end_color=MAIN_TEAL, fill_type="solid")
    fill_meta = PatternFill(start_color="F2F4F4", end_color="F2F4F4", fill_type="solid")
    
    font_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_meta = Font(name="Segoe UI", size=10, bold=True, color="000000")
    font_data = Font(name="Segoe UI", size=10)
    
    # ✓ və ✗ üçün rəngli fontlar
    font_check = Font(name="Segoe UI", size=11, bold=True, color="1B5E20") 
    font_cross = Font(name="Segoe UI", size=11, bold=True, color="B71C1C") 
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    thin_border = Border(
        left=Side(style='thin', color='BDC3C7'),
        right=Side(style='thin', color='BDC3C7'),
        top=Side(style='thin', color='BDC3C7'),
        bottom=Side(style='thin', color='BDC3C7')
    )
    
    # 3. Filtrlərə görə Ana Vizitləri select_related ilə sürətli çəkirik
    vizit_queryset = AptekVizit.objects.select_related('user', 'rayon', 'bolge').all()
    if bolge_id:
        vizit_queryset = vizit_queryset.filter(bolge_id=bolge_id)
    if tarix_bas and tarix_son:
        vizit_queryset = vizit_queryset.filter(tarix__range=[tarix_bas, tarix_son])
        
    vizitler = vizit_queryset.order_by('tarix', 'vaxt')
    
    # 4. ÜST BANNER (Row 1)
    ws.merge_cells("A1:CA1")
    ws["A1"] = f"SOLVEY PHARMA — APTEK VİZİT BLANKI | {tarix_bas} - {tarix_son}"
    ws["A1"].font = font_title
    ws["A1"].fill = fill_title
    ws["A1"].alignment = Alignment(horizontal="right", vertical="center")
    ws.row_dimensions[1].height = 35
    
    # 5. META MƏLUMATLAR (Row 3)
    bolge_adi = "Bütün bölgələr"
    if bolge_id:
        try:
            bolge_adi = Region.objects.get(id=bolge_id).region_name
        except:
            pass
            
    ws.merge_cells("A3:B3")
    ws["A3"] = f"Bölgə: {bolge_adi}"
    ws["A3"].font = font_meta
    ws["A3"].fill = fill_meta
    ws["A3"].border = thin_border
    
    ws.merge_cells("C3:E3")
    ws["C3"] = f"Tarix: {tarix_bas} / {tarix_son}"
    ws["C3"].font = font_meta
    ws["C3"].fill = fill_meta
    ws["C3"].border = thin_border
    ws.row_dimensions[3].height = 22
    
    # 6. ƏSAS SOL BAŞLIQLAR (Row 4 və Row 5 Birləşir)
    base_headers = ["#", "Aptekin adı və nömrəsi", "Rayon", "Rəfdəki vəziyyət", "Aptek işçisi", "Vaxt", "Nümayəndə"]
    for i, h in enumerate(base_headers):
        col = get_column_letter(i + 1)
        ws.merge_cells(f"{col}4:{col}5")
        ws[f"{col}4"] = h
        ws[f"{col}4"].font = font_header
        ws[f"{col}4"].fill = fill_header
        ws[f"{col}4"].alignment = align_center
        ws[f"{col}4"].border = thin_border
        
    # 7. DƏRMAN BAŞLIQLARI (Dinamik - Medical Modelindən)
    preparatlar = Medical.objects.all().order_by('med_name')
    current_col = 8 # H sütunundan başlayır (8-ci sütun)
    
    preparat_col_mapping = {} 
    for p in preparatlar:
        start_col = get_column_letter(current_col)
        end_col = get_column_letter(current_col + 2)
        
        # Dərmanın Adı (Üst Sətir)
        ws.merge_cells(f"{start_col}4:{end_col}4")
        ws[f"{start_col}4"] = p.med_name
        ws[f"{start_col}4"].font = font_header
        ws[f"{start_col}4"].fill = fill_header
        ws[f"{start_col}4"].alignment = align_center
        
        # Alt Başlıqlar
        sub_headers = ["Soruşulan", "Satılıb", "Mövcud"]
        for j, sub in enumerate(sub_headers):
            sub_col = get_column_letter(current_col + j)
            ws[f"{sub_col}5"] = sub
            ws[f"{sub_col}5"].font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
            ws[f"{sub_col}5"].fill = fill_header
            ws[f"{sub_col}5"].alignment = align_center
            
        preparat_col_mapping[p.id] = current_col
        current_col += 3
        
    ws.row_dimensions[4].height = 24
    ws.row_dimensions[5].height = 22
    
    # Başlıqlara border verilməsi
    for r in [4, 5]:
        for c in range(1, current_col):
            ws.cell(row=r, column=c).border = thin_border
            
    # 8. SƏTİRLƏRİN REAL DATA İLƏ DOLDURULMASI
    row_num = 6
    for idx, v in enumerate(vizitler, start=1):
        
        # Bu vizitə bağlı olan bütün preparat qeydlərini (`related_name='preparatlar'`) çəkirik
        vizit_preparatlari = v.preparatlar.all()
        
        # Excel-dəki "Rəfdəki vəziyyət" və "Aptek işçisi" sütunları üçün dataları götürürük
        # (Vizitə aid ilk dərmanın qeydini və ya tapılan ilk boş olmayan dəyəri götürür)
        ref_veziyyeti_degeri = ""
        aptek_iscisi_degeri = ""
        for vp in vizit_preparatlari:
            if vp.ref_vez:
                ref_veziyyeti_degeri = vp.ref_vez
            if vp.aptek_iscisi:
                aptek_iscisi_degeri = vp.aptek_iscisi
            if ref_veziyyeti_degeri and aptek_iscisi_degeri:
                break

        # Sətir məlumatlarının yazılması
        ws.cell(row=row_num, column=1, value=idx).alignment = align_center
        
        aptek_tam_ad = f"{v.aptek_ad} {v.aptek_nomre or ''}".strip()
        ws.cell(row=row_num, column=2, value=aptek_tam_ad).alignment = align_left
        
        rayon_ad = v.rayon.city_name if v.rayon else ""
        ws.cell(row=row_num, column=3, value=rayon_ad).alignment = align_center
        
        # Sizin istədiyiniz model dəyişəni bura oturtuldu: `v.ref_vez` əvəzinə `ref_veziyyeti_degeri`
        ws.cell(row=row_num, column=4, value=ref_veziyyeti_degeri).alignment = align_center
        ws.cell(row=row_num, column=5, value=aptek_iscisi_degeri).alignment = align_left
        
        # Tarix və Vaxtın birləşdirilməsi formatı (Məs: 02.06.2026 23:40)
        tarix_str = v.tarix.strftime("%d.%m.%Y") if v.tarix else ""
        vaxt_str = v.vaxt.strftime("%H:%M") if v.vaxt else ""
        vaxt_tam = f"{tarix_str} {vaxt_str}".strip()
        ws.cell(row=row_num, column=6, value=vaxt_tam).alignment = align_center
        
        numayende_ad = v.user.ad if v.user else ""
        ws.cell(row=row_num, column=7, value=numayende_ad).alignment = align_left
        
        # Sol tərəfə stil vermək
        for c in range(1, 8):
            ws.cell(row=row_num, column=c).font = font_data
            ws.cell(row=row_num, column=c).border = thin_border
            
        # ── MATRİSİN (DƏRMAN STATUSLARININ) DOLDURULMASI ──
        # Vizit preparatlarını sürətli axtarış üçün dictionary halına salırıq
        vp_dict = {vp.preparat_id: vp for vp in vizit_preparatlari}
        
        for p_id, col_start in preparat_col_mapping.items():
            s_cell = ws.cell(row=row_num, column=col_start)
            sat_cell = ws.cell(row=row_num, column=col_start + 1)
            m_cell = ws.cell(row=row_num, column=col_start + 2)
            
            # Hər üç hüceyrə üçün ilkin border və nizamlamanı veririk
            for cell in [s_cell, sat_cell, m_cell]:
                cell.alignment = align_center
                cell.border = thin_border
            
            # Əgər bu vizitdə bu dərmana aid qeyd (sətir) varsa:
            if p_id in vp_dict:
                vp_obj = vp_dict[p_id]
                
                # 1. Soruşulubsa "✓" yaz
                if vp_obj.sorusulub:
                    s_cell.value = "✓"
                    s_cell.font = font_check
                    
                # 2. Satılıbsa "✓" yaz
                if vp_obj.satilib:
                    sat_cell.value = "✓"
                    sat_cell.font = font_check
                    
                # 3. Mövcuddursa "✓", yoxsa "✗" yaz
                if vp_obj.movcuddur:
                    m_cell.value = "✓"
                    m_cell.font = font_check
                else:
                    m_cell.value = "✗"
                    m_cell.font = font_cross
            else:
                # Əgər vizit zamanı bu dərman haqqında heç bir qeyd daxil edilməyibsə, 
                # "Mövcuddur" bölməsini standart olaraq boş və ya şəkildəki kimi nəzarətsiz buraxırıq.
                pass
                
        ws.row_dimensions[row_num].height = 24
        row_num += 1
        
    # 9. Sütun ölçülərinin avtomatik nizamlanması
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        if col[0].column <= 7:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
        else:
            ws.column_dimensions[col_letter].width = 10 
            
    # H6 sütunundan paneli dondururuq
    ws.freeze_panes = "H6"
    
    # 10. Brauzerə ötürmə
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="Solvey_Aptek_Hesabat_{tarix_bas}.xlsx"'
    wb.save(response)
    return response