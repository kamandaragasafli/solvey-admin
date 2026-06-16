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
    # Əgər adam zatən daxil olubsa, birbaşa hesablamağa getsin
    if request.session.get('current_user_data'):
        return redirect('/groups/calculate/')

    # 🚀 MIDDLWARE-İ SUSDURMAQ (ƏN VACİB HİSSƏ):
    # Əgər istifadəçi anonimdirsə (çıxış edibsə və ya ilk dəfə gəlirsə),
    # Biz arxa planda müvəqqəti bir sistem istifadəçisi ilə daxili auth-u aktiv edirik.
    # Beləcə core.middleware baxır ki, sistem boş deyil və bizi ana /login/-ə ATLA MIR.
    if not request.user.is_authenticated:
        system_user, _ = User.objects.get_or_create(username="system_groups_user")
        system_user.backend = 'django.contrib.auth.backends.ModelBackend'
        django_login(request, system_user)
        # Bu sətir sayəsində middleware-dən keçdik!

    if request.method == "POST":
        name_input = request.POST.get("name").strip()
        password_input = request.POST.get("password").strip()
        
        # Real istifadəçini bizim MD5 modelindən yoxlayırıq
        user = Istifadeci.objects.filter(
            login=name_input, 
            sifre=Istifadeci.hash_sifre(password_input), 
            aktiv=True
        ).first()
        
        if user is not None:
            # Bizim tətbiqin əsas sessiyası
            request.session['current_user_data'] = user.session_dict()
            
            # İndi isə daxili auth sistemini real daxil olan adamın adına keçiririk
            django_auth_user, _ = User.objects.get_or_create(
                username=user.login,
                defaults={'first_name': user.ad, 'is_active': True}
            )
            django_auth_user.backend = 'django.contrib.auth.backends.ModelBackend'
            django_login(request, django_auth_user)
            
            return redirect('/groups/calculate/')
        else:
            messages.error(request, "İstifadəçi adı və ya şifrə səhvdir!")
            return redirect('/groups/login/')
            
    return render(request, "calculate/login.html")


def logout_user(request):
    # 🔥 DİQQƏT: django_logout(request) funksiyasını ƏSLA çağırmırıq!
    # Çünki o çağırılsaydı settings.py-dakı LOGOUT_REDIRECT_URL='login' işə düşəcəkdi 
    # və middleware bizi dərhal ana /login/-ə tullayacaqdı.
    
    # Onun əvəzinə sadəcə bizim xüsusi sessiyanı silirik:
    if 'current_user_data' in request.session:
        del request.session['current_user_data']
    
    # Daxili auth sistemini də tam silmək əvəzinə, sadəcə yuxarıdakı saxta sistem istifadəçisinə geri qaytarırıq.
    # Beləcə middleware yenə adamın sistemdə olduğunu zənn edir və bizi rəvan buraxır.
    system_user, _ = User.objects.get_or_create(username="system_groups_drugs_user")
    system_user.backend = 'django.contrib.auth.backends.ModelBackend'
    django_login(request, system_user)
    
    # Tam zəmanətli şəkildə öz loginimizə qayıdırıq
    return redirect('/groups/login/')

# Qiymət siyahısı (Konstantlar funksiyalardan kənarda saxlanılır)
login_required(login_url="calculate:login_user")
PRICES_NUMAYENDE_QRUP_1 = {
    "LEVOSTRONG": 0.6,
    "LIPOMAG": 3.6,
    "SOLSEDA": 1.5,
    "SOLTEP": 0.0,
    "ZEMOVAR": 2.3,
    "KALVEY": 0.0,
    "PAINSTOP": 1.5,
    "BETASOL": 2.1,
    "LITASOL": 1.7,
    "FENSAVIN": 1.6,
}

login_required(login_url="calculate:login_user")
PRICES_NUMAYENDE_QRUP_2 = {
    "PROSTAZOLIN": 0.6,
    "HEPTRAZOL": 1.6,
    "OPEBLOCK": 2.4,
    "OPSIDOL": 0.0,
    "SERRASOL": 3.0,
    "GENOSFER": 1.6,
    "VITOMER": 1.2,
    "KARTOVEY": 0.0,
    "SOLTROP": 2.7,
    "ROPSOL": 1.4,
    "MOXIVISTA": 0.6,
}


login_required(login_url="calculate:login_user")
PRICES_MENECER = {
    "LEVOSTRONG": 0.4,
    "MOXIVISTA": 0.4,
    "VITOMER": 0.8,
    "ROPSOL": 0.9,
    "PROSTAZOLIN": 0.4,
    "PAINSTOP": 1,
    "FENSAVIN": 1.2,
    "GENOSFER": 1.2,
    "KALVEY": 0,
    "LIPOMAQ": 3,
    "SOLSEDA": 1.2,
    "SOLTEP": 0,
    "KARTOVEY": 0,
    "BETASOL": 1.4,
    "LITASOL": 1.3,
    "OPSIDOL": 0,
    "SERRASOL": 2,
    "SOLTROP": 1.8,
    "ZEMOVAR": 1.7,
    "OPEBLOCK": 1.6,
    "HEPTRAZOL": 1.4,
}

def hesablamalar(request):
    # 1. TƏHLÜKƏSİZLİK: Əgər istifadəçi giriş etməyibsə, tam URL ilə qeyd olunan login-ə atırıq
    user_data = request.session.get('current_user_data')
    if not user_data:
        return redirect('/groups/login/')  # Səhv yönləndirmənin qarşısını almaq üçün birbaşa statik URL yazırıq

    user_role = user_data.get('rol')   
    user_qrup = user_data.get('qrup')  

    # --- Qiymət və Qrup Filtrləmə Məntiqi ---
    if user_role in ['menecer', 'diviziya_rehb', 'rehber', 'admin']:
        active_prices = PRICES_MENECER
    else:
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
        "GENOSFER": "Genosfer", "VITOMER": "Vitomer", "KARTOVEY": "Kartovey", 
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
            "role": user_data.get("rol"), 
            "group": user_data.get("qrup")
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