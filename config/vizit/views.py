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


def _bolgeler_for_user(user_rol, user_bolge_id):
    if user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER) and user_bolge_id:
        return Region.objects.filter(pk=user_bolge_id)
    return Region.objects.order_by('region_name')


def _api_bolge_icazesi(request, bolge_id):
    """ajax.php: nümayəndə/menecer yalnız öz bölgəsinə baxa bilər."""
    user_rol = request.session.get('rol')
    user_bolge_id = request.session.get('bolge_id')
    if user_rol in (Istifadeci.ROL_NUMAYENDE, Istifadeci.ROL_MENECER) and user_bolge_id:
        try:
            return int(bolge_id) == int(user_bolge_id)
        except (TypeError, ValueError):
            return False
    return True


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
        if 'add_user' in request.POST:
            login = request.POST.get('login', '').strip()
            sifre = request.POST.get('sifre', '').strip()
            ad = request.POST.get('ad', '').strip()
            rol = request.POST.get('rol', Istifadeci.ROL_NUMAYENDE)
            bolge_id = request.POST.get('bolge_id', '')
            bolge_id = int(bolge_id) if bolge_id else None

            if login and sifre and ad:
                try:
                    istifadeci = Istifadeci(login=login, ad=ad, rol=rol, bolge_id=bolge_id, aktiv=True)
                    istifadeci.set_password(sifre)
                    istifadeci.save()
                    messages.success(request, '✅ İstifadəçi əlavə edildi.')
                except IntegrityError:
                    messages.error(request, '❌ Xəta: login artıq mövcuddur.')
            else:
                messages.error(request, '❌ Bütün sahələri doldurun.')

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
                        messages.error(
                            request,
                            '❌ Bu rayon/bölgə üçün xəstəxana tapılmadı. Əvvəlcə admin paneldə xəstəxana əlavə edin.',
                        )
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

    if 'del_user' in request.GET:
        Istifadeci.objects.filter(pk=int(request.GET['del_user'])).delete()
        messages.success(request, '✅ Əməliyyat uğurla icra edildi (İstifadəçi silindi).')
        return _admin_redirect('istifadeciler')

    return render(
        request,
        'vizit/admin_panel.html',
        {
            'tab': tab,
            'istifadeciler': Istifadeci.objects.select_related('bolge').order_by('rol', 'ad'),
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
    user_id = request.session['istifadeci_id']
    user_rol = request.session.get('rol')
    user_bolge_id = request.session.get('bolge_id')
    bugun = timezone.localdate()

    if request.method == 'POST' and 'vizit_bagla' in request.POST:
        hekim_id = request.POST.get('hekim_id')
        rayon_id = request.POST.get('rayon_id')
        bolge_id = request.POST.get('bolge_id')
        munasibat = request.POST.get('munasibat', '')
        qeyd = request.POST.get('qeyd', '').strip()
        preparatlar = request.POST.getlist('preparatlar[]')

        if hekim_id and bolge_id and munasibat in MUNASIBAT_SECIMLERI and preparatlar:
            try:
                bolge_pk = int(bolge_id)
                hekim_pk = int(hekim_id)
            except (TypeError, ValueError):
                messages.error(request, '❌ Bütün sahələri düzgün doldurun.')
                return redirect('vizit:index')

            hekim = Doctors.objects.filter(pk=hekim_pk, is_active=True).first()
            if not hekim:
                messages.error(request, '❌ Bütün sahələri düzgün doldurun.')
                return redirect('vizit:index')

            effective_rayon_id = None
            if rayon_id:
                try:
                    effective_rayon_id = int(rayon_id)
                except (TypeError, ValueError):
                    pass
            elif hekim.city_id:
                effective_rayon_id = hekim.city_id

            now = timezone.localtime()
            vizit = Vizit.objects.create(
                istifadeci_id=user_id,
                hekim_id=hekim.pk,
                rayon_id=effective_rayon_id,
                bolge_id=bolge_pk,
                munasibat=munasibat,
                tarix=now.date(),
                vaxt=now.time().replace(second=0, microsecond=0),
                qeyd=qeyd or None,
            )
            VizitPreparat.objects.bulk_create(
                [VizitPreparat(vizit=vizit, preparat_id=int(pid)) for pid in preparatlar]
            )
            messages.success(request, '✅ Vizit uğurla qeydə alındı!')
        else:
            messages.error(request, '❌ Bütün sahələri düzgün doldurun.')
        return redirect('vizit:index')

    bugun_vizitler = (
        Vizit.objects.filter(tarix=bugun)
        .select_related('hekim', 'rayon', 'istifadeci')
        .prefetch_related('preparatlar__preparat')
        .order_by('-id')
    )
    if user_rol == Istifadeci.ROL_NUMAYENDE:
        bugun_vizitler = bugun_vizitler.filter(istifadeci_id=user_id)

    return render(
        request,
        'vizit/create-vizit.html',
        {
            'bolgeler': _bolgeler_for_user(user_rol, user_bolge_id),
            'preparatlar_siyahisi': Medical.objects.filter(status=True).order_by('med_name'),
            'bugun_vizitler': bugun_vizitler,
            'user_rol': user_rol,
            'bugun_tarix': bugun.strftime('%d.%m.%Y'),
        },
    )


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

    bolgeler = _bolgeler_for_user(user_rol, user_bolge_id)
    rayonlar = (
        City.objects.filter(region_id=f['filter_bolge_id']).order_by('city_name')
        if f['filter_bolge_id']
        else City.objects.none()
    )

    vizitler = vizitler_qs.order_by('-tarix', '-vaxt')
    total_vizit = vizitler.count()

    prep_stat = [
        {'ad': row['preparat__med_name'], 'c': row['c']}
        for row in (
            VizitPreparat.objects.filter(vizit__in=vizitler_qs.values('pk'))
            .values('preparat__med_name')
            .annotate(c=Count('id'))
            .order_by('-c')[:8]
        )
    ]

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
    user_bolge_id = request.session.get('bolge_id')
    today = timezone.localdate()

    default_tarix_bas = today.replace(day=1).isoformat()
    default_tarix_son = today.isoformat()

    filter_bolge = request.GET.get('bolge_id', '')
    if not filter_bolge and user_rol == Istifadeci.ROL_MENECER and user_bolge_id:
        filter_bolge = str(user_bolge_id)

    filter_tarix_bas = request.GET.get('tarix_bas') or default_tarix_bas
    filter_tarix_son = request.GET.get('tarix_son') or default_tarix_son

    bolgeler = _bolgeler_for_user(user_rol, user_bolge_id)

    numayende_stat = []
    rayon_stat = []
    if filter_bolge:
        numayende_stat, rayon_stat = _bolge_stat_data(
            int(filter_bolge), filter_tarix_bas, filter_tarix_son
        )

    return render(
        request,
        'vizit/bolge_stat.html',
        {
            'bolgeler': bolgeler,
            'numayende_stat': numayende_stat,
            'rayon_stat': rayon_stat,
            'user_rol': user_rol,
            'user_bolge_id': user_bolge_id,
            'filter_bolge': filter_bolge,
            'filter_tarix_bas': filter_tarix_bas,
            'filter_tarix_son': filter_tarix_son,
        },
    )