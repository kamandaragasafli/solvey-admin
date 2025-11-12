from django.shortcuts import render, redirect, get_object_or_404
from .models import Doctors, RecipeDrug, Recipe, RealSales, RealSalesDrug
from medicine.models import Medical
from django.contrib import messages
from regions.models import Region , Hospital, City
from payment.models import Payment_doctor, Sale, MonthlyDoctorReport
from django.http import JsonResponse
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
import openpyxl
from decimal import Decimal
from django.core.paginator import Paginator
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from openpyxl import Workbook
from django.db.models import Sum , Q
from django.utils import timezone
from collections import defaultdict
from datetime import datetime
from core.models import DeletedRecipeDrugLog 
from django.contrib.auth.models import User 
from decimal import Decimal, ROUND_HALF_UP
from regions.models import Region, Hospital, City
from django.db import transaction, IntegrityError
from django.db.models import Max
import urllib.parse
from datetime import date, timedelta
from django.core.paginator import Paginator


def doctors_list(request):
    regions = Region.objects.all()
    queryset = Doctors.objects.all().prefetch_related('odenisler')

    # Region filter
    region_id = request.GET.get('region_filter')
    if region_id:
        queryset = queryset.filter(bolge_id=region_id)

    # Debt filter
    debt_filter = request.GET.get('debt_filter')
    if debt_filter == 'greater':
        queryset = queryset.filter(previous_debt__gt=0)
    elif debt_filter == 'zero':
        queryset = queryset.filter(previous_debt=0)
    elif debt_filter == 'less':
        queryset = queryset.filter(previous_debt__lt=100)

    # Search filter
    search_query = request.GET.get('search')
    if search_query:
        queryset = queryset.filter(ad__icontains=search_query)

    # Prepare data with last payment info
    doctor_data = []
    for doctor in queryset:
        last_payment = doctor.odenisler.order_by('-date').first()
        doctor_data.append({
            "doctor": doctor,
            "last_payment_date": last_payment.date if last_payment else None,
            "last_payment_amount": last_payment.pay if last_payment else 0
        })

    # Pagination ləğv edildi
    return render(request, "doctors.html", {"doctors": doctor_data, "regions": regions})


def create_doctor(request):
    regions = Region.objects.all()
    hospitals = Hospital.objects.all()
    cities = City.objects.all()  
    
    if request.method == "POST":
        ad = request.POST.get("ad")
        ixtisas = request.POST.get("ixtisas")
        kategoriya = request.POST.get("kategoriya")
        derece = request.POST.get("derece")
        cinsiyyet = request.POST.get("cinsiyyet")
        bolge_id = request.POST.get("bolge_id")    
        city_id = request.POST.get("city_id")  # yeni əlavə etdik
        klinika_id = request.POST.get("klinika_id")
        number = request.POST.get("number")

        if not all([ad, ixtisas, kategoriya, bolge_id, klinika_id]):
            messages.error(request, "Zəhmət olmasa bütün vacib sahələri doldurun.")
            return redirect("add-doctor")

        bolge = get_object_or_404(Region, id=bolge_id)
        klinika = get_object_or_404(Hospital, id=klinika_id)
        city = City.objects.filter(id=city_id).first() if city_id else None


        
        doctor = Doctors.objects.create(
            ad=ad,
            ixtisas=ixtisas,
            kategoriya=kategoriya,
            derece=derece or 'II',
            cinsiyyet=cinsiyyet or 'Kişi',
            bolge=bolge,
            city=city,
            klinika=klinika,
            number=number,

        )


        messages.success(request, "Həkim uğurla əlavə edildi.")
        return redirect("doctor_detail", doctor_id=doctor.id)

    context = {
        "regions": regions,
        "hospitals": hospitals,
        "cities": cities,
    }
    return render(request, "crud/add-doctor.html", context)


def get_hospitals_by_region(request):
    region_id = request.GET.get("region_id")
    hospitals = Hospital.objects.filter(region_net_id=region_id).values("id", "hospital_name")
    return JsonResponse({"hospitals": list(hospitals)})

def get_cities_by_region(request):
    region_id = request.GET.get("region_id")
    cities = City.objects.filter(region_id=region_id)

    city_list = [
        {
            "id": city.id,
            "city_name": city.get_city_name_display()  # Model metodunu burada çağıra bilərsən
        }
        for city in cities
    ]

    return JsonResponse({"cities": city_list})




def del_all(request):
    Doctors.objects.all().delete()
    messages.success(request, "Bütün həkimlər uğurla silindi.")
    return redirect("doctors")  # Silindikdən sonra uyğun səhifəyə yönləndir


def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctors, id=doctor_id)
    
    # Doğru model: Payment_doctor
    payments = Payment_doctor.objects.filter(doctor=doctor).order_by("-date")[:10]
    recipe = RecipeDrug.objects.filter(recipe__dr=doctor).select_related('recipe', 'drug', 'recipe__region')


    # Əgər resept modeli varsa
    recibe_total = RecipeDrug.objects.filter(recipe__dr=doctor).aggregate(total=Sum('number'))['total'] or 0


    monthly_reports = MonthlyDoctorReport.objects.filter(doctor=doctor).order_by('-report_month')
    silinme_list = []
    for report in monthly_reports:
        silinme_list.append({
            "month": report.report_month.strftime("%B %Y"),  
            "hekimden_silinen": report.hekimden_silinen
        })



    context = {
        "doctor": doctor,
        "payments": payments,
        "recibe_total": recibe_total,
        "recipe": recipe,
        "silinme_list": silinme_list,
    }
    return render(request, "doctor-details.html", context)

def ajax_doctors_by_region(request):
    region_id = request.GET.get('region_id')
    if region_id:
        doctors = Doctors.objects.filter(bolge=region_id).values('id', 'ad')
        doctors_list = list(doctors)
        return JsonResponse({'doctors': doctors_list})
    else:
        return JsonResponse({'doctors': []})




def icaze_var(il, ay, region_id):
    from datetime import date
    cari_tarix = date.today()
    cari_il = cari_tarix.year
    cari_ay = cari_tarix.month

    hesabat_baglidir = MonthlyDoctorReport.objects.filter(
        report_month__year=il,
        report_month__month=ay,
        region_id=region_id
    ).exists()

    # Əlavə şərt: cari ay üçün hesabat hələ açılmayıb, 
    # amma keçən ay bağlıdırsa → cari aya icazə ver
    if (il, ay) == (cari_il, cari_ay) and not hesabat_baglidir:
        kecen_ay = cari_ay - 1
        kecen_il = cari_il
        if kecen_ay == 0:
            kecen_ay = 12
            kecen_il -= 1

        kecen_ay_baglidir = MonthlyDoctorReport.objects.filter(
            report_month__year=kecen_il,
            report_month__month=kecen_ay,
            region_id=region_id
        ).exists()

        if kecen_ay_baglidir:
            return True  

    if hesabat_baglidir:
        return (il, ay) >= (cari_il, cari_ay)
    else:
        return (il, ay) < (cari_il, cari_ay)


from .utils import fix_recipe_drug_sequence 

def create_recipe(request):
    regions = Region.objects.all().order_by("region_name")
    drugs = Medical.objects.all().order_by('id')
    last_recipes = RecipeDrug.objects.all().order_by("-created_at", "-id")[:5]

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
            doctors = Doctors.objects.filter(bolge_id=region_id) if region_id else Doctors.objects.none()
            return render(request, "crud/add-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        ay = istifade_olunacaq_tarix.month
        il = istifade_olunacaq_tarix.year

        # İcazəni yoxla
        if not icaze_var(il, ay, region_id):
            messages.error(request, f"{istifade_olunacaq_tarix.strftime('%Y-%m')} ayı üçün əlavə etməyə icazə yoxdur.")
            doctors = Doctors.objects.filter(bolge_id=region_id) if region_id else Doctors.objects.none()
            return render(request, "crud/add-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        # Həkimləri göstər
        doctors = Doctors.objects.filter(bolge_id=region_id) if region_id else Doctors.objects.none()

        # Region və həkim yoxdursa
        if not (region_id and doctor_id):
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "crud/add-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        # Recipe yarat - SEQUENCE PROBLEMİNƏ QARŞI QORUMA İLƏ
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with transaction.atomic():
                    # Recipe yarat
                    recipe = Recipe.objects.create(
                        region_id=region_id,
                        dr_id=doctor_id,
                        date=istifade_olunacaq_tarix
                    )
                    doctor = Doctors.objects.get(id=doctor_id)

                    # Əlavə olunan dərmanlar
                    for key in request.POST:
                        if key.startswith("quantity_"):
                            drug_id = key.split("_")[1]
                            count = request.POST.get(key)
                            if count and float(count) > 0:
                                RecipeDrug.objects.create(
                                    recipe=recipe,
                                    drug_id=drug_id,
                                    number=count
                                )

                    messages.success(request, f"{doctor.ad} həkimə resept {selected_date} tarixi ilə əlavə olundu.")
                    break  # Uğurlu oldu, döngüdən çıx

            except IntegrityError as e:
                retry_count += 1
                if 'duplicate key' in str(e) and 'doctors_recipedrug_pkey' in str(e):
                    # Sequence problemi - sıfırla və yenidən cəhd et
                    if retry_count < max_retries:
                        fix_recipe_drug_sequence()  # ← İndi utils-dən gəlir
                        continue
                    else:
                        messages.error(request, "Texniki xəta. Zəhmət olmasa bir neçə dəqiqədən sonra yenidən cəhd edin.")
                        return redirect('create_recipe')
                else:
                    # Digər IntegrityError
                    messages.error(request, f"Verilənlər bazası xətası: {str(e)}")
                    return redirect('create_recipe')
                    
            except Exception as e:
                messages.error(request, f"Gözlənilməz xəta: {str(e)}")
                return redirect('create_recipe')

    else:
        doctors = Doctors.objects.none()

    return render(request, "crud/add-recipe.html", {
        "regions": regions,
        "doctors": doctors,
        "last_recipes": last_recipes,
        "drugs": drugs,
        "selected_region": selected_region,
        "selected_doctor": selected_doctor,
        "selected_date": selected_date
    })



def create_detail_recipe(request):
    regions = Region.objects.all().order_by("region_name")
    drugs = Medical.objects.all().order_by("med_full_name")

    selected_region = ""
    selected_doctor = None
    selected_date = ""

    # GET sorğusundan doctor_id al
    doctor_id = request.GET.get("doctor_id")
    if doctor_id:
        try:
            selected_doctor = Doctors.objects.get(id=doctor_id)
            selected_region = selected_doctor.bolge.id
        except Doctors.DoesNotExist:
            selected_doctor = None

    if request.method == "POST":
        region_id = request.POST.get("region", "")
        doctor_id = request.POST.get("doctor", "")
        date = request.POST.get("date", "")

        selected_region = region_id
        selected_doctor = Doctors.objects.get(id=doctor_id) if doctor_id else None
        selected_date = date

        # Regiona görə həkimləri filtre et
        if selected_region:
            doctors = Doctors.objects.filter(bolge_id=selected_region).order_by("ad")
        else:
            doctors = Doctors.objects.none()

        if not (region_id and doctor_id and date):
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "crud/add-details-recipe.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        # Recipe yarat
        recipe = Recipe.objects.create(
            region_id=region_id,
            dr_id=doctor_id,
            date=date
        )
        doctor = Doctors.objects.get(id=doctor_id)

        # Əlavə olunan dərmanları qeyd et
        for key in request.POST:
            if key.startswith("quantity_"):
                drug_id = key.split("_")[1]
                count = request.POST.get(key)
                if count and int(count) > 0:
                    RecipeDrug.objects.create(
                        recipe=recipe,
                        drug_id=drug_id,
                        number=count
                    )

        messages.success(request, f"{doctor.ad} həkimə resept uğurla əlavə olundu.")

    else:
        # GET zamanı regiona görə həkimləri seçilmiş həkim varsa filtre et
        if selected_region:
            doctors = Doctors.objects.filter(bolge_id=selected_region).order_by("ad")
        else:
            doctors = Doctors.objects.none()

    return render(request, "crud/add-details-recipe.html", {
        "regions": regions,
        "doctors": doctors,
        "drugs": drugs,
        "selected_region": selected_region,
        "selected_doctor": selected_doctor,
        "selected_date": selected_date
    })



def del_recipe(request, id):
    rm_recipe = get_object_or_404(RecipeDrug, id=id)
    
    # Silinmə əməliyyatını loglamaq
    DeletedRecipeDrugLog.objects.create(
        drug_name=rm_recipe.drug,
        recipe_id=rm_recipe.recipe.id,
        deleted_by=request.user if request.user.is_authenticated else None,
    )
    
    # Həkimin ID-sini al
    doctor_id = rm_recipe.recipe.dr.id
    
    # Resepti sil
    rm_recipe.delete()
    
    # Həkimin detallarına yönləndir
    return redirect('doctor_detail', doctor_id=doctor_id)


def del_payments(request, id):
    payment = get_object_or_404(Payment_doctor, id=id)
    doctor_id = payment.doctor.id
    payment.delete()
    return redirect('doctor_detail', doctor_id=doctor_id)




def update_recipe(request, id):
    # RecipeDrug obyektini götür
    recipe_drug = get_object_or_404(RecipeDrug, id=id)

    if request.method == "POST":
        number = request.POST.get("number")
        if number:
            recipe_drug.number = number
            recipe_drug.save()
            messages.success(request, "Resept uğurla yeniləndi.")
            # Update sonra həkimin detal səhifəsinə yönləndir
            return redirect("doctor_detail", doctor_id=recipe_drug.recipe.dr.id)
        else:
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")

    context = {
        "recipe_drug": recipe_drug
    }
    return render(request, "doctor_details.html", context)



def load_cities_hospitals(request):
    region_id = request.GET.get('region_id')
    if not region_id or not region_id.isdigit():
        return JsonResponse({'cities': [], 'hospitals': []})

    cities = list(City.objects.filter(region_id=region_id).values('id', 'city_name'))
    hospitals = list(Hospital.objects.filter(region_net_id=region_id).values('id', 'hospital_name'))
    return JsonResponse({'cities': cities, 'hospitals': hospitals})




def update_doctor(request, pk):
    doctor = get_object_or_404(Doctors, pk=pk)
    if request.method == "POST":
        doctor.ad = request.POST.get('ad', doctor.ad)
        doctor.ixtisas = request.POST.get('ixtisas', doctor.ixtisas)
        doctor.kategoriya = request.POST.get('kategoriya', doctor.kategoriya)
        doctor.cinsiyyet = request.POST.get('cinsiyyet', doctor.cinsiyyet)
        doctor.derece = request.POST.get('derece', doctor.derece)
        doctor.number = request.POST.get('number', doctor.number)
        doctor.save()
        return redirect('doctor_detail', doctor_id=doctor.pk)  # Changed 'pk' to 'doctor_id'
    return render(request, 'doctor-details.html', {'doctor': doctor})


def create_real_sales(request):
    regions = Region.objects.all().order_by("region_name")
    doctors = Doctors.objects.all().order_by("ad")
    drugs = Medical.objects.all().order_by('id')

    selected_region = None
    selected_doctor = None
    selected_date = None

    if request.method == "POST":
        region_id = request.POST.get("region")
        doctor_id = request.POST.get("doctor")
        date = request.POST.get("date")

        selected_region = region_id
        selected_doctor = doctor_id
        selected_date = date

        if not (region_id and doctor_id and date):
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "crud/add-real-sales.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        # Dərmanların olub-olmadığını yoxlayaq
        selected_drugs = []
        for key in request.POST:
            if key.startswith("quantity_"):
                drug_id = key.split("_")[1]
                count = request.POST.get(key)
                if count and int(count) > 0:
                    selected_drugs.append((int(drug_id), int(count)))

        if not selected_drugs:
            messages.error(request, "Zəhmət olmasa ən az bir dərman miqdarı daxil edin.")
            return render(request, "crud/add-real-sales.html", {
                "regions": regions,
                "doctors": doctors,
                "drugs": drugs,
                "selected_region": selected_region,
                "selected_doctor": selected_doctor,
                "selected_date": selected_date
            })

        # Real satış yaradılır
        real_sale = RealSales.objects.create(
            region_n_id=region_id,
            dr_name_id=doctor_id,
            date_sale=date
        )
        
        total_commission = Decimal('0')

        for drug_id, count in selected_drugs:
            RealSalesDrug.objects.create(
                real_sale=real_sale,
                drug_name_id=drug_id,
                numbers=count
            )



            # Bölgə satışını azaldırıq
            sale_qs = Sale.objects.filter(region_id=region_id, drug_id=drug_id).first()
            if sale_qs:
                sale_qs.quantity = max(0, sale_qs.quantity - count)
                sale_qs.save()

            # Həkimin reseptini azaldırıq
            recipe_drugs = RecipeDrug.objects.filter(recipe__region_id=region_id, recipe__dr_id=doctor_id, drug_id=drug_id)
            for rd in recipe_drugs:
                rd.number = max(0, rd.number - count)
                rd.save()

            # Komissiyanı hesabla
            drug = Medical.objects.get(id=drug_id)
            komissiya = drug.komissiya * count
            total_commission += komissiya

        # Həkimin yekun borcunu artırırıq
        doctor = Doctors.objects.get(id=doctor_id)
        doctor.hekimden_silinen += total_commission
        doctor.save()

        messages.success(request, "Satış uğurla əlavə olundu və komissiya borca əlavə edildi.")
        return redirect("create_real_sales")

    return render(request, "crud/add-real-sales.html", {
        "regions": regions,
        "doctors": doctors,
        "drugs": drugs,
        "selected_region": selected_region,
        "selected_doctor": selected_doctor,
        "selected_date": selected_date
    })

def create_datasiya(request):
    regions = Region.objects.all().order_by("region_name")
    selected_region = request.GET.get("region") or None

    doctors = Doctors.objects.filter(region_id=selected_region).order_by("ad") if selected_region else []

    if request.method == "POST":
        region_id = request.POST.get("region")
        date = request.POST.get("date")

        if not region_id or not date:
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "crud/add-datasiya.html", {
                "regions": regions,
                "doctors": doctors,
                "selected_region": region_id,
                "selected_date": date,
            })

        # Həkimlərin borcunu yenilə
        for key, value in request.POST.items():
            if key.startswith("given_") or key.startswith("received_"):
                parts = key.split("_")
                prefix = parts[0]
                doctor_id = parts[1]

                if value.strip() == "":
                    continue
                try:
                    amount = Decimal(value)
                except ValueError:
                    amount = 0

                if amount == 0:
                    continue

                try:
                    doctor = Doctors.objects.get(id=doctor_id)
                except Doctors.DoesNotExist:
                    continue

                if prefix == "given":
                    doctor.datasiya += amount
                elif prefix == "received":
                    doctor.datasiya -= amount

                doctor.save()

        messages.success(request, "Datasiya uğurla əlavə etdiniz.")
        return redirect("datasiya")

    return render(request, "crud/add-datasiya.html", {
        "regions": regions,
        "doctors": doctors,
        "selected_region": selected_region,
    })

def finance_view(request):
    regions = Region.objects.all().order_by("region_name")
    selected_region = request.GET.get("region")

    doctors = []

    # Cari ay və il
    today = date.today()
    current_month = today.month
    current_year = today.year

    if selected_region:
        doctors = Doctors.objects.filter(region_id=selected_region).order_by("ad")

        for doctor in doctors:
            # Bu ay üçün Avans və İnvestisiya cəmlərini tapırıq
            payments = Payment_doctor.objects.filter(
                doctor=doctor,
                area_id=selected_region,
                date__month=current_month,
                date__year=current_year
            ).values("payment_type").annotate(total=Sum("pay"))

            # Varsayılan 0 dəyərlər
            doctor.avans = Decimal("0.00")
            doctor.investisiya = Decimal("0.00")

            for p in payments:
                if p["payment_type"] == "Avans":
                    doctor.avans = p["total"] or Decimal("0.00")
                elif p["payment_type"] == "İnvest":
                    doctor.investisiya = p["total"] or Decimal("0.00")
            
            # BURADA BORC HESABLANMASINI ƏLAVƏ EDİN
            # Məsələn:
            doctor.previous_debt = Decimal("0.00")  # Öz borc hesablama məntiqinizə uyğun

    return render(request, "finance.html", {
        "regions": regions,
        "doctors": doctors,
        "selected_region": selected_region,
    })


def create_razilasma(request):
    regions = Region.objects.all().order_by("region_name")
    selected_region = request.GET.get("region") or None
    doctors = Doctors.objects.filter(region_id=selected_region).order_by("ad") if selected_region else []

    if request.method == "POST":
        region_id = request.POST.get("region")
        date = request.POST.get("date")

        if not region_id or not date:
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return render(request, "crud/add-razılaşma.html", {
                "regions": regions,
                "doctors": doctors,
                "selected_region": region_id,
                "selected_date": date,
            })

        # Həkimlərin razılaşma sayını yenilə
        for key, value in request.POST.items():
            if key.startswith("razilasma_"):
                doctor_id = key.split("_")[1]
                if value.strip() == "":
                    continue

                try:
                    count = int(value)
                except ValueError:
                    count = 0

                if count == 0:
                    continue

                try:
                    doctor = Doctors.objects.get(id=doctor_id)
                except Doctors.DoesNotExist:
                    continue

                # Burada həkimin razılaşma sayını saxlayırsan
                doctor.razılaşma += count  
                doctor.save()

        messages.success(request, "Razılaşma uğurla əlavə edildi.")
        return redirect("razilasma")

    return render(request, "crud/add-razılaşma.html", {
        "regions": regions,
        "doctors": doctors,
        "selected_region": selected_region,
    })


def ajax_doctors_by_region(request):
    region_id = request.GET.get('region_id')
    
    if not region_id:
        return JsonResponse({'doctors': []})
    
    # Cari ay və il
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # Həkimləri və onların ödəniş məlumatlarını al
    doctors = Doctors.objects.filter(bolge=region_id)
    
    doctor_list = []
    
    for doctor in doctors:
        # Bu həkim üçün cari ayın Avans və İnvestisiya məlumatlarını hesabla
        payments = Payment_doctor.objects.filter(
            doctor=doctor,
            area_id=region_id,
            date__month=current_month,
            date__year=current_year
        ).values('payment_type').annotate(total=Sum('pay'))
        
        # Default dəyərlər
        avans = Decimal('0.00')
        investisiya = Decimal('0.00')
        
        # Ödəniş növlərinə görə cəmlə
        for payment in payments:
            if payment['payment_type'] == 'Avans':
                avans = payment['total'] or Decimal('0.00')
            elif payment['payment_type'] == 'İnvest':
                investisiya = payment['total'] or Decimal('0.00')
        
        doctor_list.append({
            'id': doctor.id,
            'ad': doctor.ad,
            'previous_debt': float(doctor.previous_debt) if doctor.previous_debt else 0.0,
            'avans': float(avans),
            'investisiya': float(investisiya)
        })
    
    return JsonResponse({'doctors': doctor_list})

def data_list(request):
    region = Region.objects.all()
    drug = Medical.objects.all().order_by('id')

    context = {
        "region": region,
        "drug": drug
    }
    return render(request, "data-list.html", context)

def ajax_region_data(request):
    region_id = request.GET.get("region_id")
    date_range = request.GET.get("date_range")
    name_filter = request.GET.get("name_filter")
    month = request.GET.get("month")
    page = request.GET.get("page", 1)
    per_page = 30

    try:
        region_id = int(region_id)
    except (TypeError, ValueError):
        return JsonResponse({"results": []})

    # Əsas queryset
    doctors = Doctors.objects.filter(bolge=region_id)

    # Name filter
    if name_filter == 'with_dannisi':
        doctors = doctors.filter(
            Q(ad__icontains='dannı') | Q(ad__icontains='dannisi') | Q(ad__icontains='dannısı')
        )
    elif name_filter == 'without_dannisi':
        doctors = doctors.exclude(
            Q(ad__icontains='dannı') | Q(ad__icontains='dannisi') | Q(ad__icontains='dannısı')
        )

    # Tarix aralığı və ay filteri
    month_start = month_end = None
    dr_start = dr_end = None

    if month:
        try:
            month_int = int(month)
            current_year = datetime.now().year
            month_start = datetime(current_year, month_int, 1).date()
            if month_int == 12:
                month_end = datetime(current_year + 1, 1, 1).date()
            else:
                month_end = datetime(current_year, month_int + 1, 1).date()
        except ValueError:
            pass

    if date_range and " - " in date_range:
        try:
            start_str, end_str = date_range.split(" - ")
            dr_start = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
            dr_end = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass

    # Final start_date və end_date
    if month_start and month_end and dr_start and dr_end:
        start_date = max(month_start, dr_start)
        end_date = min(month_end, dr_end)
    elif month_start and month_end:
        start_date = month_start
        end_date = month_end
    elif dr_start and dr_end:
        start_date = dr_start
        end_date = dr_end
    else:
        start_date = end_date = None

    result = []
    all_medical_drugs = Medical.objects.all().order_by('id')

    for doctor in doctors:
        # RecipeDrug queryset
        all_drugs = RecipeDrug.objects.filter(recipe__dr=doctor, recipe__region=region_id)

        if start_date and end_date:
            all_drugs = all_drugs.filter(recipe__date__gte=start_date, recipe__date__lte=end_date)

        # Hər dərman üzrə cəmi say
        drugs_agg = all_drugs.values('drug__med_name').annotate(total_count=Sum('number'))

        drugs = []
        total = 0
        for med_drug in all_medical_drugs:
            found_drug = next((d for d in drugs_agg if d['drug__med_name'] == med_drug.med_name), None)
            count = found_drug['total_count'] if found_drug else 0
            drugs.append({"name": med_drug.med_name, "count": count})
            total += count

        # Filter: without_dannisi və total=0
        if name_filter == "without_dannisi" and total == 0:
            continue

        # Son ödəniş
        last_payment = doctor.odenisler.order_by('-date').first()

        if last_payment:
            odeme_type = last_payment.payment_type.lower()  # kiçik hərflərə çevir
            if odeme_type == "avans":
                odeme_class = "text-primary"  # göy
            elif odeme_type == "investisiya":
                odeme_class = "text-warning"  # sarı
            elif odeme_type == "geriqaytarma":
                odeme_class = "text-danger"   # qırmızı
            else:
                odeme_class = "text-success"  # yaşıl

            odeme_amount = float(last_payment.pay)
            odeme_date = last_payment.date.strftime('%Y-%m-%d')
            odeme_type_json = last_payment.payment_type.lower()
        else:
            odeme_class = "text-success"  # heçnə yoxdursa yaşıl
            odeme_amount = 0
            odeme_date = None
            odeme_type_json = ""

        # JSON olaraq göndər
        odeme = {
            "amount": odeme_amount,
            "type": odeme_type_json,
            "class": odeme_class,
            "date": odeme_date
        }


        result.append({
            "bolge": doctor.bolge.region_name,
            "doctor": doctor.ad,
            "doctor_id": doctor.id,
            "barcode": doctor.barkod,
            "odeme": odeme,
            "borc": float(doctor.borc),
            "drugs": drugs,
            "total": float(total)
        })

    # Pagination
    paginator = Paginator(result, per_page)
    try:
        current_page = paginator.page(page)
        paginated_results = list(current_page.object_list)
    except:
        current_page = paginator.page(1)
        paginated_results = list(current_page.object_list)

    return JsonResponse({
        "results": paginated_results,
        "total_pages": paginator.num_pages,
        "current_page": current_page.number,
        "has_previous": current_page.has_previous(),
        "has_next": current_page.has_next(),
        "total_results": len(result)
    })

def export_region_excel(request):
    region_id = request.GET.get('region_id')
    date_range = request.GET.get("date_range")
    name_filter = request.GET.get('name_filter')
    search_term = request.GET.get("search")
    month = request.GET.get("month")

    if not region_id:
        return HttpResponse("Bölgə seçilməyib.", status=400)

    try:
        region = Region.objects.get(id=region_id)
    except Region.DoesNotExist:
        return HttpResponse("Bölgə tapılmadı.", status=404)

    # Əsas queryset
    doctors = (
        Doctors.objects
        .filter(bolge=region)
        .select_related('bolge')
        .prefetch_related('odenisler')
    )

    # 🔹 Axtarış filteri
    if search_term:
        doctors = doctors.filter(
            Q(ad__icontains=search_term) |
            Q(barkod__icontains=search_term)
        )

    # 🔹 Dannisi filteri
    if name_filter == 'with_dannisi':
        doctors = doctors.filter(Q(ad__icontains='dannısı') | Q(ad__icontains='dannisi'))
    elif name_filter == 'without_dannisi':
        doctors = doctors.exclude(Q(ad__icontains='dannısı') | Q(ad__icontains='dannisi'))

    # 🔹 Tarix intervalı
    start_date = end_date = None
    if date_range:
        try:
            if "to" in date_range:
                start_str, end_str = date_range.split("to")
                start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
            elif " - " in date_range:
                start_str, end_str = date_range.split(" - ")
                start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass

    drugs = list(Medical.objects.all().order_by('id'))

    recipe_filter = Q(recipe__region=region)
    if start_date and end_date:
        recipe_filter &= Q(recipe__date__range=(start_date, end_date))
    elif month:
        recipe_filter &= Q(recipe__date__month=month)

    counts_qs = (
        RecipeDrug.objects
        .filter(recipe_filter)
        .values('recipe__dr_id', 'drug_id')
        .annotate(total=Sum('number'))
    )

    doctor_drug_counts = defaultdict(dict)
    doctor_total_counts = defaultdict(int)

    for row in counts_qs:
        dr_id = row['recipe__dr_id']
        drug_id = row['drug_id']
        total = row['total'] or 0
        doctor_drug_counts[dr_id][drug_id] = total
        doctor_total_counts[dr_id] += total

    # 📊 Excel yaradılması
    wb = Workbook()
    ws = wb.active
    ws.title = f"{region.region_name} - Filterli"

    headers = ["№", "Bölgə", "Həkim adı", "Kod", "Son Ödəniş"] + [d.med_name for d in drugs] + ["Total"]
    ws.append(headers)

    bold_font = Font(bold=True, color="060411")
    header_fill = PatternFill(fill_type="solid", fgColor="F0F0F0")
    thin = Side(style='thin', color="000000")
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center_align = Alignment(horizontal="center", vertical="bottom")

    for cell in ws[1]:
        cell.font = bold_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center", textRotation=90)

    ws.freeze_panes = "A2"

    idx = 1
    for doctor in doctors:
        total = doctor_total_counts.get(doctor.id, 0)
        last_payment = doctor.odenisler.order_by('-date').first()

        if last_payment:
            odeme = f"₼{float(last_payment.pay):.2f} - {last_payment.date.strftime('%Y-%m-%d')}"
        elif doctor.geriqaytarma > 0:
            odeme = f"₼{float(doctor.geriqaytarma):.2f}"
        elif doctor.investisiya > 0:
            odeme = f"₼{float(doctor.investisiya):.2f}"
        elif doctor.avans > 0:
            odeme = f"₼{float(doctor.avans):.2f}"
        else:
            odeme = "-"

        row = [
            idx,
            doctor.bolge.region_name,
            doctor.ad,
            doctor.barkod,
            odeme,
        ]

        counts_map = doctor_drug_counts.get(doctor.id, {})
        for drug in drugs:
            row.append(counts_map.get(drug.id, 0))
        row.append(total)

        ws.append(row)
        idx += 1

    # 📈 Cəmlər
    start_drug_col = 6
    total_col_idx = len(headers)

    drug_totals = [0] * (total_col_idx - start_drug_col)
    overall_total = 0

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=start_drug_col, max_col=total_col_idx):
        
        for i, cell in enumerate(row[:-1]):
            try:
                drug_totals[i] += int(cell.value or 0)
            except:
                pass
        try:
            overall_total += int(row[-1].value or 0)
        except:
            pass

    total_row_idx = ws.max_row + 1
    ws.cell(row=total_row_idx, column=1, value="Cəmi")
    for i, total in enumerate(drug_totals):
      
        ws.cell(row=total_row_idx, column=start_drug_col + i, value=total)
    ws.cell(row=total_row_idx, column=total_col_idx, value=overall_total)

    for cell in ws[total_row_idx]:
        cell.border = thin_border
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{region.region_name} Qeydiyyatı.xlsx"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    wb.save(response)
    return response

def get_region(request):
    
    reg = Region.objects.all()
    context = {
        "reg": reg
    }
    return render(request, "test.html", context)


# Borcalacaq Hesablama
from django.db.models import Max

def region_report(request, region_id):
    # Dərmanlar və həkimlər
    dermanlar = Medical.objects.all().order_by('-id')
    hekimler = Doctors.objects.filter(bolge_id=region_id).order_by('ad')

    # Reseptlər və satışlar (region üzrə)
    region_recipe_drugs = RecipeDrug.objects.filter(recipe__region_id=region_id)
    sales = Sale.objects.filter(region_id=region_id)

    # Ay seçimi
    month = request.GET.get("month")
    if month:
        try:
            ay = int(month)
        except ValueError:
            ay = None
    else:
        # Ən son satış ayı
        last_sale_date = sales.aggregate(last_date=Max('sale_date'))['last_date']
        ay = last_sale_date.month if last_sale_date else None

    if ay:
        region_recipe_drugs = region_recipe_drugs.filter(recipe__date__month=ay)
        sales = sales.filter(sale_date__month=ay)

    # Dərəcə faktorları
    dereceler = {"VIP": 1.00, "I": 0.90, "II": 0.65, "III": 0.40}

    report_data = []
    for hekim in hekimler:
        faktor = dereceler.get(hekim.derece, 0)
        hekim_sira = {'hekim': hekim, 'dermanlar': [], 'faizli_dermanlar': [], 'toplam': 0, 'faizli_toplam': Decimal('0.00')}
        for derman in dermanlar:
            toplam = region_recipe_drugs.filter(recipe__dr=hekim, drug=derman).aggregate(total=Sum('number'))['total'] or 0
            faizli = (Decimal(toplam) * Decimal(faktor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            hekim_sira['dermanlar'].append(toplam)
            hekim_sira['faizli_dermanlar'].append(faizli)
            hekim_sira['toplam'] += toplam
            hekim_sira['faizli_toplam'] += faizli
        report_data.append(hekim_sira)

    # Dərmanların toplamları
    derman_toplamlari = []
    faizli_derman_toplamlari = []
    for i, derman in enumerate(dermanlar):
        toplam = region_recipe_drugs.filter(drug=derman).aggregate(total=Sum('number'))['total'] or 0
        derman_toplamlari.append(toplam)
        toplam_faizli = sum(row['faizli_dermanlar'][i] for row in report_data)
        faizli_derman_toplamlari.append(round(toplam_faizli, 2))

    toplam_hekim_say = sum(row['toplam'] for row in report_data)
    toplam_faizli_say = round(sum(row['faizli_toplam'] for row in report_data), 2)

    # Effektivlik faizləri
    effektivlik_faizleri = []
    for i, derman in enumerate(dermanlar):
        satis_sayi = sales.filter(drug=derman).aggregate(s=Sum('quantity'))['s'] or 0
        faizli_resept = faizli_derman_toplamlari[i]
        effektivlik = (Decimal(satis_sayi) / Decimal(faizli_resept)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if faizli_resept > 0 else Decimal('0.00')
        effektivlik_faizleri.append(effektivlik)

    # Effektivlikli dərmanlar və komissiya
    for row in report_data:
        row['effektivlikli_dermanlar'] = []
        row['effektivlikli_toplam'] = Decimal('0.00')
        for i, faizli in enumerate(row['faizli_dermanlar']):
            effektiv = effektivlik_faizleri[i]
            vurulmus = (faizli * effektiv).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            row['effektivlikli_dermanlar'].append(vurulmus)
            row['effektivlikli_toplam'] += vurulmus

    for row in report_data:
        row['komissiya_miqdarlari'] = []
        row['umumi_komissiya'] = Decimal('0.00')
        for i, effektiv in enumerate(row['effektivlikli_dermanlar']):
            komissiya_faizi = dermanlar[i].komissiya or Decimal('0')
            miqdar = (effektiv * komissiya_faizi).quantize(Decimal('0.01'))
            row['komissiya_miqdarlari'].append(miqdar)
            row['umumi_komissiya'] += miqdar
        # Həkim modelinə yaz
        hekim = row['hekim']
        hekim.hesablanan_miqdar = row['effektivlikli_toplam']
        hekim.hekimden_silinen = row['umumi_komissiya']
        hekim.save()
        row['hekim_effektiv_komissiya'] = list(zip(row['effektivlikli_dermanlar'], row['komissiya_miqdarlari']))

    effektivlikli_derman_toplamlari = [round(sum(row['effektivlikli_dermanlar'][i] for row in report_data), 2) for i in range(len(dermanlar))]
    toplam_effektivlikli_say = round(sum(effektivlikli_derman_toplamlari), 2)
    toplam_komissiya = sum(row['umumi_komissiya'] for row in report_data).quantize(Decimal('0.01'))
    komissiya_toplamlari = [sum(row['komissiya_miqdarlari'][i] for row in report_data).quantize(Decimal('0.01')) for i in range(len(dermanlar))]

    region = get_object_or_404(Region, id=region_id)

    context = {
        'dermanlar': dermanlar,
        'hekimler_data': report_data,
        'derman_toplamlari': derman_toplamlari,
        'faizli_derman_toplamlari': faizli_derman_toplamlari,
        'effektivlik_faizleri': effektivlik_faizleri,
        'effektivlikli_derman_toplamlari': effektivlikli_derman_toplamlari,
        'toplam_effektivlikli_say': toplam_effektivlikli_say,
        'komissiya_toplamlari': komissiya_toplamlari,
        'toplam_hekim_say': toplam_hekim_say,
        'toplam_faizli_say': toplam_faizli_say,
        'toplam_komissiya': toplam_komissiya,
        'region': region,
        'ay': ay,
        'aylar': range(1, 13),
    }

    return render(request, 'test_2.html', context)




# def region_report(request, region_id):
#     dermanlar = Medical.objects.all().order_by('med_name')
#     hekimler = Doctors.objects.filter(bolge_id=region_id).order_by('ad')
#     region_recipe_drugs = RecipeDrug.objects.filter(recipe__region_id=region_id)

#     dereceler = {
#         "VİP": 1.00,
#         "I": 0.90,
#         "II": 0.65,
#         "III": 0.40,
#     }

#     report_data = []
#     for hekim in hekimler:
#         derece = hekim.derece
#         faktor = dereceler.get(derece, 0)

#         hekim_sira = {
#             'hekim': hekim,
#             'dermanlar': [],
#             'faizli_dermanlar': [],
#             'toplam': 0,
#             'faizli_toplam': 0,
#         }

#         for derman in dermanlar:
#             toplam = region_recipe_drugs.filter(recipe__dr=hekim, drug=derman).aggregate(
#                 total=Sum('number')
#             )['total'] or 0

#             faizli = (Decimal(str(toplam)) * Decimal(str(faktor))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#             hekim_sira['dermanlar'].append(toplam)
#             hekim_sira['faizli_dermanlar'].append(faizli)

#             hekim_sira['toplam'] += toplam
#             hekim_sira['faizli_toplam'] += faizli

#         report_data.append(hekim_sira)

#     # Dərmanların toplamı (sütunlar üzrə)
#     derman_toplamlari = []
#     faizli_derman_toplamlari = []
#     for index, derman in enumerate(dermanlar):
#         toplam = region_recipe_drugs.filter(drug=derman).aggregate(total=Sum('number'))['total'] or 0
#         derman_toplamlari.append(toplam)

#         toplam_faizli = sum(row['faizli_dermanlar'][index] for row in report_data)
#         faizli_derman_toplamlari.append(round(toplam_faizli, 2))

#     toplam_hekim_say = sum(item['toplam'] for item in report_data)
#     toplam_faizli_say = round(sum(item['faizli_toplam'] for item in report_data), 2)

#     # Effektivlik faizləri hesablanması
#     sales = Sale.objects.filter(region_id=region_id)
#     effektivlik_faizleri = []

#     for index, derman in enumerate(dermanlar):
#         satis_sayi = sales.filter(drug=derman).aggregate(s=Sum('quantity'))['s'] or 0
#         faizli_resept = faizli_derman_toplamlari[index]

#         effektivlik = (Decimal(satis_sayi) / Decimal(faizli_resept)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if faizli_resept > 0 else Decimal('0.00')
#         effektivlik_faizleri.append(effektivlik)

#     # Həkim reseptlərinə effektivlik tətbiqi
#     for row in report_data:
#         row['effektivlikli_dermanlar'] = []
#         row['effektivlikli_toplam'] = Decimal('0.00')

#         for i, faizli in enumerate(row['faizli_dermanlar']):
#             effektivlik = Decimal(str(effektivlik_faizleri[i]))
#             vurulmus = (Decimal(str(faizli)) * effektivlik).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             row['effektivlikli_dermanlar'].append(vurulmus)
#             row['effektivlikli_toplam'] += vurulmus

#     # Həkim modelinə yaz (hesablanan miqdar)
#     for row in report_data:
#         hekim = row['hekim']
#         hekim.hesablanan_miqdar = row['effektivlikli_toplam']
#         hekim.save()

#     # Effektivlikli dərman toplamları (sütunlara görə cəmlər)
#     effektivlikli_derman_toplamlari = []
#     for i in range(len(dermanlar)):
#         cem = sum(row['effektivlikli_dermanlar'][i] for row in report_data)
#         effektivlikli_derman_toplamlari.append(round(cem, 2))

#     toplam_effektivlikli_say = round(sum(effektivlikli_derman_toplamlari), 2)

#     # Komissiyalı hesablamalar
#     for row in report_data:
#         row['komissiya_miqdarlari'] = []
#         row['umumi_komissiya'] = Decimal('0')

#         for i, effektiv_miqdar in enumerate(row['effektivlikli_dermanlar']):
#             derman = dermanlar[i]
#             komissiya_faizi = derman.komissiya or Decimal('0')
#             miqdar = Decimal(str(effektiv_miqdar)) * komissiya_faizi
#             miqdar = miqdar.quantize(Decimal('0.01'))
#             row['komissiya_miqdarlari'].append(miqdar)
#             row['umumi_komissiya'] += miqdar

#         row['hekimden_silinen'] = row['umumi_komissiya']

#     toplam_komissiya = sum(row['umumi_komissiya'] for row in report_data).quantize(Decimal('0.01'))

#     # Həkim modelinə yaz (komissiya və effektivlik)
#     for row in report_data:
#         hekim = row['hekim']
#         hekim.hesablanan_miqdar = row['effektivlikli_toplam']
#         row['hekim_effektiv_komissiya'] = list(zip(row['effektivlikli_dermanlar'], row['komissiya_miqdarlari']))
#         hekim.hekimden_silinen = row['umumi_komissiya']
#         hekim.save()

#     region = get_object_or_404(Region, id=region_id)

#     context = {
#         'dermanlar': dermanlar,
#         'hekimler_data': report_data,
#         'derman_toplamlari': derman_toplamlari,
#         'faizli_derman_toplamlari': faizli_derman_toplamlari,
#         'effektivlik_faizleri': effektivlik_faizleri,
#         'region': region,
#         'toplam_hekim_say': toplam_hekim_say,
#         'toplam_faizli_say': toplam_faizli_say,
#         'effektivlikli_derman_toplamlari': effektivlikli_derman_toplamlari,
#         'toplam_effektivlikli_say': toplam_effektivlikli_say,
#         'toplam_komissiya': toplam_komissiya,
#     }

#     return render(request, 'test_2.html', context)