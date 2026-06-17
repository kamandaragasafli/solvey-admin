from django.shortcuts import render
from .models import  Calculate, Medical
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from vizit.models import Istifadeci
from django.contrib.auth import login as django_login, logout as django_logout   # Bura əlavə edildi
from django.contrib.auth.models import User



def login_user(request):
    if request.session.get('current_user_data'):
        return redirect('/groups/calculate/')

    if request.method == "POST":
        name_input = request.POST.get("name", "").strip()
        password_input = request.POST.get("password", "").strip()
        
        user = Istifadeci.objects.filter(
            login=name_input, 
            sifre=Istifadeci.hash_sifre(password_input), 
            aktiv=True
        ).first()
        
        if user is not None:
            # Əvvəlcə Django auth user ilə login ol
            django_auth_user, _ = User.objects.get_or_create(
                username=user.login,
                defaults={'first_name': user.ad, 'is_active': True}
            )
            django_auth_user.backend = 'django.contrib.auth.backends.ModelBackend'
            django_login(request, django_auth_user)
            
            # Django_login session flush etdikdən SONRA yaz
            request.session['current_user_data'] = user.session_dict()
            request.session.modified = True
            
            return redirect('/groups/calculate/')
        else:
            messages.error(request, "İstifadəçi adı və ya şifrə səhvdir!")
            return redirect('/groups/login/')
            
    # GET request — sistem user ilə middleware-i keç
    if not request.user.is_authenticated:
        system_user, _ = User.objects.get_or_create(username="system_groups_user")
        system_user.backend = 'django.contrib.auth.backends.ModelBackend'
        django_login(request, system_user)
            
    return render(request, "calculate/login.html")


def logout_user(request):
    request.session.flush()
    return redirect('/groups/login/')

# Qiymət siyahısı (Konstantlar funksiyalardan kənarda saxlanılır)
PRICES_NUMAYENDE_QRUP_1 = {
    "LEVOSTRONG": 0.6, "LIPOMAG": 3.6, "SOLSEDA": 1.5, "SOLTEP": 0.0,
    "ZEMOVAR": 2.3, "KALVEY": 0.0, "PAINSTOP": 1.5, "BETASOL": 2.1,
    "LITASOL": 1.7, "FENSAVIN": 1.6,
}

PRICES_NUMAYENDE_QRUP_2 = {
    "PROSTAZOLIN": 0.6, "HEPTRAZOL": 1.6, "OPEBLOCK": 2.4, "OPSIDOL": 0.0,
    "SERRASOL": 3.0, "GENOSFER": 1.6, "VITOMER": 1.2, "KARTOVEY": 0.0,
    "SOLTROP": 2.7, "ROPSOL": 1.4, "MOXIVISTA": 0.6,
}

# Menecer qiymətləri şəkildəki qruplara əsasən ikiyə bölündü
PRICES_MENECER_QRUP_1 = {
    "LEVOSTRONG": 0.4,
    "LIPOMAG": 3.0,     # "LIPOMAQ" -> "LIPOMAG" olaraq düzəldildi
    "SOLSEDA": 1.2,
    "SOLTEP": 0.0,
    "ZEMOVAR": 1.7,
    "KALVEY": 0.0,
    "PAINSTOP": 1.0,
    "BETASOL": 1.4,
    "LITASOL": 1.3,
    "FENSAVIN": 1.2,
}

PRICES_MENECER_QRUP_2 = {
    "PROSTAZOLIN": 0.4,
    "HEPTRAZOL": 1.4,
    "OPEBLOCK": 1.6,
    "OPSIDOL": 0.0,
    "SERRASOL": 2.0,
    "GENOSFER": 1.2,
    "VITOMER": 0.8,     # "Vitomer" adının qorunması təmin edilir
    "KARTOVEY": 0.0,
    "SOLTROP": 1.8,
    "ROPSOL": 0.9,
    "MOXIVISTA": 0.4,
}

# =========================================================================

def hesablamalar(request):
    # 1. TƏHLÜKƏSİZLİK: Əgər istifadəçi giriş etməyibsə, redirect edirik
    user_data = request.session.get('current_user_data')
    if not user_data:
        return redirect('/groups/login/')

    user_role = user_data.get('rol')   
    user_qrup = user_data.get('qrup')  

    # --- Yenilənmiş Qiymət və Qrup Filtrləmə Məntiqi ---
    if user_role in ['menecer', 'diviziya_rehb', 'rehber', 'admin']:
        # Menecer və rəhbərlər üçün qrup ayrımı
        if user_qrup == 'QRUP 2':
            active_prices = PRICES_MENECER_QRUP_2
        else:
            active_prices = PRICES_MENECER_QRUP_1
    else:
        # Nümayəndələr üçün qrup ayrımı
        if user_qrup == 'QRUP 2':
            active_prices = PRICES_NUMAYENDE_QRUP_2
        else:
            active_prices = PRICES_NUMAYENDE_QRUP_1

    display_names = {
        "LEVOSTRONG": "Levostrong", "LIPOMAG": "Lipomag", "SOLSEDA": "Solseda", 
        "SOLTEP": "Soltep", "ZEMOVAR": "Zemovar", "KALVEY": "Kalvey", 
        "PAINSTOP": "Painstop", "BETASOL": "Betasol", "LITASOL": "Litasol", 
        "FENSAVIN": "Fensavin", "PROSTAZOLIN": "Prostazolin", "HEPTRAZOL": "Heptrazol", 
        "OPEBLOCK": "Opeblock", "OPSIDOL": "Opsidol", "SERRASOL": "Serrasol", 
        "GENOSFER": "Genosfer", "VITOMER": "Vitomer D3", "KARTOVEY": "Kartovey", 
        "SOLTROP": "Soltrop", "ROPSOL": "Ropsol", "MOXIVISTA": "Moxivista"
    }

    filtered_items = []
    for med_key, price in active_prices.items():
        name_display = display_names.get(med_key, med_key.title())
        filtered_items.append({"med_name": name_display, "azn": price})

    context = {
        "medicals": filtered_items,
        "current_user": {
            "name": user_data.get("ad"),
            "role": user_role, 
            "group": user_qrup
        }
    }
    return render(request, "calculate/calculate.html", context)


def admin_page(request):
    # 1. TƏHLÜKƏSİZLİK: Giriş edilməyibsə dərhal /groups-drugs/login/ səhifəsinə göndər
    user_data = request.session.get('current_user_data')
    if not user_data:
        return redirect('/groups/login/')
    
    # 2. SƏLAHİYYƏT: Yalnız 'admin' və ya 'rehber' bu səhifəyə girə bilsin
    if user_data.get('rol') not in ['admin', 'rehber']:
        messages.error(request, "Bu səhifəyə giriş icazəniz yoxdur!")
        return redirect('/groups/calculate/')

    if request.method == "POST":
        login_input = request.POST.get("name")      
        password_input = request.POST.get("password")
        ad_input = request.POST.get("ad") or login_input 
        role = request.POST.get("role")
        group = request.POST.get("group") or None

        if login_input and password_input and role:
            if Istifadeci.objects.filter(login=login_input).exists():
                messages.error(request, f"'{login_input}' istifadəçi adı ilə artıq kimsə qeydiyyatdan keçib!")
            else:
                yeni_user = Istifadeci(
                    login=login_input,
                    ad=ad_input,
                    rol=role,
                    qrup=group,
                    aktiv=True
                )
                yeni_user.set_password(password_input)
                yeni_user.save()
                
                messages.success(request, "Yeni istifadəçi uğurla əlavə edildi.")
                return redirect('/groups/admin/') 
        else:
            messages.error(request, "Zəhmət olmasa tələb olunan bütün xanaları doldurun.")

    all_users = Istifadeci.objects.all().order_by('-id')
    
    context = {
        "users": all_users,
        "roles": Istifadeci.ROL_CHOICES,    
        "groups_list": Istifadeci.QRUP_CHOICES, 
        "current_user": user_data
    }
    return render(request, "calculate/admin_page.html", context)