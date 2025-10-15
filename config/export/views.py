from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from payment.models import Payment_doctor
from medicine.models import Medical
from regions.models import Region, Hospital
from doctors.models import Doctors, RecipeDrug, Recipe
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, date 
import pandas as pd
import subprocess
import os


from .models import Backup
@csrf_exempt
def create_backup(request):
    if request.method == 'POST':
        db_name = settings.DATABASES['default']['NAME']
        db_user = settings.DATABASES['default']['USER']
        db_password = settings.DATABASES['default']['PASSWORD']
        db_host = settings.DATABASES['default']['HOST']
        db_port = settings.DATABASES['default']['PORT']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        filename = f'solvey_backup_{timestamp}.sql'
        backup_file = os.path.join(backup_dir, filename)

        pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        try:
            subprocess.run([
                pg_dump_path,
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-f', backup_file,
                db_name
            ], check=True, env=env)

            # Fayl ölçüsünü hesablamaq
            size_bytes = os.path.getsize(backup_file)
            size_mb = size_bytes / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"

            # Modelə qeyd et
            backup_obj = Backup.objects.create(
                ad='Solvey Backup',
                fayl=f'backups/{filename}',
                olcu=size_str
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Backup uğurla yaradıldı.',
                'filename': backup_obj.ad,
                'file_url': backup_obj.fayl.url,
                'size': backup_obj.olcu
            })

        except subprocess.CalledProcessError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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
                ixtisas = str(row.get("ixtisas", "")).strip()

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
            return redirect("import_debts")

        try:
            df = pd.read_excel(excel_file, header=0)
            updated_count = 0
            not_found = []

            for _, row in df.iterrows():
                ad = str(row.get('ad', '')).strip()
                borc = row.get('Əvvəlki Borc', 0)

                if not ad:
                    continue

                # Həkimi adına görə tap
                doctors = Doctors.objects.filter(ad__iexact=ad)

                if not doctors.exists():
                    not_found.append(f"{ad}")
                    continue

                for doctor in doctors:
                    doctor.previous_debt = borc  # Əvəzləyir, += yazsan üzərinə gələcək
                    doctor.save()
                    updated_count += 1

            messages.success(request, f"{updated_count} həkimin borcu yeniləndi.")
            if not_found:
                messages.warning(request, f"Tapılmayan həkimlər: {', '.join(not_found)}")

        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {str(e)}")

        return redirect("doctors")

    return render(request, "import_excel.html")




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
            # Seçilmiş tarixi datetime obyektinə çevir
            import_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            
            df = pd.read_excel(excel_file, header=0)
            created_count = 0
            not_found = []

            for _, row in df.iterrows():
                ad = str(row.get('ad', '')).strip()
                avans = row.get('avans', 0)
                investisiya = row.get('invest', 0)

                if not ad:
                    continue

                doctors = Doctors.objects.filter(ad__iexact=ad)

                if not doctors.exists():
                    not_found.append(ad)
                    continue

                for doctor in doctors:
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
                    
                    # Investisiya ödənişi yarat
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

                    for drug_name in df.columns[3:]:
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


def admin_recipes_delete(request, id):
    recipe = get_object_or_404(RecipeDrug, id=id)
    recipe.delete()
    return redirect("admin")