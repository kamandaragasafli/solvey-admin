from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from datetime import date
from decimal import Decimal as D
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
from payment.models import Payment_doctor, Sale, MonthlyDoctorReport, Financial_document
from regions.models import Region
from doctors.models import Doctors, Recipe, RecipeDrug
from medicine.models import Medical
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.core.serializers.json import DjangoJSONEncoder
import json
from collections import defaultdict
from django.db.models.functions import ExtractMonth
from datetime import datetime
import urllib.parse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.http import HttpResponse
from decimal import Decimal as d
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt




def get_doctors_by_region(request):
    region_id = request.GET.get("region_id")
    if region_id:
        doctors = Doctors.objects.filter(bolge_id=region_id).order_by("ad")
        doctor_list = [{"id": d.id, "ad": d.ad} for d in doctors]
        return JsonResponse({"doctors": doctor_list})
    return JsonResponse({"doctors": []})


def add_pay_dr(request, region_id=None):

    
    region = Region.objects.all()

    if region_id:
        
        doctors = Doctors.objects.filter(bolge_id=region_id).prefetch_related('odenisler')

        for d in doctors:
            last = d.odenisler.order_by('-date').first()
            if last:
                d.son_odenis_mebleg = last.pay
                d.son_odenis_tarixi = last.date
                d.son_odenis_novu = last.payment_type

    else:
        doctors = Doctors.objects.none()

    if request.method == "POST":
        region_id = request.POST.get("region_id")
        doctor_id = request.POST.get("doctor_id")
        payment_type = request.POST.get("payment_type")
        amount = request.POST.get("amount")
        pay_date = request.POST.get("pay_date")

        if not all([region_id, doctor_id, payment_type, amount, pay_date]):
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return redirect("add-pay-dr-region", region_id=region_id)

        try:
            borc_miqdari = Decimal(amount)
        except:
            messages.error(request, "Ödəniş məbləği düzgün formatda deyil.")
            return redirect("add-pay-dr-region", region_id=region_id)

        dr = get_object_or_404(Doctors, id=doctor_id)

        try:
            # Ödəniş qeyd edilir
            Payment_doctor.objects.create(
                area_id=region_id,
                doctor_id=doctor_id,
                payment_type=payment_type,
                pay=borc_miqdari,
                date=pay_date
            )
            

            if payment_type == "Avans":
                dr.avans = borc_miqdari
                dr.investisiya = 0
                dr.geriqaytarma = 0
                # dr.borc += borc_miqdari  # <-- bunu sil

            elif payment_type == "İnvest":
                dr.investisiya = borc_miqdari
                dr.avans = 0
                dr.geriqaytarma = 0
                # dr.borc -= borc_miqdari  # <-- bunu sil

            elif payment_type == "Geri_qaytarma":
                dr.geriqaytarma = borc_miqdari
                dr.avans = 0
                dr.investisiya = 0

                # Bu hissə qalır, çünki "ödəniş" kimi düşünülür
                if dr.borc > 0:
                    dr.borc -= borc_miqdari
                else:
                    dr.borc += borc_miqdari



            dr.save()

            messages.success(request, "Ödəniş uğurla əlavə edildi.")
            return redirect("doctor_detail", doctor_id=doctor_id)


        except Exception as e:
            messages.error(request, f"Xəta baş verdi: {e}")
            return redirect("add-pay-dr-region", region_id=region_id)

    context = {
        "region": region,
        "doctors": doctors,
        "selected_region_id": region_id,
    }
    return render(request, "crud/addpay_dr.html", context)



def document_add(request):
    region = Region.objects.all()  # Bölgələri template'a göndərin
    
    if request.method == 'POST':
        try:
            region_id = request.POST.get('region_id')
            doctor_id = request.POST.get('doctor_id')
            check_photo = request.FILES.get('check_photo')
            check_date = request.POST.get('check_date')
            
            if not all([region_id, doctor_id, check_photo, check_date]):
                messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
                return redirect('document_add')
            
            # Fayl ölçüsünü yoxla
            if check_photo.size > 5 * 1024 * 1024:  # 5MB
                messages.error(request, "Fayl ölçüsü 5MB-dan çox ola bilməz")
                return redirect('document_add')
            
            # Sənədi yadda saxla
            document = Financial_document(
                check_photo=check_photo,
                check_dr_id=doctor_id,
                check_region_id=region_id,
                check_date=check_date
            )
            document.save()
            
            messages.success(request, 'Sənəd uğurla əlavə edildi!')
            return redirect('document_add')
            
        except Exception as e:
            messages.error(request, f'Xəta baş verdi: {str(e)}')
            return redirect('document_add')
    
    context = {
        'region': region,
    }
    return render(request, 'crud/add_document.html', context)




def financial_documents(request):
    documents = Financial_document.objects.select_related(
        'check_dr', 'check_region'
    ).order_by('-check_date')
    
    # Filter by region if provided
    region_id = request.GET.get('region')
    if region_id:
        documents = documents.filter(check_region_id=region_id)
    
    # Filter by doctor name if provided
    doctor_name = request.GET.get('doctor')
    if doctor_name:
        documents = documents.filter(check_dr__ad__icontains=doctor_name)
    
    # Statistics
    total_documents = documents.count()
    this_month = timezone.now().month
    this_month_count = documents.filter(
        check_date__month=this_month
    ).count()
    
    regions = Region.objects.all()
    
    context = {
        'documents': documents,
        'total_documents': total_documents,
        'this_month_count': this_month_count,
        'regions': regions,
    }
    
    return render(request, 'finance-document.html', context)

def create_sale(request):
    drug_all = Medical.objects.all().order_by('id')
    region_all = Region.objects.all()

    if request.method == "POST":
        region_id = request.POST.get("region")
        date_str = request.POST.get("date")

        if not region_id or not date_str:
            messages.error(request, "Bölgə və tarixi seçməlisiniz!")
            return redirect('index')

        # Tarixi date tipinə çeviririk
        try:
            sale_date = parse_date(date_str)
            if sale_date is None:
                raise ValueError
        except ValueError:
            messages.error(request, "Tarix düzgün deyil!")
            return redirect('index')

        region = Region.objects.get(id=region_id)
        sales_created = False
        errors = []

        # Bu ayın ilk günü (aylığa görə yoxlamaq üçün)
        month_start = sale_date.replace(day=1)

        for key, value in request.POST.items():
            if key.startswith('quantity_') and value.isdigit() and int(value) > 0:
                drug_id = key.split("_")[1]
                quantity = int(value)
                drug = Medical.objects.get(id=drug_id)

                # Eyni ay, bölgə, dərman üçün artıq satış var?
                exists = Sale.objects.filter(
                    region=region,
                    drug=drug,
                    sale_date__year=month_start.year,
                    sale_date__month=month_start.month
                ).exists()

                if exists:
                    errors.append(f"{drug.med_name} dərmanı üçün bu ay artıq satış əlavə olunub.")
                else:
                    Sale.objects.create(
                        region=region,
                        drug=drug,
                        quantity=quantity,
                        sale_date=sale_date
                    )
                    sales_created = True

        if sales_created:
            messages.success(request, 'Satışlar uğurla əlavə olundu')

        if errors:
            for error in errors:
                messages.warning(request, error)

        if not sales_created and not errors:
            messages.warning(request, 'Heç bir dərman seçilməyib')

        return redirect('index')

    context = {
        "drug_all": drug_all,
        "region_all": region_all,
    }
    return render(request, 'crud/add-sales.html', context)

def sales(request):
    # Get all regions and drugs
    all_region = Region.objects.all()
    all_drug = Medical.objects.all().order_by('id')

    # Get available years for the year dropdown
    years = Sale.objects.dates('sale_date', 'year').distinct()
    years = [year.year for year in years]

    # Initialize sales dictionary and totals
    sales_dict = {}
    totals_per_region = {}

    # Get filter parameters
    region_search = request.GET.get('region_search', '')
    region_id = request.GET.get('region', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')

    # Base queryset for sales
    sales_queryset = Sale.objects.all()

    # Apply filters
    if region_search:
        all_region = all_region.filter(region_name__icontains=region_search)
    if region_id:
        all_region = all_region.filter(id=region_id)
    if month:
        sales_queryset = sales_queryset.filter(sale_date__month=month)
    if year:
        sales_queryset = sales_queryset.filter(sale_date__year=year)

    # Build sales dictionary
    for region in all_region:
        sales_dict[region.id] = {}
        region_total = 0
        for drug in all_drug:
            qty = sales_queryset.filter(region=region, drug=drug).aggregate(Sum('quantity'))['quantity__sum'] or 0
            sales_dict[region.id][drug.id] = qty
            region_total += qty
        totals_per_region[region.id] = region_total

    context = {
        'all_region': all_region,
        'all_drug': all_drug,
        'sales_dict': sales_dict,
        'totals_per_region': totals_per_region,
        'years': years,
    }
    return render(request, "reports/sales.html", context)

def report_list(request):
    region = Region.objects.all()
    drug = Medical.objects.all().order_by('id')

    context = {
        "region": region,
        "drug": drug
    }
    return render(request, "reports/report.html", context)


def d(v):
    try:
        return Decimal(str(v or 0))
    except (TypeError, ValueError):
        return Decimal('0')
    


def ajax_region_report(request):
    region_id = request.GET.get("region_id")
    month = request.GET.get("month")
    borc_filter = request.GET.get("borc")

    if not region_id:
        return JsonResponse({"results": []})

    doctors = Doctors.objects.filter(bolge_id=region_id)
    result = []

    # Satışlar (bütün region üçün filtr)
    sales = Sale.objects.filter(region_id=region_id)
    if month:
        try:
            ay = int(month)
            sales = sales.filter(sale_date__month=ay)
        except ValueError:
            sales = Sale.objects.none()

    sales_exist = sales.exists()

    for doctor in doctors:
        # Seçilən ay üçün mövcud hesabatı tap
        monthly_report = None
        if month:
            try:
                report_month = date.today().replace(month=int(month), day=1)
                monthly_report = MonthlyDoctorReport.objects.filter(
                    doctor=doctor,
                    report_month=report_month
                ).first()
            except ValueError:
                pass

        if monthly_report:
            previous_debt = d(monthly_report.yekun_borc or 0)
            borc = d(monthly_report.borc or 0)
            avans = d(monthly_report.avans or 0)
            investisiya = d(monthly_report.investisiya or 0)
            datasiya = d(0)
            hekimden_silinen = d(monthly_report.hekimden_silinen or 0)
            hesablanan_miqdar = d(monthly_report.hesablanan_miqdar or 0)
        else:
            previous_debt = d(doctor.previous_debt or 0)
            borc = d(doctor.borc or 0)
            avans = d(doctor.avans or 0)
            investisiya = d(doctor.investisiya or 0)
            datasiya = d(doctor.datasiya or 0)
            hekimden_silinen = d(doctor.hekimden_silinen or 0)
            hesablanan_miqdar = d(doctor.hesablanan_miqdar or 0)

        # Əgər satış yoxdursa bu iki sahə sıfır olsun
        if not sales_exist:
            hekimden_silinen = d(0)
            hesablanan_miqdar = d(0)

        # Dərman məlumatları (reseptlər)
        recipe_drugs = RecipeDrug.objects.filter(
            recipe__dr=doctor,
            recipe__region_id=region_id
        )
        if month:
            try:
                ay = int(month)
                recipe_drugs = recipe_drugs.filter(recipe__date__month=ay)
            except ValueError:
                recipe_drugs = RecipeDrug.objects.none()

        drugs_agg = recipe_drugs.values('drug__med_name').annotate(total_count=Sum('number'))

        drugs = []
        total = 0
        for d_item in drugs_agg:
            drugs.append({
                "name": d_item['drug__med_name'],
                "count": d_item['total_count']
            })
            total += d_item['total_count']

        yekun_borc = previous_debt + avans + investisiya + datasiya - hekimden_silinen

        if borc_filter == "borclu" and yekun_borc <= 0:
            continue
        if borc_filter == "borcsuz" and yekun_borc > 0:
            continue

        result.append({
            "bolge": doctor.bolge.region_name,
            "doctor": doctor.ad,
            "doctor_id": doctor.id,
            "barcode": doctor.barkod,
            "kategoriya": doctor.get_kategoriya_display(),
            "derece": doctor.get_derece_display(),
            "ixtisas": doctor.get_ixtisas_display(),
            "previous_debt": float(previous_debt),
            "borc": float(borc),
            "avans": float(avans),
            "investisiya": float(investisiya),
            "datasiya": float(datasiya),
            "hekimden_silinen": float(hekimden_silinen),
            "hesablanan_miqdar": float(hesablanan_miqdar),
            "drugs": drugs,
            "total": float(total),
            "yekun_borc": float(yekun_borc),
        })

    return JsonResponse({"results": result}, json_dumps_params={'ensure_ascii': False})






@csrf_exempt
def hesabat_bagla(request):
    if request.method == "POST":
        try:
            ay = int(request.POST.get("ay"))
            il = int(request.POST.get("il"))
            region_id = request.POST.get("region_id")
            ay_tarixi = date(il, ay, 1)

            # Həkimləri seç
            if region_id:
                doctors_qs = Doctors.objects.filter(bolge_id=region_id)
            else:
                doctors_qs = Doctors.objects.all()

            with transaction.atomic():
                for doctor in doctors_qs.select_for_update():
                    previous_debt = D(doctor.previous_debt or 0)
                    borc = D(doctor.borc or 0)
                    avans = D(doctor.avans or 0)
                    investisiya = D(doctor.investisiya or 0)
                    hekimden_silinen = D(doctor.hekimden_silinen or 0)
                    datasiya = D(doctor.datasiya or 0)

                    yekun_borc = previous_debt + avans + investisiya + datasiya - hekimden_silinen

                    # Reseptləri götür
                    recipes = Recipe.objects.filter(
                        dr=doctor,
                        region=doctor.bolge,
                        date__year=ay_tarixi.year,
                        date__month=ay_tarixi.month
                    )
                    total_drugs = sum(item.number for recipe in recipes for item in recipe.drugs.all())

                    # Cari ay üçün hesabat
                    MonthlyDoctorReport.objects.update_or_create(
                        doctor=doctor,
                        report_month=ay_tarixi,
                        defaults={
                            "region": doctor.bolge,
                            "borc": float(borc),
                            "avans": float(avans),
                            "investisiya": float(investisiya),
                            "hekimden_silinen": float(hekimden_silinen),
                            "hesablanan_miqdar": float(doctor.hesablanan_miqdar or 0),
                            "yekun_borc": float(yekun_borc),
                            "recipe_total_drugs": total_drugs,
                        }
                    )

                    # Növbəti aya devr: həkim modelində previous_debt yenilə
                    doctor.previous_debt = yekun_borc
                    doctor.avans = 0
                    doctor.investisiya = 0
                    doctor.datasiya = 0
                    doctor.save(update_fields=["previous_debt","avans", "investisiya", "datasiya"])

            return JsonResponse({
                "success": True,
                "message": f"{ay_tarixi.strftime('%Y-%m')} ayının hesabatı uğurla bağlandı."
            })

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Xəta baş verdi: {str(e)}"})

    return JsonResponse({"success": False, "message": "Yalnız POST icazəlidir."})




    
def export_region_report_excel(request):
    region_id = request.GET.get("region_id")
    month = request.GET.get("month")
    drugs = list(Medical.objects.all().order_by('id'))  # Bütün dərmanlar

    if not region_id:
        return HttpResponse("Bölgə seçilməyib.", status=400)

    doctors = Doctors.objects.filter(bolge_id=region_id).select_related('bolge')
    
    # Satışların olub-olmadığını yoxla (AJAX funksiyası ilə eyni məntiq)
    sales = Sale.objects.filter(region_id=region_id)
    if month:
        try:
            ay = int(month)
            sales = sales.filter(sale_date__month=ay)
        except ValueError:
            sales = Sale.objects.none()
    
    sales_exist = sales.exists()

    wb = Workbook()
    ws = wb.active
    ws.title = "Bölgə Hesabatı"

    # Başlıqlar
    headers = [
        "№", "Bölgə", "Həkim", "Kod", "Kateqoriya", "Dərəcə", "İxtisas", "Əvvəlki Borc"
    ] + [d.med_name for d in drugs] + [
        "Total", "Hesablanan Miqdar", "Həkimdən Silinən", "Avans", "İnvestisiya", "Datasiya", "Yekun Borc"
    ]

    ws.append([])  # Boş sətir
    ws.append(headers)

    bold_font = Font(bold=True, color="060411")
    header_fill = PatternFill(fill_type="solid", fgColor="F0F0F0")
    thin = Side(style='thin', color="000000")
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Başlıqları formatla
    for cell in ws[2]:
        cell.font = bold_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center", textRotation=90)

    ws.freeze_panes = "A3"

    # Cəmlər üçün dəyişənlər
    drug_totals = [0] * len(drugs)
    total_total = d(0)
    hesablanan_miqdar_total = d(0)
    hekimden_silinen_total = d(0)
    avans_total = d(0)
    investisiya_total = d(0)
    datasiya_total = d(0)
    yekun_borc_total = d(0)
    previous_debt_total = d(0)

    for idx, doctor in enumerate(doctors, start=1):
        # Seçilən ay üçün mövcud hesabatı tap (AJAX ilə uyğunlaşdır)
        monthly_report = None
        if month:
            try:
                ay = int(month)
                report_month = date.today().replace(month=ay, day=1)
                monthly_report = MonthlyDoctorReport.objects.filter(
                    doctor=doctor,
                    report_month=report_month
                ).first()
            except ValueError:
                pass

        if monthly_report:
            # Hesabat bağlanıbsa, həmin ayın dəyərlərini göstər
            previous_debt = d(monthly_report.yekun_borc or 0)
            borc = d(monthly_report.borc or 0)
            avans = d(monthly_report.avans or 0)
            investisiya = d(monthly_report.investisiya or 0)
            datasiya = d(0)
            hekimden_silinen = d(monthly_report.hekimden_silinen or 0)
            hesablanan_miqdar = d(monthly_report.hesablanan_miqdar or 0)
        else:
            # Hesabat hələ bağlanmayıbsa, həkimdən götür
            previous_debt = d(doctor.previous_debt or 0)
            borc = d(doctor.borc or 0)
            avans = d(doctor.avans or 0)
            investisiya = d(doctor.investisiya or 0)
            datasiya = d(doctor.datasiya or 0)
            hekimden_silinen = d(doctor.hekimden_silinen or 0)
            hesablanan_miqdar = d(doctor.hesablanan_miqdar or 0)

        # ƏGər satış yoxdursa, bu iki sahəni sıfırla (AJAX ilə eyni məntiq)
        if not sales_exist:
            hekimden_silinen = d(0)
            hesablanan_miqdar = d(0)

        yekun_borc = previous_debt + avans + investisiya + datasiya - hekimden_silinen

        # Recipes və drug məlumatları (month filter ilə)
        recipes = Recipe.objects.filter(dr=doctor, region_id=region_id)
        if month:
            try:
                ay = int(month)
                recipes = recipes.filter(date__month=ay)
            except ValueError:
                recipes = Recipe.objects.none()

        drug_map = defaultdict(int)
        total = 0
        for recipe in recipes:
            # RecipeDrug vasitəsilə dərmanları al (AJAX ilə uyğunlaşdır)
            recipe_drugs = RecipeDrug.objects.filter(recipe=recipe)
            for item in recipe_drugs:
                drug_map[item.drug.med_name] += item.number
                total += item.number

        previous_debt_total += previous_debt
        hesablanan_miqdar_total += hesablanan_miqdar
        hekimden_silinen_total += hekimden_silinen
        avans_total += avans
        investisiya_total += investisiya
        datasiya_total += datasiya
        yekun_borc_total += yekun_borc
        total_total += total

        row = [
            idx,
            doctor.bolge.region_name,
            doctor.ad,
            doctor.barkod,
            doctor.get_kategoriya_display(),
            doctor.get_derece_display(),
            doctor.get_ixtisas_display(),
            float(previous_debt)
        ]

        # Dərman sütunları və cəmləri
        for i, drug in enumerate(drugs):
            val = drug_map.get(drug.med_name, 0)
            drug_totals[i] += val  # cəmi əlavə et
            row.append(val)

        row += [
            float(total),
            float(hesablanan_miqdar),
            float(hekimden_silinen),
            float(avans),
            float(investisiya),
            float(datasiya),
            float(yekun_borc)
        ]

        ws.append(row)

    # Alt sətir (cəmi)
    total_row_idx = ws.max_row + 1
    # "Cəmi" labelini "Bölgə" sütununa qoy (column 2)
    ws.cell(row=total_row_idx, column=2, value="Cəmi").font = Font(bold=True)
    ws.cell(row=total_row_idx, column=2).alignment = Alignment(horizontal="center")

    # Əvvəlki borcun cəmi (column 8)
    ws.cell(row=total_row_idx, column=8, value=float(previous_debt_total)).font = Font(bold=True)

    # Dərmanların cəmi (columns 9 to 9+len(drugs)-1)
    drug_start_col = 9
    for i, total_val in enumerate(drug_totals):
        ws.cell(row=total_row_idx, column=drug_start_col + i, value=total_val).font = Font(bold=True)

    # Yekun sütunların cəmləri (base_col = 9 + len(drugs))
    base_col = 9 + len(drugs)
    ws.cell(row=total_row_idx, column=base_col, value=float(total_total)).font = Font(bold=True)  # Total
    ws.cell(row=total_row_idx, column=base_col + 1, value=float(hesablanan_miqdar_total)).font = Font(bold=True)
    ws.cell(row=total_row_idx, column=base_col + 2, value=float(hekimden_silinen_total)).font = Font(bold=True)
    ws.cell(row=total_row_idx, column=base_col + 3, value=float(avans_total)).font = Font(bold=True)
    ws.cell(row=total_row_idx, column=base_col + 4, value=float(investisiya_total)).font = Font(bold=True)
    ws.cell(row=total_row_idx, column=base_col + 5, value=float(datasiya_total)).font = Font(bold=True)
    ws.cell(row=total_row_idx, column=base_col + 6, value=float(yekun_borc_total)).font = Font(bold=True)

    # Hüceyrələrə border və hizalama (alt sətir üçün)
    thin = Side(style='thin', color="BFBFBF")
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Alt sətir border və alignment
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=total_row_idx, column=col)
        cell.border = thin_border
        if isinstance(cell.value, (int, float)):
            cell.alignment = Alignment(horizontal="right")
        else:
            cell.alignment = Alignment(horizontal="center")

    # Bütün məlumat sətirləri üçün border və alignment
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.border = thin_border
            if isinstance(cell.value, (int, float)):
                cell.alignment = Alignment(horizontal="right")

    # Sütun genişliyi tənzimlənməsi
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            val_len = len(str(cell.value)) if cell.value else 0
            if val_len > max_length:
                max_length = val_len
        ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

    # Fayl adı
    region_name = doctors[0].bolge.region_name if doctors.exists() else "Region"
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{region_name}_Borc_{today_str}.xlsx".replace(" ", "_")

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
     
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    wb.save(response)
    return response

def kohne_hesabat(request):
    region_list = Region.objects.all()
    drug_list = Medical.objects.all().order_by('id')

    aylar = [
        (1, "Yanvar"),
        (2, "Fevral"),
        (3, "Mart"),
        (4, "Aprel"),
        (5, "May"),
        (6, "İyun"),
        (7, "İyul"),
        (8, "Avqust"),
        (9, "Sentyabr"),
        (10, "Oktyabr"),
        (11, "Noyabr"),
        (12, "Dekabr"),
    ]

    # Mövcud illəri gətir
    current_year = timezone.now().year
    years = range(current_year - 5, current_year + 1)

    context = {
        'region': region_list,
        'drug': drug_list,
        'aylar': aylar,
        'years': reversed(list(years)),  # Ən son illər üstə
    }
    return render(request, 'reports/old-report.html', context)


def kohne_region_ajax(request):
    region_id = request.GET.get('region_id')
    month = request.GET.get('month')
    year = request.GET.get('year', timezone.now().year)  # İl parametrini də əlavə et

    if not region_id or not month:
        return JsonResponse({'error': 'Region və ay seçilməyib'}, status=400)

    try:
        # İli də nəzərə al
        report_month = date(year=int(year), month=int(month), day=1)
    except ValueError:
        return JsonResponse({'error': 'Yanlış tarix dəyəri'}, status=400)

    # Hesabatları gətir
    reports = MonthlyDoctorReport.objects.filter(
        region_id=region_id,  # region sahəsini birbaşa istifadə et
        report_month=report_month
    ).select_related('doctor', 'region')

    results = []
    for report in reports:
        try:
            drugs = json.loads(report.recipe_drugs_list or '[]')
        except json.JSONDecodeError:
            drugs = []

        # Həkimə aid əsas məlumatlar
        doctor = report.doctor
        results.append({
            'bolge': report.region.region_name if report.region else '',
            'doctor': doctor.ad,
            'barcode': getattr(doctor, 'barcode', ''),
            'kategoriya': getattr(doctor, 'kategoriya', ''),
            'derece': getattr(doctor, 'derece', ''),
            'ixtisas': getattr(doctor, 'ixtisas', ''),
            'previous_debt': float(report.borc or 0),
            'drugs': drugs,  # Artıq formatlanmış drugs listi
            'total': report.recipe_total_drugs or 0,
            'hekimden_silinen': float(report.hekimden_silinen or 0),
            'hesablanan_miqdar': float(report.hesablanan_miqdar or 0),
            'avans': float(report.avans or 0),
            'investisiya': float(report.investisiya or 0),
            'yekun_borc': float(report.yekun_borc or 0),
        })

    return JsonResponse({'results': results})

