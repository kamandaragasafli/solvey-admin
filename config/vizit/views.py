from datetime import datetime as dt
from urllib.parse import urlencode

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, F, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db import transaction


from doctors.models import Doctors
from medicine.models import Medical
from regions.models import City, Hospital, Region

from .models import Istifadeci, Vizit, VizitPreparat
from .utils import (
    menecer_rehber_required,
    rehber_required,
    vizit_giris_yoxla,
    vizit_login_required,
    vizit_session_temizle,
    vizit_session_yaz,
)

MUNASIBAT_SECIMLERI = [c[0] for c in Vizit.MUNASIBAT_CHOICES]

ROL_BASLIQLARI = {
    Istifadeci.ROL_NUMAYENDE: 'Tibbi Nümayəndə',
    Istifadeci.ROL_MENECER: 'Menecer',
    Istifadeci.ROL_REHBER: 'Diviziya Rəhbər',
}

EXCEL_PREP_ORDER = [
    'Solseda', 'Opsidol', 'Zemovar', 'Soltrop', 'Fensavin', 'Soltep', 'Litasol',
    'Prostazolin', 'Provital', 'Heptrazol', 'Vitomer Kids', 'Fesola', 'Kartovey',
    'Betasol', 'Genosfer', 'Serrasol', 'Kalvey', 'Vitomer D3', 'Levastronq',
    'Opeblok', 'Ropsol', 'Painstop', 'Moxivista',
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
            'hekim': vizit.hekim.ad,
            'ixtisas_kod': vizit.hekim.ixtisas,
            'kateqoriya': vizit.hekim.kategoriya,
            'rayon': vizit.rayon.get_city_name_display() if vizit.rayon else '',
            'munasibat': vizit.munasibat,
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
    return redirect('vizit:login')


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

            # Rol əsaslı məhdudiyyətlər
            if rol == Istifadeci.ROL_MENECER and len(valid_bolge_ids) > 3:
                messages.error(request, '❌ Menecer rolu üçün maksimum 3 bölgə seçilə bilər.')
                return _admin_redirect(tab)
            elif rol == Istifadeci.ROL_DIVIZIYA_REHB and len(valid_bolge_ids) > 5:
                messages.error(request, '❌ Diviziya Rəhbəri rolu üçün maksimum 3 bölgə seçilə bilər.')
                return _admin_redirect(tab)

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

    # 3. İSTİFADƏÇİ SİLMƏ (GET metodu ilə)
    if 'del_user' in request.GET:
        Istifadeci.objects.filter(pk=int(request.GET['del_user'])).delete()
        messages.success(request, '✅ İstifadəçi silindi.')
        return _admin_redirect('istifadeciler')

    # 4. SƏHİFƏNİ YÜKLƏMƏ
    return render(
        request,
        'vizit/admin_panel.html',
        {
            'tab': tab,
            'istifadeciler': Istifadeci.objects.prefetch_related('bolgeler').order_by('rol', 'ad'),
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
        hekim_id = request.POST.get('hekim_id')
        bolge_id = request.POST.get('bolge_id')
        munasibat = request.POST.get('munasibat', '')
        preparatlar = request.POST.getlist('preparatlar[]')

        # Seçimi sessiyada yadda saxlayırıq ki, növbəti dəfə avtomatik seçilsin
        if bolge_id:
            request.session['son_bolge_id'] = bolge_id

        if not hekim_id or not bolge_id or not preparatlar:
            messages.error(request, '❌ Bütün sahələri düzgün doldurun.')
            return redirect('vizit:index')

        try:
            with transaction.atomic():
                vizit = Vizit.objects.create(
                    istifadeci_id=user_id,
                    hekim_id=int(hekim_id),
                    bolge_id=int(bolge_id),
                    munasibat=munasibat,
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

    # GET sorğusu və ya Səhifənin açılması
    # Vizitləri filtrələmək: Rəhbərlər hamını, digərləri yalnız özünü görsün
    vizitler_query = Vizit.objects.filter(tarix=bugun)
    
    if user_rol not in [Istifadeci.ROL_REHBER, Istifadeci.ROL_DIVIZIYA_REHB]:
        vizitler_query = vizitler_query.filter(istifadeci_id=user_id)

    # Son seçilən bölgəni sessiyadan oxuyuruq
    selected_bolge_id = request.session.get('son_bolge_id')

    return render(request, 'vizit/create-vizit.html', {
        'bolgeler': _bolgeler_for_user(user_rol, user_bolge_ids),
        'selected_bolge_id': int(selected_bolge_id) if selected_bolge_id else None,
        'preparatlar_siyahisi': Medical.objects.filter(status=True).order_by('med_name'),
        'bugun_vizitler': vizitler_query.order_by('-id'),
        'user_rol': user_rol,
        'bugun_tarix': bugun,
    })


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
            'ixtisas_kod': d.ixtisas,
            'kateqoriya': d.kategoriya,
            'derece': d.derece,
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
    prep_sira = _excel_prep_sira()
    vizitler = _excel_export_rows(f['qs'])

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
            'colspan_count': 6 + len(prep_sira),
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