from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from payment.models import Payment_doctor, Sale
from medicine.models import Medical
from regions.models import Region, Hospital, City
from doctors.models import Doctors, RecipeDrug, Recipe
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, date 
import pandas as pd
import re
from difflib import SequenceMatcher
import subprocess
import os


from .models import Backup

@csrf_exempt
def create_backup(request):
    if request.method == 'POST':
        db_name = settings.DATABASES['default']['NAME']
        db_user = settings.DATABASES['default']['USER']
        db_password = settings.DATABASES['default']['PASSWORD']
        db_host = settings.DATABASES['default']['HOST'] or 'localhost'
        db_port = settings.DATABASES['default']['PORT'] or '5432'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        filename = f'solvey_backup_{timestamp}.sql'
        backup_file = os.path.join(backup_dir, filename)

        # pg_dump path-i müəyyən et (Linux və Windows üçün)
        import platform
        if platform.system() == 'Windows':
            # Windows üçün PostgreSQL default path
            pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'
            if not os.path.exists(pg_dump_path):
                # Alternativ path-ləri yoxla
                for version in ['17', '16', '15', '14', '13', '12']:
                    alt_path = rf'C:\Program Files\PostgreSQL\{version}\bin\pg_dump.exe'
                    if os.path.exists(alt_path):
                        pg_dump_path = alt_path
                        break
        else:
            # Linux üçün: pg_dump birbaşa PATH-dadır
            pg_dump_path = 'pg_dump'

        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        try:
            # stderr-i capture et ki, real xəta mesajını görək
            result = subprocess.run([
                pg_dump_path,
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-f', backup_file,
                db_name
            ], check=True, env=env, capture_output=True, text=True)

            # Fayl ölçüsü (MB)
            size_bytes = os.path.getsize(backup_file)
            size_mb = size_bytes / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"

            backup_obj = Backup.objects.create(
                ad=f'Solvey Backup {timestamp}',
                fayl=f'backups/{filename}',
                olcu=size_str
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Backup uğurla yaradıldı.',
                'filename': filename,
                'file_url': backup_obj.fayl.url,
                'size': size_str
            })

        except subprocess.CalledProcessError as e:
            error_msg = f"pg_dump xətası: {e}"
            if e.stderr:
                error_msg += f"\nXəta detalları: {e.stderr}"
            if e.stdout:
                error_msg += f"\nÇıxış: {e.stdout}"
            return JsonResponse({
                'status': 'error', 
                'message': error_msg,
                'details': {
                    'returncode': e.returncode,
                    'stderr': e.stderr,
                    'stdout': e.stdout,
                    'db_host': db_host,
                    'db_port': db_port,
                    'db_user': db_user,
                    'db_name': db_name,
                    'pg_dump_path': pg_dump_path
                }
            }, status=500)
        except FileNotFoundError:
            return JsonResponse({
                'status': 'error', 
                'message': f'pg_dump komandası tapılmadı. Path: {pg_dump_path}',
                'suggestion': 'PostgreSQL client tools quraşdırıldığından əmin olun.'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Gözlənilməz xəta: {str(e)}'
            }, status=500)

    return JsonResponse({'status': 'error', 'message': 'Yalnız POST tələbi qəbul edilir.'}, status=405)

@csrf_exempt
def restore_backup(request, backup_id):
    """
    Backup faylından verilənlər bazasını bərpa edir.
    """
    if request.method == 'POST':
        try:
            # Bərpa ediləcək backup-ı tap
            backup = Backup.objects.get(id=backup_id)
            backup_file = os.path.join(settings.MEDIA_ROOT, str(backup.fayl))

            if not os.path.exists(backup_file):
                return JsonResponse({'status': 'error', 'message': 'Backup faylı tapılmadı.'}, status=404)

            # Verilənlər bazası məlumatlarını götür
            db_name = settings.DATABASES['default']['NAME']
            db_user = settings.DATABASES['default']['USER']
            db_password = settings.DATABASES['default']['PASSWORD']
            db_host = settings.DATABASES['default']['HOST']
            db_port = settings.DATABASES['default']['PORT']

            # PostgreSQL komanda alətləri
            psql_path = r'C:\Program Files\PostgreSQL\17\bin\psql.exe'

            # Ətraf mühit üçün parol təyin et
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password

            # Əvvəlcə bazanı təmizləmək istəsən (opsional)
            # subprocess.run([psql_path, '-h', db_host, '-p', str(db_port), '-U', db_user, '-d', db_name, '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'], check=True, env=env)

            # Backup faylından bərpa et
            subprocess.run([
                psql_path,
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-f', backup_file
            ], check=True, env=env)

            return JsonResponse({'status': 'success', 'message': f'Backup bərpası uğurla tamamlandı: {backup.ad}'})

        except Backup.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Backup tapılmadı.'}, status=404)
        except subprocess.CalledProcessError as e:
            return JsonResponse({'status': 'error', 'message': f'Bərpa zamanı xəta baş verdi: {e}'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Yalnız POST tələbi qəbul edilir.'}, status=405)


def yeni_istifadeci_elave_et(request):
    if request.method == "POST":
        email = request.POST.get("email")
        ad = request.POST.get("ad")
        parol = request.POST.get("parol")

        # Email artıq mövcuddursa xəbərdarlıq
        if User.objects.filter(username=email).exists():
            messages.error(request, "Bu email ilə artıq istifadəçi mövcuddur!")
            return redirect("yeni_istifadeci")

        # İstifadəçi yarat
        user = User.objects.create_user(
            username=email,   # username kimi email istifadə olunur
            email=email,
            password=parol,
            first_name=ad
        )
        user.save()

        messages.success(request, "İstifadəçi uğurla əlavə edildi ✅")
        return redirect("admin")

    return render(request, "admin.html")

def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.delete()
    return redirect("admin")

def admin_view(request):
    backups = Backup.objects.all().order_by('-olusturulma_tarixi')
    recipes = RecipeDrug.objects.all().order_by("-created_at", "-id")[:30]
    bolgeler = Region.objects.all
    users = User.objects.all
    current_month = datetime.now().month
    current_year = datetime.now().year
    aylar = [
        ("Yanvar", 1), ("Fevral", 2), ("Mart", 3), ("Aprel", 4),
        ("May", 5), ("İyun", 6), ("İyul", 7), ("Avqust", 8),
        ("Sentyabr", 9), ("Oktyabr", 10), ("Noyabr", 11), ("Dekabr", 12)
    ]
    years_list = [current_year - i for i in range(0, 3)]
        



    context ={
        "backups" :backups,
        "bolgeler" :bolgeler,
        "aylar": aylar,
        "current_month": current_month,
        "years_list": years_list,
        "users": users,
        "recipes" : recipes
    }
    
    return render(request, "admin.html", context)


def borc_sifirla(request):
    if request.method == "POST":
        region_id = request.POST.get("region_id")
        if not region_id:
            messages.error(request, "Zəhmət olmasa bölgə seçin!")
            return redirect("admin_view")  # Əsas səhifə və ya admin panel URL

        count = Doctors.objects.filter(bolge_id=region_id).update(previous_debt=0)
        messages.success(request, f"Seçilən bölgədə {count} həkimin əvvəlki borcu sıfırlandı.")
        return redirect("admin")

    return redirect("admin")


def imports(request):
 
    
    return render(request, "export.html")

def import_drug_from_excel(request):
    if request.method == "POST":
        excel_drug_file = request.FILES.get("excel_drug_file")
        if not excel_drug_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("drugs")

        try:
            df = pd.read_excel(excel_drug_file, header=0)
            df.columns = df.columns.str.strip().str.lower()
            
            # Lazımi sütunların olub olmadığını yoxla
            required_columns = ["dərman adı", "dərman qiyməti", "dərman komissiyası"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messages.error(request, f"Bu sütunlar tapılmadı: {missing_columns}. Mövcud sütunlar: {df.columns.tolist()}")
                return redirect("drugs")

            # Ədədi sütunları təmizlə və çevir
            df["dərman qiyməti"] = df["dərman qiyməti"].astype(str).str.replace(",", ".").astype(float)
            df["dərman komissiyası"] = df["dərman komissiyası"].astype(str).str.replace(",", ".").astype(float)
            
            # Dərman tam adı sütunu üçün yoxla (opsional)
            has_full_name = "dərman tam adı" in df.columns

            added_count = 0
            skipped_count = 0

            for _, row in df.iterrows():
                name = str(row.get("dərman adı", "")).strip()
                if not name:
                    skipped_count += 1
                    continue
                
                # Dərman tam adını əlavə et (əgər varsa)
                full_name = str(row.get("dərman tam adı", "")).strip() if has_full_name else ""
                
                price = row["dərman qiyməti"]
                commission = row["dərman komissiyası"]

                # Eyni adlı dərmanın olub olmadığını yoxla
                if Medical.objects.filter(med_name=name).exists():
                    skipped_count += 1
                    continue

                Medical.objects.create(
                    med_name=name,
                    med_full_name=full_name if full_name else None,
                    med_price=price,
                    komissiya=commission,
                    status=True  # Default status
                )
                added_count += 1

            messages.success(request, f"{added_count} dərman uğurla əlavə olundu. {skipped_count} dərman atlandı (boş ad və ya təkrarlanan).")
        
        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")
            # Daha ətraflı xəta mesajı üçün
            import traceback
            error_details = traceback.format_exc()
            print(f"Xəta detalları: {error_details}")

        return redirect("drugs")

    return render(request, "admin.html")



def import_region_from_excel(request):
    if request.method == "POST":
        excel_region_file = request.FILES.get("excel_region_file")
        if not excel_region_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")  # Düzgün URL adı

        try:
            df = pd.read_excel(excel_region_file, header=0)  # Başlıq sətri düzəltdik
            messages.info(request, f"Sütunlar: {list(df.columns)}")  # DEBUG üçün

            region_col = None
            for col in df.columns:
                if col.strip().lower() == "bölgə":
                    region_col = col
                    break

            if not region_col:
                messages.error(request, "'Bölgə' sütunu tapılmadı.")
                return redirect("admin")

            added_count = 0
            for _, row in df.iterrows():
                name = str(row.get(region_col, "")).strip()
                if not name:
                    continue

                if not Region.objects.filter(region_name__iexact=name).exists():
                    Region.objects.create(region_name=name)
                    added_count += 1

            messages.success(request, f"{added_count} bölgə uğurla əlavə olundu.")
        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("region_list")

    return render(request, "admin.html")


def import_doctor_city_from_excel(request):
    """
    Həkimlərə şəhər təyin etmək üçün Excel importu.
    Format: Bölgə, Həkim, Şəhər.
    Şəhər boşdursa həkimin şəhəri boş qalır. Şəhər yoxdursa yaradılır.
    """
    if request.method != "POST":
        return redirect("admin")

    excel_file = request.FILES.get("excel_city_file")
    if not excel_file:
        messages.error(request, "Fayl seçilməyib.")
        return redirect("admin")

    try:
        df = pd.read_excel(excel_file, header=0)
        cols = [str(c).strip() for c in df.columns]
        df.columns = cols

        def _norm(s):
            s = str(s).strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c").replace("ğ", "g")
            return s

        region_col = None
        doctor_col = None
        city_col = None
        for col in cols:
            c = _norm(col)
            if "bolg" in c or "bölg" in c or c == "bolge":
                region_col = col
            elif "hekim" in c or "həkim" in c:
                doctor_col = col
            elif "seher" in c or "şəhər" in c or "sheher" in c or c == "city":
                city_col = col

        if not region_col or not doctor_col or not city_col:
            if len(cols) >= 3:
                region_col = cols[0]
                doctor_col = cols[1]
                city_col = cols[2]
            else:
                messages.error(request, f"Sütunlar tapılmadı. Mövcud: {cols}")
                return redirect("admin")

        valid_city_names = [ch[1] for ch in City.CITY_CHOICES]
        updated_count = 0
        created_cities = 0
        not_found_doctors = set()

        for _, row in df.iterrows():
            region_name = str(row.get(region_col, "")).strip()
            doctor_name = str(row.get(doctor_col, "")).strip()
            city_name_raw = str(row.get(city_col, "")).strip()

            if not region_name or not doctor_name:
                continue

            doctor = Doctors.objects.filter(
                bolge__region_name__icontains=region_name,
                ad__iexact=doctor_name
            ).select_related("bolge").first()

            if not doctor:
                doctor = Doctors.objects.filter(
                    bolge__region_name__icontains=region_name,
                    ad__icontains=doctor_name
                ).select_related("bolge").first()

            if not doctor:
                not_found_doctors.add(f"{region_name} / {doctor_name}")
                continue

            if not city_name_raw or city_name_raw.lower() == "nan":
                doctor.city = None
                doctor.save()
                updated_count += 1
                continue

            matched_city = None
            for valid in valid_city_names:
                if valid.lower() == city_name_raw.lower():
                    matched_city = valid
                    break
                if SequenceMatcher(None, city_name_raw.lower(), valid.lower()).ratio() >= 0.9:
                    matched_city = valid
                    break

            if not matched_city:
                matched_city = city_name_raw

            city_obj, created = City.objects.get_or_create(
                region=doctor.bolge,
                city_name=matched_city
            )
            if created:
                created_cities += 1

            doctor.city = city_obj
            doctor.save()
            updated_count += 1

        messages.success(request, f"{updated_count} həkimə şəhər təyin edildi.")
        if created_cities:
            messages.info(request, f"{created_cities} yeni şəhər yaradıldı.")
        if not_found_doctors:
            messages.warning(request, f"Tapılmayan həkimlər: {', '.join(sorted(not_found_doctors)[:5])}{'...' if len(not_found_doctors) > 5 else ''}")
    except Exception as e:
        messages.error(request, f"Xəta: {str(e)}")

    return redirect("admin")


def import_hospital_from_excel(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_hospital_file")
        if not excel_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")

        try:
            df = pd.read_excel(excel_file, header=0)
            messages.info(request, f"Sütunlar: {list(df.columns)}")

            region_col = None
            hospital_col = None
            for col in df.columns:
                if col.strip().lower() == "bölgə":
                    region_col = col
                elif col.strip().lower() == "xəstəxana":
                    hospital_col = col

            if not region_col or not hospital_col:
                messages.error(request, "'Bölgə' və ya 'Xəstəxana' sütunu tapılmadı.")
                return redirect("admin")

            seen = set()
            added_count = 0

            for _, row in df.iterrows():
                region_name = str(row.get(region_col, "")).strip()
                hospital_name = str(row.get(hospital_col, "")).strip()

                if not region_name or not hospital_name:
                    continue

                key = (region_name.lower(), hospital_name.lower())
                if key in seen:
                    continue
                seen.add(key)

                region_obj, _ = Region.objects.get_or_create(region_name__iexact=region_name, defaults={"region_name": region_name})

                # Əvvəlki eyni hospital varsa, sil
                Hospital.objects.filter(hospital_name__iexact=hospital_name, region_net=region_obj).delete()

                # Yeni hospital əlavə et
                Hospital.objects.create(hospital_name=hospital_name, region_net=region_obj)
                added_count += 1

            messages.success(request, f"{added_count} xəstəxana uğurla əlavə olundu (təkrarlar silinərək).")
        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")
        return redirect("hospital_list")

    return render(request, "admin.html")




def import_doctors_from_excel(request):
    if request.method == "POST" and request.FILES.get("excel_doctor_file"):
        file = request.FILES["excel_doctor_file"]
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip().str.lower()  # sütun adlarını normalize elə

            for index, row in df.iterrows():
                bolge_adi = str(row.get("bölgə", "")).strip()
                hekim_adi = str(row.get("həkim", "")).strip()
                derece = str(row.get("dərəcə", "")).strip()
                telefon = row.get("telefon")
                telefon = str(telefon).strip() if pd.notna(telefon) else ""  # "None" stringi düşməsin
                klinika_adi = str(row.get("klinika", "")).strip()
                ixtisas = str(row.get("ixtisas", "")).strip().upper()

                if not bolge_adi or not hekim_adi:
                    continue  # boş dəyərləri atla

                # Bölgəni tap və ya yarat
                bolge_obj, _ = Region.objects.get_or_create(region_name=bolge_adi)

                # Klinikayı tap və ya yarat (bölgə ilə birlikdə)
                klinika_obj = None
                if klinika_adi:
                    klinika_obj, _ = Hospital.objects.get_or_create(
                        hospital_name=klinika_adi,
                        region_net=bolge_obj
                    )

                # Həkimi yarad (barkod avtomatik modeldə generate olunacaq)
                Doctors.objects.create(
                    ad=hekim_adi,
                    ixtisas=ixtisas,
                    derece=derece,
                    number=telefon,
                    bolge=bolge_obj,
                    klinika=klinika_obj
                )

            messages.success(request, "Həkimlər uğurla import edildi.")
        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {e}")

        return redirect("admin")

    return redirect("admin")



def import_debts_from_excel(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_debt_file")
        if not excel_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")

        try:
            df = pd.read_excel(excel_file, header=0)
            updated_count = 0
            not_found = []

            # Excel-də olan bütün bölgələri topla
            excel_regions = df["Bölgə"].dropna().astype(str).str.strip().unique()

            # Hər bölgənin həkimlərini yoxlayıb borcu güncəllə
            for region_name in excel_regions:
                # Sistemdə bu bölgənin həkimləri
                doctors_in_region = Doctors.objects.filter(bolge__region_name__iexact=region_name)

                # Excel-də bu bölgənin həkim adları və borcları
                excel_data_in_region = df[df["Bölgə"].astype(str).str.strip() == region_name][["Həkim", "Əvvəlki Borc"]]

                # Excel-də olan həkimləri yenilə
                excel_doctors_names = []
                for _, row in excel_data_in_region.iterrows():
                    ad = str(row["Həkim"]).strip()
                    borc = row["Əvvəlki Borc"]
                    excel_doctors_names.append(ad)

                    doctor = doctors_in_region.filter(ad__iexact=ad).first()
                    if doctor:
                        doctor.previous_debt = float(borc) if pd.notna(borc) else 0.0
                        doctor.save()
                        updated_count += 1
                    else:
                        # Excel-də həkim var amma sistemdə yox → yeni həkim yaratmırıq
                        not_found.append(f"{region_name} - {ad}")

                # Excel-də olmayan həkimlərin borcunu sıfırla (yalnız həmin bölgədə)
                for doctor in doctors_in_region:
                    if doctor.ad not in excel_doctors_names:
                        doctor.previous_debt = 0.0
                        doctor.save()

            messages.success(request, f"{updated_count} həkimin borcu yeniləndi.")
            if not_found:
                messages.warning(request, f"Tapılmayan həkimlər: {', '.join(not_found)}")

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("admin")

    return render(request, "admin.html")



def import_avn_inv_from_excel(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_finance_file")
        selected_date = request.POST.get("selected_date")
        
        if not excel_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")
            
        if not selected_date:
            messages.error(request, "Tarix seçilməyib.")
            return redirect("admin")

        try:
            import_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            df = pd.read_excel(excel_file, header=0)

            created_count = 0
            not_found = []

            for _, row in df.iterrows():
                ad = str(row.get('ad', '')).strip()
                bolge = str(row.get('bolge', '')).strip()  # 🔹 Fayldan bölgəni oxuyuruq
                avans = row.get('avans', 0)
                investisiya = row.get('invest', 0)

                if not ad or not bolge:
                    continue

                # 🔹 Həm ad, həm də bölgəyə görə həkimi tapırıq
                doctor = Doctors.objects.filter(ad__iexact=ad, bolge__iexact=bolge).first()

                if not doctor:
                    not_found.append(f"{ad} ({bolge})")
                    continue

                # Region məlumatını doctor modelindən alırıq
                region = doctor.bolge

                # Avans ödənişi yarat
                if avans and float(avans) != 0:
                    Payment_doctor.objects.create(
                        area=region,
                        doctor=doctor,
                        payment_type='Avans',
                        pay=avans,
                        date=import_date
                    )
                    created_count += 1

                # İnvest ödənişi yarat
                if investisiya and float(investisiya) != 0:
                    Payment_doctor.objects.create(
                        area=region,
                        doctor=doctor,
                        payment_type='İnvest',
                        pay=investisiya,
                        date=import_date
                    )
                    created_count += 1

            messages.success(request, f"{created_count} ödəniş qeydi {import_date} tarixinə əlavə edildi.")
            if not_found:
                messages.warning(request, f"Tapılmayan həkimlər: {', '.join(not_found)}")

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("admin")

    return render(request, "admin.html")


def import_recipes_from_excel(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_recipe_file")
        selected_date = request.POST.get("selected_date")
        
        if not excel_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")
            
        if not selected_date:
            messages.error(request, "Tarix seçilməyib.")
            return redirect("admin")

        try:
            # DÜZƏLİŞ: datetime.strptime yerine düzgün istifadə
            import_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            
            df = pd.read_excel(excel_file)
            added_count = 0
            not_found_doctors = set()
            not_found_regions = set()
            not_found_drugs = set()

            # Dərmanları əvvəlcədən bazadan çək və sadələşdirilmiş formada dictionary qur
            med_map = {}
            for med in Medical.objects.all():
                ad = med.med_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                med_map.setdefault(ad, []).append(med)

            for _, row in df.iterrows():
                hekim_adi = str(row.get("Həkim", "")).strip()
                bolge_adi = str(row.get("Bölgə", "")).strip()

                if not hekim_adi or hekim_adi == ".":
                    continue

                try:
                    region = Region.objects.get(region_name__iexact=bolge_adi)
                except Region.DoesNotExist:
                    not_found_regions.add(bolge_adi)
                    continue

                doctors = Doctors.objects.filter(ad__iexact=hekim_adi, bolge=region)
                if not doctors.exists():
                    not_found_doctors.add(f"{hekim_adi} ({bolge_adi})")
                    continue

                for doctor in doctors:
                    # Yeni: Seçilmiş tarixi istifadə et
                    recipe = Recipe.objects.create(region=region, dr=doctor, date=import_date)

                    for drug_name in df.columns[2:]:
                        try:
                            say_str = str(row[drug_name]).replace(",", ".").strip()
                            say = float(say_str)
                        except Exception:
                            say = 0

                        if say <= 0:
                            continue

                        drug_key = drug_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")

                        meds = med_map.get(drug_key)
                        if not meds:
                            not_found_drugs.add(drug_name.strip())
                            continue

                        for med in meds:
                            RecipeDrug.objects.create(recipe=recipe, drug=med, number=say)

                    added_count += 1

            messages.success(request, f"{added_count} resept {import_date} tarixinə uğurla əlavə olundu.")
            if not_found_regions:
                messages.warning(request, f"Tapılmayan bölgələr: {', '.join(sorted(not_found_regions))}")
            if not_found_doctors:
                messages.warning(request, f"Tapılmayan həkimlər: {', '.join(sorted(not_found_doctors))}")
            if not_found_drugs:
                messages.warning(request, f"Tapılmayan dərmanlar: {', '.join(sorted(not_found_drugs))}")

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("admin")

    return render(request, "admin.html")


def import_sales_from_excel(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_sale_file")
        selected_date = request.POST.get("selected_date")
        
        if not excel_file:
            messages.error(request, "Fayl seçilməyib.")
            return redirect("admin")
            
        if not selected_date:
            messages.error(request, "Tarix seçilməyib.")
            return redirect("admin")

        try:
            # Tarixi düzgün formatda al
            import_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            
            df = pd.read_excel(excel_file)
            added_count = 0
            not_found_regions = set()
            not_found_drugs = set()

            # Bölgələri və dərmanları əvvəlcədən bazadan çək
            region_map = {}
            for region in Region.objects.all():
                region_name = region.region_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                region_map[region_name] = region

            drug_map = {}
            for drug in Medical.objects.all():
                drug_name = drug.med_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                drug_map[drug_name] = drug

            # Excel sütunlarını emal et (birinci sütun O/T/NAIR 2025, son sütun TOTAL)
            for _, row in df.iterrows():
                # İlk sütun - dərman adı
                drug_name = str(row.iloc[0]).strip()
                
                if not drug_name or drug_name == "nan" or drug_name == "TOTAL":
                    continue

                # Dərmanı tap
                drug_key = drug_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                
                if drug_key not in drug_map:
                    not_found_drugs.add(drug_name)
                    continue

                drug = drug_map[drug_key]

                # Bölgələr üzrə satış məlumatlarını emal et
                for i in range(1, len(df.columns) - 1):  # Birinci sütun dərman adı, son sütun TOTAL
                    region_name = df.columns[i]
                    region_name_clean = region_name.strip().lower().replace("ı", "i").replace("ə", "e").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                    
                    # Bölgəni tap
                    if region_name_clean not in region_map:
                        not_found_regions.add(region_name)
                        continue

                    region = region_map[region_name_clean]

                    # Satış miqdarını al
                    try:
                        quantity_str = str(row.iloc[i]).replace(",", ".").strip()
                        quantity = int(float(quantity_str)) if quantity_str and quantity_str != "nan" else 0
                    except (ValueError, TypeError):
                        quantity = 0

                    # Satış məlumatını yadda saxla
                    if quantity > 0:
                        Sale.objects.create(
                            region=region,
                            drug=drug,
                            quantity=quantity,
                            sale_date=import_date
                        )
                        added_count += 1

            messages.success(request, f"{added_count} satış məlumatı {import_date} tarixinə uğurla əlavə olundu.")
            if not_found_regions:
                messages.warning(request, f"Tapılmayan bölgələr: {', '.join(sorted(not_found_regions))}")
            if not_found_drugs:
                messages.warning(request, f"Tapılmayan dərmanlar: {', '.join(sorted(not_found_drugs))}")

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("admin")

    return render(request, "admin.html")


def _normalize_region_for_match(name):
    """Bölgə adını müqayisə üçün: bölgə, -Salyan çıxar; Şamaxı↔ŞAMAXI."""
    s = str(name).strip().lower()
    for suffix in [" bölgə", " bölge", "-salyan"]:
        if s.endswith(suffix):
            s = s[:-len(suffix)].strip()
    return s.replace("ı", "i")  # Şamaxı ↔ ŞAMAXI


def _normalize_drug_for_match(name):
    """Dərman adını müqayisə üçün: D3 çıxar; görünməyən simvolları sil."""
    s = str(name).strip().lower().replace("\xa0", " ")
    s = "".join(c for c in s if c.isprintable() or c.isspace()).strip()
    if s.endswith(" d3"):
        s = s[:-3].strip()
    return s


def _normalize_baku_region_for_match(name):
    """Bakı bölgə adı: 2 Bölgə↔Bakı bölgə-2, Zabrat↔Zabrat."""
    s = str(name).strip().lower().replace("ı", "i").replace("ö", "o").replace("ə", "e")
    m = re.search(r"bolge-?\s*(\d+)", s)
    if m:
        return f"bolge{m.group(1)}"
    m = re.search(r"(\d+)\s*bolge", s)
    if m:
        return f"bolge{m.group(1)}"
    return s.replace(" ", "").replace("-", "")


def import_baku_sales_from_excel(request):
    """
    Bakı Satış Excel importu.
    Format: Bölgə sütunu + dərman sütunları (Sobseda, Opsidol, ...) + Aylıq satış.
    Sətirlərdə: 2 Bölgə, 6 Bölgə, Zabrat, Pirallahı və s.
    """
    if request.method != "POST":
        return redirect("admin")

    excel_file = request.FILES.get("excel_baku_sales")
    selected_date = request.POST.get("baku_sales_date")

    if not excel_file:
        messages.error(request, "Fayl seçilməyib.")
        return redirect("admin")
    if not selected_date:
        messages.error(request, "Tarix seçilməyib.")
        return redirect("admin")

    try:
        import_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        df = pd.read_excel(excel_file)

        baku_regions = list(Region.objects.filter(region_type="Bakı"))
        drug_list = list(Medical.objects.all())

        added_count = 0
        added_total_qty = 0
        not_matched_regions = set()
        not_matched_drugs = set()

        cols = list(df.columns)
        region_col_idx = 0
        for i, c in enumerate(cols):
            if "bölg" in str(c).lower() or str(c).strip().lower() == "bolge":
                region_col_idx = i
                break

        drug_col_indices = []
        for i in range(len(cols)):
            if i == region_col_idx:
                continue
            c = str(cols[i]).strip().lower()
            if "aylıq" in c or "total" in c or c == "cem" or c == "cəm":
                continue
            drug_col_indices.append((i, cols[i]))

        for _, row in df.iterrows():
            region_name_raw = str(row.iloc[region_col_idx]).strip()
            if not region_name_raw or region_name_raw == "nan" or region_name_raw.upper() in ("CƏM", "CEM", "YANVAR", "FƏRQ", "TOTAL"):
                continue

            matched_region = None
            excel_norm = _normalize_baku_region_for_match(region_name_raw)
            best_r = 0.84
            for r in baku_regions:
                sys_norm = _normalize_baku_region_for_match(r.region_name)
                if excel_norm == sys_norm:
                    matched_region = r
                    break
                ratio = SequenceMatcher(None, excel_norm, sys_norm).ratio()
                if ratio >= 0.85 and ratio > best_r:
                    best_r = ratio
                    matched_region = r

            if not matched_region:
                not_matched_regions.add(region_name_raw)
                continue

            for col_idx, drug_name_raw in drug_col_indices:
                drug_name_str = str(drug_name_raw).strip()
                if not drug_name_str or drug_name_str == "nan":
                    continue

                matched_drug = None
                excel_drug_norm = _normalize_drug_for_match(drug_name_str)
                best_ratio = 0.89
                for d in drug_list:
                    sys_drug_norm = _normalize_drug_for_match(d.med_name)
                    if excel_drug_norm == sys_drug_norm:
                        matched_drug = d
                        break
                    if (excel_drug_norm.startswith(sys_drug_norm) or sys_drug_norm.startswith(excel_drug_norm)) and len(sys_drug_norm) >= 4:
                        matched_drug = d
                        break
                    ratio = SequenceMatcher(None, excel_drug_norm, sys_drug_norm).ratio()
                    if ratio >= 0.85 and ratio > best_ratio:
                        best_ratio = ratio
                        matched_drug = d

                if not matched_drug:
                    not_matched_drugs.add(drug_name_str)
                    continue

                try:
                    val = row.iloc[col_idx]
                    q_str = str(val).replace(",", ".").strip()
                    q = int(float(q_str)) if q_str and q_str != "nan" else 0
                    quantity = max(0, q)
                except (ValueError, TypeError):
                    quantity = 0

                if quantity > 0:
                    Sale.objects.create(
                        region=matched_region,
                        drug=matched_drug,
                        quantity=quantity,
                        sale_date=import_date
                    )
                    added_count += 1
                    added_total_qty += quantity

        messages.success(request, f"{added_count} satış məlumatı (cəmi {added_total_qty} ədəd) {import_date} tarixinə əlavə olundu.")
        if not_matched_regions:
            messages.warning(request, f"Uyğunlaşmayan bölgələr: {', '.join(sorted(not_matched_regions))}")
        if not_matched_drugs:
            messages.warning(request, f"Uyğunlaşmayan dərmanlar: {', '.join(sorted(not_matched_drugs))}")

    except Exception as e:
        messages.error(request, f"Xəta: {str(e)}")

    return redirect("admin")


def import_region_sales_from_excel(request):
    """
    Region Satış Excel importu.
    Format: fevral2026 | Dərmanlar | ŞAMAXI | ŞƏKİ | ... | TOTAL
    - Bölgə: 90% oxşarlıq (Gəncə bölgə↔GƏNCƏ, Şirvan-Salyan↔ŞİRVAN)
    - Dərman: 95% oxşarlıq (Vitomer D3↔Vitomer, Levastronq↔Levostrong)
    - Mənfi ədədlər → 0
    """
    if request.method != "POST":
        return redirect("admin")

    excel_file = request.FILES.get("excel_region_sales")
    selected_date = request.POST.get("region_sales_date")

    if not excel_file:
        messages.error(request, "Fayl seçilməyib.")
        return redirect("admin")

    if not selected_date:
        messages.error(request, "Tarix seçilməyib.")
        return redirect("admin")

    try:
        import_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        df = pd.read_excel(excel_file)

        region_list = list(Region.objects.all())
        drug_list = list(Medical.objects.all())

        added_count = 0
        added_total_qty = 0
        not_matched_regions = set()
        not_matched_drugs = set()

        # Dərman sütununun indeksini tap
        cols = list(df.columns)
        drug_col_idx = 1
        for i, c in enumerate(cols):
            c_str = str(c).strip().lower()
            if "dərman" in c_str or c_str == "dermanlar":
                drug_col_idx = i
                break

        # Region sütunları
        region_col_indices = []
        for i in range(drug_col_idx + 1, len(cols)):
            col_name = str(cols[i]).strip().upper()
            if col_name == "TOTAL" or "total" in col_name.lower():
                break
            region_col_indices.append((i, cols[i]))

        for _, row in df.iterrows():
            drug_name_raw = str(row.iloc[drug_col_idx]).strip()
            if not drug_name_raw or drug_name_raw == "nan" or drug_name_raw.upper() == "TOTAL":
                continue

            # Dərman uyğunlaşdırma: 95% oxşarlıq + "Vitomer D3" → "Vitomer" (startswith)
            matched_drug = None
            best_ratio = 0.89
            excel_drug_norm = _normalize_drug_for_match(drug_name_raw)

            for d in drug_list:
                sys_drug_norm = _normalize_drug_for_match(d.med_name)
                if excel_drug_norm == sys_drug_norm:
                    matched_drug = d
                    break
                if excel_drug_norm.startswith(sys_drug_norm) or sys_drug_norm.startswith(excel_drug_norm):
                    if len(sys_drug_norm) >= 4:
                        matched_drug = d
                        break
                ratio = SequenceMatcher(None, excel_drug_norm, sys_drug_norm).ratio()
                if ratio >= 0.85 and ratio > best_ratio:
                    best_ratio = ratio
                    matched_drug = d

            if not matched_drug:
                not_matched_drugs.add(drug_name_raw)
                continue

            for col_idx, region_name_raw in region_col_indices:
                region_name_str = str(region_name_raw).strip()
                if not region_name_str or region_name_str.upper() == "TOTAL":
                    continue

                # Bölgə uyğunlaşdırma: 90% oxşarlıq + Gəncə bölgə↔GƏNCƏ, Şirvan-Salyan↔ŞİRVAN
                matched_region = None
                best_r = 0.84
                excel_region_norm = _normalize_region_for_match(region_name_str)

                for r in region_list:
                    sys_region_norm = _normalize_region_for_match(r.region_name)
                    if excel_region_norm == sys_region_norm:
                        matched_region = r
                        break
                    ratio = SequenceMatcher(None, excel_region_norm, sys_region_norm).ratio()
                    if ratio >= 0.85 and ratio > best_r:
                        best_r = ratio
                        matched_region = r

                if not matched_region:
                    not_matched_regions.add(region_name_str)
                    continue

                try:
                    val = row.iloc[col_idx]
                    q_str = str(val).replace(",", ".").strip()
                    q = int(float(q_str)) if q_str and q_str != "nan" else 0
                    quantity = max(0, q)
                except (ValueError, TypeError):
                    quantity = 0

                if quantity > 0:
                    Sale.objects.create(
                        region=matched_region,
                        drug=matched_drug,
                        quantity=quantity,
                        sale_date=import_date
                    )
                    added_count += 1
                    added_total_qty += quantity

        messages.success(request, f"{added_count} satış məlumatı (cəmi {added_total_qty} ədəd) {import_date} tarixinə əlavə olundu.")
        if not_matched_regions:
            messages.warning(request, f"Uyğunlaşmayan bölgələr: {', '.join(sorted(not_matched_regions))}")
        if not_matched_drugs:
            messages.warning(request, f"Uyğunlaşmayan dərmanlar: {', '.join(sorted(not_matched_drugs))}")

    except Exception as e:
        messages.error(request, f"Xəta: {str(e)}")

    return redirect("admin")


def admin_recipes_delete(request, id):
    recipe = get_object_or_404(RecipeDrug, id=id)
    recipe.delete()
    return redirect("admin")