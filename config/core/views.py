
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
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests
import os



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

            baki_region_drug_counts[region.region_name][drug.med_name] = monthly
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
    bottom_alignment = Alignment(horizontal="center", vertical="bottom", text_rotation=90)
    center_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    header_fill = PatternFill(start_color="8ab1e3", end_color="8ab1e3", fill_type="solid")

    # Yuxarıda tarix
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(all_drug) + 3)
    cell = ws.cell(row=1, column=1)
    cell.value = f"Tarix: {today}"
    cell.font = bold_font
    cell.alignment = center_alignment

    # Header
    headers = ["№", "Bölgə"] + [drug.med_name for drug in all_drug] + ["Gündəlik Qeydiyyat", "Aylıq Qeydiyyat"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.font = bold_font
        cell.alignment = bottom_alignment
        cell.border = thin_border
        cell.fill = header_fill

    # Məzmun
    for index, region in enumerate(diger_region, start=1):
        row_num = index + 3  # 3-cü sətirdən sonra yazmağa başlayırıq

        # № sütunu
        cell = ws.cell(row=row_num, column=1)
        cell.value = index
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

        # Bölgə sütunu
        cell = ws.cell(row=row_num, column=2)
        cell.value = region.region_name
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

        # Dərmanlar
        for col_num, drug in enumerate(all_drug, start=3):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = region_drug_counts_daily[region.region_name][drug.med_name]
            cell.font = calibri_font
            cell.alignment = center_alignment
            cell.border = thin_border

        # Günlük və aylıq cəmlər
        for i, value in enumerate([region_daily_totals[region.region_name],
                                region_monthly_totals[region.region_name]],
                                start=len(all_drug) + 3):
            cell = ws.cell(row=row_num, column=i)
            cell.value = value
            cell.font = bold_font
            cell.alignment = center_alignment
            cell.border = thin_border
            cell.fill = header_fill

    # Aşağıda cəm
    total_row = len(diger_region) + 4

    cell = ws.cell(row=total_row, column=2)
    cell.value = "Cəm"
    cell.font = Font(bold=True, name="Calibri", color="FFFFFF", size=12)
    cell.alignment = center_alignment
    cell.border = thin_border
    cell.fill = PatternFill(start_color="1f4e78", end_color="1f4e78", fill_type="solid")


    for col_num, drug in enumerate(all_drug, start=3):
        cell = ws.cell(row=total_row, column=col_num)
        cell.value = sum(region_drug_counts_daily[reg.region_name][drug.med_name] for reg in diger_region)
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

    # Günlük və aylıq cəmlərin ümumisi
    for i, value in enumerate([sum(region_daily_totals.values()), sum(region_monthly_totals.values())],
                            start=len(all_drug) + 3):
        cell = ws.cell(row=total_row, column=i)
        cell.value = value
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

    # Excel faylını göndər
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


    # Header (artıq yalnız aylıq məlumat göstəririk)
    headers = ["Bölgə"] + [drug.med_name for drug in all_drug] + ["Aylıq Qeydiyyat"]
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

        # Dərmanlar - AYLIQ cəmlər
        for col_num, drug in enumerate(all_drug, start=2):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = region_drug_counts_monthly[region.region_name][drug.med_name]
            cell.font = calibri_font
            cell.alignment = center_alignment

            cell.border = thin_border

        # Yalnız AYLQ cəm - fonlu, bold, böyük
        total_col_index = len(all_drug) + 2
        cell = ws.cell(row=row_num, column=total_col_index)
        cell.value = region_monthly_totals[region.region_name]
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
        cell.value = sum(region_drug_counts_monthly[reg.region_name][drug.med_name] for reg in baku_region)
        cell.font = bold_font
        cell.alignment = center_alignment
        cell.border = thin_border
        cell.fill = header_fill

    # Yalnız aylıq ümumi toplam
    total_col_index = len(all_drug) + 2
    cell = ws.cell(row=total_row, column=total_col_index)
    cell.value = sum(region_monthly_totals.values())
    cell.font = bold_font
    cell.alignment = center_alignment
    cell.border = thin_border
    cell.fill = header_fill

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Aylıq Bakı Qeydiyyat - {today}.xlsx"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
    wb.save(response)
    return response

 
  # Aylıq və günlük Excel Faylı Çıxarışı son

# OpenAI Chat API Endpoint with Database Query Support
@csrf_exempt
@require_http_methods(["POST"])
def openai_chat(request):
    """OpenAI API integration for chat assistant with database query capabilities"""
    try:
        from core.ai_queries import FUNCTIONS, FUNCTION_MAP
        
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        model = data.get('model', 'gpt-3.5-turbo')
        conversation_history = data.get('history', [])  # For maintaining context
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get OpenAI API key from settings
        from django.conf import settings
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        
        if not api_key:
            return JsonResponse({
                'reply': 'Üzr istəyirəm, AI xidməti hazırda mövcud deyil. Zəhmət olmasa sistem administratoru ilə əlaqə saxlayın.'
            }, status=503)
        
        # Prepare messages with conversation history
        messages = [
            {
                'role': 'system',
                'content': '''Sən Solvey tibbi şirkətinin admin paneli üçün köməkçi AI-sən.
Azərbaycan dilində cavab ver. Qısa, dəqiq və faydalı cavablar ver.

Mütləq qayda:
- Verilənlər bazasından məlumat almaq üçün HƏMİŞƏ təqdim olunmuş funksiyalardan istifadə et.
- Heç vaxt özündən rəqəm, statistika və ya tarix UYDURMA, yalnız funksiyaların qaytardığı nəticələri istifadə et.
- Funksiya sıfır nəticə qaytaranda bunu aydın yaz: "Bu həkim üçün bu dövrdə məlumat tapılmadı."

Kontekst:
- İstifadəçi ardıcıl suallar verəndə əvvəlki mesajdakı həkim adını və tarixi yadında saxla.
- Məs: "Məmmədov Əsəd keçən ay nə qədər qeydiyyatı var?" + "noyabrda bəs?" → bu, eyni həkim üçün noyabr ayına aid sorğu deməkdir.
- "noyabrda bəs?", "bu ay necə?", "keçən ay nə qədər?" kimi qısa cümlələri HƏKİM ADI kimi yox, əvvəlki sualın davamı kimi şərh et.

Tarix şərhi:
- "keçən ay" → cari tarixdən əvvəlki ay kimi şərh et.
- "bu ay" → cari ay.
- "noyabrda" kimi ay adları veriləndə uyğun aya çevir.

Funksiya nümunələri:
- "Ən son əlavə olunan həkimləri göstər" → get_recent_doctors
- "Həkim statistikalarını göstər" → get_doctor_statistics
- "Bakı bölgəsinin həkimlərini göstər" → get_doctors_by_region
- "Vüsalə üçün bu ay neçə resept yazılıb?" → get_doctor_prescription_stats
- "Bağırova Könülün aylıq qeydiyyat aylarını göstər" → get_doctor_financial_details və ya əlavə aylıq hesabat funksiyası.

Cavab formatı:
- Mümkün qədər sadə saxla (ad + bölgə kimi), yalnız istifadəçi əlavə detal istəyəndə daha detallı məlumat ver.
'''
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history[-10:])  # Keep last 10 messages for context
        
        # Add current message
        messages.append({
            'role': 'user',
            'content': message
        })
        
        # Prepare the request to OpenAI API with function calling
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': messages,
            'functions': FUNCTIONS,
            'function_call': 'auto',  # Let the model decide when to call functions
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        # Make request to OpenAI API
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            message_obj = result['choices'][0]['message']
            
            # Check if the model wants to call a function
            if message_obj.get('function_call'):
                function_name = message_obj['function_call']['name']
                function_args = json.loads(message_obj['function_call']['arguments'])
                
                # Execute the function
                if function_name in FUNCTION_MAP:
                    function_result = FUNCTION_MAP[function_name](**function_args)
                    
                    # Add function result to conversation and get final response
                    messages.append(message_obj)  # Add assistant's function call request
                    messages.append({
                        'role': 'function',
                        'name': function_name,
                        'content': json.dumps(function_result, ensure_ascii=False)
                    })
                    
                    # Make second request to get the final answer
                    payload['messages'] = messages
                    response2 = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if response2.status_code == 200:
                        result2 = response2.json()
                        reply = result2['choices'][0]['message']['content']
                    else:
                        # If second request fails, format the function result directly
                        reply = format_function_result(function_name, function_result)
                else:
                    reply = 'Üzr istəyirəm, bu funksiya mövcud deyil.'
            else:
                # Direct response without function calling
                reply = message_obj['content']
            
            return JsonResponse({'reply': reply})
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('error', {}).get('message', 'Xəta baş verdi')
            return JsonResponse({
                'reply': f'Üzr istəyirəm, xəta baş verdi: {error_msg}'
            }, status=response.status_code)
            
    except requests.exceptions.Timeout:
        return JsonResponse({
            'reply': 'Üzr istəyirəm, sorğu zaman aşımına uğradı. Zəhmət olmasa yenidən cəhd edin.'
        }, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'reply': 'Üzr istəyirəm, bağlantı xətası baş verdi. Zəhmət olmasa yenidən cəhd edin.'
        }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'reply': f'Gözlənilməz xəta: {str(e)}'
        }, status=500)


def format_function_result(function_name, result):
    """Format function results for display"""
    if function_name == 'get_recent_doctors':
        if not result:
            return 'Ən son əlavə olunan həkim tapılmadı.'
        text = 'Ən son əlavə olunan həkimlər:\n\n'
        for i, doctor in enumerate(result, 1):
            text += f"{i}. {doctor['ad']}\n"
            text += f"   Bölgə: {doctor['bolge']}, Şəhər: {doctor['city']}\n"
            text += f"   Klinika: {doctor['klinika']}, İxtisas: {doctor['ixtisas']}\n"
            text += f"   Dərəcə: {doctor['derece']}, Tarix: {doctor['created_at']}\n\n"
        return text
    
    elif function_name == 'get_doctor_statistics':
        stats = result
        text = f"📊 Həkim Statistikaları:\n\n"
        text += f"Ümumi həkim sayı: {stats['total_doctors']}\n"
        text += f"Bu ay əlavə olunan: {stats['new_this_month']}\n\n"
        
        if stats['by_degree']:
            text += "Dərəcə üzrə:\n"
            for degree, count in stats['by_degree'].items():
                text += f"  - {degree}: {count}\n"
        
        if stats['by_region']:
            text += "\nBölgə üzrə (top 5):\n"
            sorted_regions = sorted(stats['by_region'].items(), key=lambda x: x[1], reverse=True)[:5]
            for region, count in sorted_regions:
                text += f"  - {region}: {count}\n"
        
        return text
    
    elif function_name == 'get_region_statistics':
        if not result:
            return 'Bölgə tapılmadı.'
        text = '📍 Bölgə Statistikaları:\n\n'
        for region in result:
            text += f"{region['region_name']} ({region['region_type']}):\n"
            text += f"  Həkim: {region['doctor_count']}, "
            text += f"Şəhər: {region['city_count']}, "
            text += f"Xəstəxana: {region['hospital_count']}\n\n"
        return text
    
    elif function_name == 'search_doctors':
        if not result:
            return 'Axtarışa uyğun həkim tapılmadı.'
        text = f'Axtarış nəticələri ({len(result)} həkim):\n\n'
        for i, doctor in enumerate(result, 1):
            # Daha sadə nəticə: yalnız ad və bölgə göstərək
            text += f"{i}. {doctor['ad']}\n"
            text += f"   Bölgə: {doctor['bolge']}\n\n"
        return text
    
    elif function_name == 'get_financial_summary':
        stats = result
        text = '💰 Maliyyə Ümumi Məlumatları:\n\n'
        text += f"Ümumi borc: {stats['total_debt']:.2f} ₼\n"
        text += f"Əvvəlki borc: {stats['total_previous_debt']:.2f} ₼\n"
        text += f"Borclu həkim sayı: {stats['doctors_with_debt']} / {stats['total_doctors']}\n"
        return text
    
    elif function_name == 'get_doctors_by_region':
        if not result:
            return 'Bu bölgədə həkim tapılmadı.'
        text = f'Bölgə həkimləri ({len(result)} həkim):\n\n'
        for i, doctor in enumerate(result, 1):
            # Sadə format: ad və bölgə kifayətdir, əlavə detallar soruşularsa göstərilər
            text += f"{i}. {doctor['ad']}\n"
            text += f"   Şəhər: {doctor['city']}, Klinika: {doctor['klinika']}\n\n"
        return text

    elif function_name == 'get_doctor_financial_details':
        if not result:
            return 'Bu ada uyğun həkim tapılmadı.'

        # Bir neçə həkim uyğun gələrsə, hamısını sadə siyahı kimi göstər
        if len(result) > 1:
            text = f'Axtarış nəticələri ({len(result)} həkim):\n\n'
            for i, doctor in enumerate(result, 1):
                text += f"{i}. {doctor['ad']}\n"
                text += f"   Bölgə: {doctor['bolge']}\n\n"
            text += "Zəhmət olmasa daha dəqiq ad və ya barkod qeyd edin ki, konkret həkim üçün tam maliyyə detallarını göstərə bilim."
            return text

        # Yalnız bir həkim varsa, detallı maliyyə məlumatları
        doctor = result[0]
        text = f"💳 Həkim üzrə maliyyə məlumatları: {doctor['ad']}\n\n"
        text += "Cari vəziyyət:\n"
        text += f"  - Əvvəlki borc: {doctor['previous_debt']:.2f} ₼\n"
        text += f"  - Cari borc: {doctor['borc']:.2f} ₼\n"
        text += f"  - Hesablanan miqdar: {doctor['hesablanan_miqdar']:.2f} ₼\n"
        text += f"  - Həkimdən silinən: {doctor['hekimden_silinen']:.2f} ₼\n"
        text += f"  - Datasiya: {doctor['datasiya']:.2f} ₼\n"
        text += f"  - Avans: {doctor['avans']:.2f} ₼\n"
        text += f"  - İnvestisiya: {doctor['investisiya']:.2f} ₼\n"
        text += f"  - Geri qaytarma: {doctor['geriqaytarma']:.2f} ₼\n"
        text += f"  - Yekun borc: {doctor['yekun_borc']:.2f} ₼\n\n"

        # Ödənişlər
        payments = doctor.get('payments', [])
        if payments:
            text += "Son ödənişlər:\n"
            for p in payments:
                text += f"  - {p['date']}: {p['payment_type']} - {p['pay']:.2f} ₼ ({p['region']})\n"
        else:
            text += "Son açıq ödəniş tapılmadı.\n"

        # Aylıq hesabatlar
        reports = doctor.get('monthly_reports', [])
        if reports:
            text += "\nSon aylıq hesabatlar:\n"
            for r in reports:
                text += f"  - {r['month']}: yekun borc {r['yekun_borc']:.2f} ₼, borc {r['borc']:.2f} ₼, avans {r['avans']:.2f} ₼, investisiya {r['investisiya']:.2f} ₼, geri qaytarma {r['geriqaytarma']:.2f} ₼\n"

        return text

    elif function_name == 'get_doctor_prescription_stats':
        # Həkim tapılmadıqda və ya xəta olduqda
        if not result.get('doctor_found'):
            return result.get('message', 'Bu ada uyğun həkim tapılmadı.')

        doctor = result['doctor']
        year = result.get('year')
        month = result.get('month')
        day = result.get('day')

        period_text = ''
        if year and month and day:
            period_text = f"{year}-{month:02d}-{day:02d} tarixi üçün"
        elif year and month:
            period_text = f"{year}-{month:02d} ayı üçün"
        elif year:
            period_text = f"{year}-ci il üçün"
        else:
            period_text = "seçilən dövr üçün"

        text = f"🧾 {doctor['ad']} həkimin {period_text} resept statistikası:\n\n"
        text += f"  - Ümumi resept sayı: {result['total_recipes']}\n"
        text += f"  - Ümumi dərman sayı (cəmi ədəd): {result['total_drug_count']:.1f}\n\n"

        drugs = result.get('drugs', [])
        if drugs:
            text += "Ən çox yazılan dərmanlar:\n"
            for d in drugs[:10]:
                text += f"  - {d['name']}: {d['count']:.1f} ədəd\n"
        else:
            text += "Bu dövr üçün resept və dərman məlumatı tapılmadı.\n"

        return text

    return str(result)