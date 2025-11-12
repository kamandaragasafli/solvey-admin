
from django.http import HttpResponse
from openpyxl import Workbook
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.shortcuts import render,redirect,get_object_or_404
from medicine.models import Medical
from decimal import Decimal
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from django.contrib import messages
from datetime import datetime
from django.db.models import Sum, DecimalField
from django.http import JsonResponse

from django.db.models import Count,  Sum
from django.utils import timezone
from django.utils.timezone import make_aware, is_aware
from datetime import datetime, time

from django.db.models import Count
from django.db.models.functions import Coalesce
from doctors.models import Doctors, Recipe, RecipeDrug
from regions.models import Region, Hospital, City
from core.models import DeletedRecipeDrugLog
from itertools import chain
from operator import attrgetter
from decimal import Decimal, ROUND_HALF_UP
import urllib.parse
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from datetime import datetime



def ensure_aware_datetime(value):
    """Giriş dəyəri datetime.date və ya datetime.datetime ola bilər"""
    if isinstance(value, datetime):
        dt = value
    else:  # əgər bu datetime.date-dirsə
        dt = datetime.combine(value, time.min)
    
    if not is_aware(dt):
        return make_aware(dt)
    return dt


# Əsas Səhifə
def index(request):
    # Həkimlər, xəstəxanalar, şəhərlər
    doctors = Doctors.objects.select_related('bolge').all()
    total_doctors = doctors.count()
    total_hospitals = Hospital.objects.count()
    total_cities = City.objects.count()
    all_drug = Medical.objects.all()



    # Şəhər statistikası
    city_stats = Hospital.objects.values('city__city_name').annotate(say=Count('id'))
    city_labels = [x['city__city_name'] for x in city_stats]
    city_counts = [x['say'] for x in city_stats]

    baki_hospitals_b = Hospital.objects.filter(region_net__region_type='Bakı').count()

    # Son reseptlər
    last_recipes = Recipe.objects.select_related('dr').order_by('-date')[:10]

    # Son silinmiş loglar
    deleted_logs = DeletedRecipeDrugLog.objects.order_by('-deleted_at')[:10]
    for log in deleted_logs:
        try:
            log.recipe = Recipe.objects.select_related('dr').get(id=log.recipe_id)
        except Recipe.DoesNotExist:
            log.recipe = None

    # Tip ayırd edilməsi üçün obyektlərə atribut əlavə edək
    for r in last_recipes:
        r.event_type = "added"
        r.event_date = ensure_aware_datetime(r.date)

    for l in deleted_logs:
        l.event_type = "deleted"
        l.event_date = ensure_aware_datetime(l.deleted_at)

    # Birləşdir və sırala
    combined_events = sorted(
        chain(last_recipes, deleted_logs),
        key=attrgetter("event_date"),
        reverse=True
    )[:10]

    # Aktiv həkim sayı
    active_count = (
        Doctors.objects
        .annotate(derman_sayi=Count('recipe__drugs'))
        .filter(derman_sayi__gt=1)
        .count()
    )



    today = timezone.localdate()
    first_day_of_month = today.replace(day=1)

    # Digər bölgələr
    diger_region = Region.objects.filter(region_type="Digər")
    baki_region = Region.objects.filter(region_type="Bakı")

    # Bakı üçün data (hamısı sıfır olacaq)
    baki_region_drug_counts = {}
    baki_region_daily_totals = {}
    baki_region_monthly_totals = {}

    for region in baki_region:
        baki_region_drug_counts[region.region_name] = {}
        daily_total = Decimal(0)
        monthly_total = Decimal(0)

        for drug in all_drug:
            baki_region_drug_counts[region.region_name][drug.med_name] = 0

        baki_region_daily_totals[region.region_name] = 0
        baki_region_monthly_totals[region.region_name] = 0

    # RecipeDrug məlumatları
    drugs_data = (
        RecipeDrug.objects
        .filter(recipe__region__in=diger_region)
        .values("recipe__region__region_name", "drug__med_name", "recipe__date")
        .annotate(total=Sum("number"))
    )

    region_drug_counts = {}
    region_daily_totals = {}
    region_monthly_totals = {}

    # Dövr: hər bölgə üçün gündəlik və aylıq hesabla
    for region in diger_region:
        region_drug_counts[region.region_name] = {}
        daily_total = Decimal(0)
        monthly_total = Decimal(0)

        for drug in all_drug:
            # Gündəlik
            daily = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and item["recipe__date"] == today
            )
            # Aylıq
            monthly = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and first_day_of_month <= item["recipe__date"] <= today
            )

            region_drug_counts[region.region_name][drug.med_name] = daily
            daily_total += daily
            monthly_total += monthly

        region_daily_totals[region.region_name] = daily_total
        region_monthly_totals[region.region_name] = monthly_total

    # ✅ Dövr bitdi, indi sıralama et
    diger_region = sorted(
        diger_region,
        key=lambda r, totals=region_monthly_totals: totals.get(r.region_name, 0),
        reverse=True
    )
    # Bakı regionları üçün
    baki_drugs_data = (
        RecipeDrug.objects
        .filter(recipe__region__in=baki_region)
        .values("recipe__region__region_name", "drug__med_name", "recipe__date")
        .annotate(total=Sum("number"))
    )

    baki_region_drug_counts = {}
    baki_region_daily_totals = {}
    baki_region_monthly_totals = {}

    for region in baki_region:
        baki_region_drug_counts[region.region_name] = {}
        daily_total = 0
        monthly_total = 0

        for drug in all_drug:
            # Günlük
            daily = sum(
                item["total"]
                for item in baki_drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and item["recipe__date"] == today
            )
            # Aylıq
            monthly = sum(
                item["total"]
                for item in baki_drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and first_day_of_month <= item["recipe__date"] <= today
            )

            baki_region_drug_counts[region.region_name][drug.med_name] = daily
            daily_total += daily
            monthly_total += monthly

        baki_region_daily_totals[region.region_name] = daily_total
        baki_region_monthly_totals[region.region_name] = monthly_total

    baki_region = sorted(
    baki_region,
    key=lambda r, totals=baki_region_monthly_totals: totals.get(r.region_name, 0),
    reverse=True
)
    today = timezone.localdate()  # Cari tarix
    current_month = today.month   # Cari ay
    current_year = today.year  
    total_other = (
        RecipeDrug.objects
        .filter(
            recipe__region__in=diger_region,
            recipe__date__month=current_month,
            recipe__date__year=current_year
        )
        .aggregate(total=Coalesce(Sum('number', output_field=DecimalField()), Decimal('0.0')))
    )['total']
    total_other = total_other.quantize(Decimal('1.'), rounding=ROUND_HALF_UP)

    total_baku = (
        RecipeDrug.objects
        .filter(
            recipe__region__in=baki_region,
            recipe__date__month=current_month,
            recipe__date__year=current_year
        )
        .aggregate(total=Coalesce(Sum('number', output_field=DecimalField()), Decimal('0.0')))
    )['total']
    total_baku = total_baku.quantize(Decimal('1.'), rounding=ROUND_HALF_UP)

    # Context dövrün içində deyil, dövr bitdikdən sonra
    context = {
        'doctors': doctors,
        'aktiv_sayi': active_count,
        'combined_events': combined_events,
        'total_doctors': total_doctors,
        'total_hospitals': total_hospitals,
        'total_cities': total_cities,
        'city_labels': city_labels,
        'city_counts': city_counts,
        'baki_hospitals_bage': baki_hospitals_b,
        'total_other': total_other,
        'total_baku': total_baku,
        'doctor_count': total_doctors,
        'city_count': total_cities,
        'hospital_count': total_hospitals,
        "all_drug": all_drug,
        "diger_region": diger_region,
        "baki_region":baki_region,
        "region_drug_counts": region_drug_counts,
        "region_daily_totals": region_daily_totals,
        "region_monthly_totals": region_monthly_totals,

        "baki_region_drug_counts": baki_region_drug_counts,
        "baki_region_daily_totals": baki_region_daily_totals,
        "baki_region_monthly_totals": baki_region_monthly_totals,
  
    }

    return render(request, 'index.html', context)


# Region data Start
def region_drug_data_other(request):
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    regions = (
        Region.objects
        .filter(region_type='Digər')
        .annotate(
            drug_count=Coalesce(
                Sum(
                    'doctors__recipe__drugs__number',
                    filter=(
                        Q(doctors__recipe__date__month=current_month) &
                        Q(doctors__recipe__date__year=current_year)
                    )
                ),
                0,
                output_field=DecimalField()
            )
        )
        .order_by('region_name')
    )

    labels = [r.region_name for r in regions]
    counts = [float(r.drug_count) for r in regions]  # Decimal → float

    return JsonResponse({
        'labels': labels,
        'data': counts
    })

def region_drug_data_baku(request):
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    regions = (
        Region.objects
        .filter(region_type='Bakı')
        .annotate(
            drug_count=Coalesce(
                Sum(
                    'doctors__recipe__drugs__number',
                    filter=(
                        Q(doctors__recipe__date__month=current_month) &
                        Q(doctors__recipe__date__year=current_year)
                    )
                ),
                0,
                output_field=DecimalField()
            )
        )
        .order_by('region_name')
    )

    labels = [r.region_name for r in regions]
    counts = [float(r.drug_count) for r in regions]  # Decimal → float

    return JsonResponse({
        'labels': labels,
        'data': counts
    })


# Region data end
# Login
# def user_login(request):
#     if request.method == "POST":
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
        
#         if user is not None:
#             login(request, user)

#             if user.is_superuser:
#                 return redirect('/admin')  # Superuser admin panelə
#             elif user.groups.filter(name="Moderator").exists():
#                 return redirect('/admin')  # Moderator dashboard
#             elif user.groups.filter(name="İstifadəçi").exists():
#                 return redirect('movqe_gonder_view')  # Normal istifadəçi
#             else:
#                 # Qrup təyin olunmayıbsa normal istifadəçi kimi
#                 return redirect('movqe_gonder_view')  
#         else:
#             error = "İstifadəçi adı və ya şifrə yanlışdır"
#             return render(request, 'login.html', {'error': error})
    
#     return render(request, 'login.html')

def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('/admin')  # Superuser admin panelə
        else:
            error = "İstifadəçi adı və ya şifrə yanlışdır"
            return render(request, 'login.html', {'error': error})
    
    return render(request, 'login.html')



def user_logout(request):
    logout(request)
    return redirect('login')

# Aylıq və günlük Excel Faylı Çıxarışı start
def export_excel_ayliq_region(request):
    today = timezone.localdate()
    first_day_of_month = today.replace(day=1)

    # Digər bölgələr
    diger_region = Region.objects.filter(region_type="Digər")
    all_drug = Medical.objects.all()

    # RecipeDrug məlumatları
    drugs_data = (
        RecipeDrug.objects
        .filter(recipe__region__in=diger_region)
        .values("recipe__region__region_name", "drug__med_name", "recipe__date")
        .annotate(total=Sum("number"))
    )

    region_drug_counts_daily = {}
    region_drug_counts_monthly = {}
    region_daily_totals = {}
    region_monthly_totals = {}

    for region in diger_region:
        region_drug_counts_daily[region.region_name] = {}
        region_drug_counts_monthly[region.region_name] = {}
        daily_total = Decimal(0)
        monthly_total = Decimal(0)

        for drug in all_drug:
            daily = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and item["recipe__date"] == today
            )
            monthly = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and first_day_of_month <= item["recipe__date"] <= today
            )

            region_drug_counts_daily[region.region_name][drug.med_name] = daily
            region_drug_counts_monthly[region.region_name][drug.med_name] = monthly
            daily_total += daily
            monthly_total += monthly

        region_daily_totals[region.region_name] = daily_total
        region_monthly_totals[region.region_name] = monthly_total

    # Aylıq qeydiyyata görə azalan sırayla sort
    diger_region = sorted(
        diger_region,
        key=lambda r: region_monthly_totals.get(r.region_name, 0),
        reverse=True
    )

    # Excel faylı yarat
    wb = Workbook()
    ws = wb.active
    ws.title = "Aylıq Region Qeydiyyat"

     # Stil tərifləri
    bold_font = Font(bold=True, name="Calibri", size=12)
    calibri_font = Font(name="Calibri", size=11)
    bottom_alignment = Alignment(horizontal="center", vertical="bottom", text_rotation= 90 )
    center_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), 
        right=Side(style="thin"), 
        top=Side(style="thin"), 
        bottom=Side(style="thin")
    )
    medium_border = Border(
        left=Side(style="medium"),
        right=Side(style="medium"),
        top=Side(style="medium"),
        bottom=Side(style="medium")
    )
    header_fill = PatternFill(start_color="8ab1e3", end_color="8ab1e3", fill_type="solid")


    # Yuxarıda tarix
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(all_drug)+3)
    cell = ws.cell(row=1, column=1)
    cell.value = f"Tarix: {today}"
    cell.font = bold_font
    cell.alignment = center_alignment


    # Header
    headers = ["Bölgə"] + [drug.med_name for drug in all_drug] + ["Gündəlik Qeydiyyat", "Aylıq Qeydiyyat"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)  # Header 3-cü sətirdə
        cell.value = header
        cell.font = bold_font
        cell.alignment = bottom_alignment 
        cell.border = thin_border
        cell.fill = header_fill
        if col_num == 1 or col_num > len(all_drug):
            cell.fill = header_fill

    # Məzmun
    for row_num, region in enumerate(diger_region, start=4):
        # Region adı bold və çərçivəli
        cell = ws.cell(row=row_num, column=1)
        cell.value = region.region_name
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.fill = header_fill

        cell.border = thin_border

        # Dərmanlar
        for col_num, drug in enumerate(all_drug, start=2):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = region_drug_counts_daily[region.region_name][drug.med_name]
            cell.font = calibri_font
            cell.alignment = center_alignment

            cell.border = thin_border

        # Günlük və aylıq cəmlər - fonlu, bold, böyük
        for i, value in enumerate([region_daily_totals[region.region_name], region_monthly_totals[region.region_name]], start=len(all_drug)+2):
            cell = ws.cell(row=row_num, column=i)
            cell.value = value
            cell.font = bold_font
            cell.alignment = center_alignment

            cell.border = thin_border
            cell.fill = header_fill

    # Aşağıda cəm
    total_row = len(diger_region) + 3
    ws.cell(row=total_row, column=1).value = "Cəm"
    ws.cell(row=total_row, column=1).font = bold_font
    ws.cell(row=total_row, column=1).alignment = center_alignment
    ws.cell(row=total_row, column=1).border = thin_border
    ws.cell(row=total_row, column=1).fill = header_fill

    for col_num, drug in enumerate(all_drug, start=2):
        cell = ws.cell(row=total_row, column=col_num)
        cell.value = sum(region_drug_counts_daily[reg.region_name][drug.med_name] for reg in diger_region)
        cell.font = calibri_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill
        cell.font = bold_font

    # Günlük və aylıq toplamlar
    for i, value in enumerate([sum(region_daily_totals.values()), sum(region_monthly_totals.values())], start=len(all_drug)+2):
        cell = ws.cell(row=total_row, column=i)
        cell.value = value
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Aylıq Region Qeydiyyat - {today}.xlsx"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    wb.save(response)
    return response



def export_excel_ayliq_baki(request):
    today = timezone.localdate()
    first_day_of_month = today.replace(day=1)

    # Digər bölgələr
    baku_region = Region.objects.filter(region_type="Bakı")
    all_drug = Medical.objects.all()

    # RecipeDrug məlumatları
    drugs_data = (
        RecipeDrug.objects
        .filter(recipe__region__in=baku_region)
        .values("recipe__region__region_name", "drug__med_name", "recipe__date")
        .annotate(total=Sum("number"))
    )

    region_drug_counts_daily = {}
    region_drug_counts_monthly = {}
    region_daily_totals = {}
    region_monthly_totals = {}

    for region in baku_region:
        region_drug_counts_daily[region.region_name] = {}
        region_drug_counts_monthly[region.region_name] = {}
        daily_total = Decimal(0)
        monthly_total = Decimal(0)

        for drug in all_drug:
            daily = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and item["recipe__date"] == today
            )
            monthly = sum(
                item["total"]
                for item in drugs_data
                if item["recipe__region__region_name"] == region.region_name
                and item["drug__med_name"] == drug.med_name
                and first_day_of_month <= item["recipe__date"] <= today
            )

            region_drug_counts_daily[region.region_name][drug.med_name] = daily
            region_drug_counts_monthly[region.region_name][drug.med_name] = monthly
            daily_total += daily
            monthly_total += monthly

        region_daily_totals[region.region_name] = daily_total
        region_monthly_totals[region.region_name] = monthly_total

    # Aylıq qeydiyyata görə azalan sırayla sort
    baku_region = sorted(
        baku_region,
        key=lambda r: region_monthly_totals.get(r.region_name, 0),
        reverse=True
    )

    # Excel faylı yarat
    wb = Workbook()
    ws = wb.active
    ws.title = "Region Qeydiyyat"

     # Stil tərifləri
    bold_font = Font(bold=True, name="Calibri", size=12)
    calibri_font = Font(name="Calibri", size=11)
    bottom_alignment = Alignment(horizontal="center", vertical="bottom", text_rotation= 90 )
    center_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), 
        right=Side(style="thin"), 
        top=Side(style="thin"), 
        bottom=Side(style="thin")
    )
    medium_border = Border(
        left=Side(style="medium"),
        right=Side(style="medium"),
        top=Side(style="medium"),
        bottom=Side(style="medium")
    )
    header_fill = PatternFill(start_color="8ab1e3", end_color="8ab1e3", fill_type="solid")


    # Yuxarıda tarix
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(all_drug)+3)
    cell = ws.cell(row=1, column=1)
    cell.value = f"Tarix: {today}"
    cell.font = bold_font
    cell.alignment = center_alignment


    # Header
    headers = ["Bölgə"] + [drug.med_name for drug in all_drug] + ["Gündəlik Qeydiyyat", "Aylıq Qeydiyyat"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)  # Header 3-cü sətirdə
        cell.value = header
        cell.font = bold_font
        cell.alignment = bottom_alignment 
        cell.border = thin_border
        cell.fill = header_fill
        if col_num == 1 or col_num > len(all_drug):
            cell.fill = header_fill

    # Məzmun
    for row_num, region in enumerate(baku_region, start=4):
        # Region adı bold və çərçivəli
        cell = ws.cell(row=row_num, column=1)
        cell.value = region.region_name
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.fill = header_fill

        cell.border = thin_border

        # Dərmanlar
        for col_num, drug in enumerate(all_drug, start=2):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = region_drug_counts_daily[region.region_name][drug.med_name]
            cell.font = calibri_font
            cell.alignment = center_alignment

            cell.border = thin_border

        # Günlük və aylıq cəmlər - fonlu, bold, böyük
        for i, value in enumerate([region_daily_totals[region.region_name], region_monthly_totals[region.region_name]], start=len(all_drug)+2):
            cell = ws.cell(row=row_num, column=i)
            cell.value = value
            cell.font = bold_font
            cell.alignment = center_alignment

            cell.border = thin_border
            cell.fill = header_fill

    # Aşağıda cəm
    total_row = len(baku_region) + 3
    ws.cell(row=total_row, column=1).value = "Cəm"
    ws.cell(row=total_row, column=1).font = bold_font
    ws.cell(row=total_row, column=1).alignment = center_alignment
    ws.cell(row=total_row, column=1).border = thin_border
    ws.cell(row=total_row, column=1).fill = header_fill

    for col_num, drug in enumerate(all_drug, start=2):
        cell = ws.cell(row=total_row, column=col_num)
        cell.value = sum(region_drug_counts_daily[reg.region_name][drug.med_name] for reg in baku_region)
        cell.font = calibri_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill
        cell.font = bold_font

    # Günlük və aylıq toplamlar
    for i, value in enumerate([sum(region_daily_totals.values()), sum(region_monthly_totals.values())], start=len(all_drug)+2):
        cell = ws.cell(row=total_row, column=i)
        cell.value = value
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill
        cell.font = bold_font

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Aylıq Bakı Qeydiyyat - {today}.xlsx"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    wb.save(response)
    return response

 
# Aylıq və günlük Excel Faylı Çıxarışı son