from django.shortcuts import render, redirect,get_object_or_404
from .models import Region, Hospital, City
from django.contrib import messages
from doctors.models import Doctors
from datetime import date, datetime
from django.utils import timezone

# Create your views here.
def region_list(request):
    regions = Region.objects.all().order_by("region_type")
    baki_sayi = Region.objects.filter(region_type='Bakı').count()
    diger_sayi = Region.objects.filter(region_type='Digər').count()
    
    context ={
        "regions": regions,
        "baki_sayi": baki_sayi,
        "diger_sayi": diger_sayi,
        'region_count': Region.objects.count(),
        'doctor_count': Doctors.objects.count(),
        'city_count': City.objects.count(),
        'hospital_count': Hospital.objects.count(),
    }
    return render(request, "regions.html", context)

def hospital_list(request):
    hospitals = Hospital.objects.all().order_by("region_net")
    regions = Region.objects.all().order_by("region_name")
    context ={
        "hospitals": hospitals,
        "regions": regions,
    }
    return render(request, "hospitals.html", context)


def city_list(request):
    """Şəhərlərin sadə siyahı səhifəsi"""
    cities = City.objects.select_related("region").order_by("region__region_name", "city_name")
    regions = Region.objects.all().order_by("region_name")
    context = {
        "cities": cities,
        "regions": regions,
    }
    return render(request, "cities.html", context)


def create_city(request):
    """Şəhər əlavə et"""
    if request.method == "POST":
        region_id = request.POST.get("region_id")
        city_name = request.POST.get("city_name")

        if not region_id or not city_name:
            messages.error(request, "Zəhmət olmasa bütün sahələri doldurun.")
            return redirect("city_list")

        selected_region = get_object_or_404(Region, id=region_id)

        # Eyni bölgədə eyni şəhər adı olub-olmadığını yoxla
        if City.objects.filter(region=selected_region, city_name=city_name).exists():
            messages.warning(request, f"Bu bölgədə '{city_name}' adlı şəhər artıq mövcuddur.")
            return redirect("city_list")

        City.objects.create(region=selected_region, city_name=city_name)
        messages.success(request, "Şəhər uğurla əlavə edildi.")
        return redirect("city_list")

    return redirect("city_list")




def create_region(request):
    if request.method == "POST":
        region_name = request.POST.get("region_name")

        if Region.objects.filter(region_name__iexact=region_name).exists():
            messages.warning(request, "Bu adda bölgə artıq mövcuddur.")
            return redirect("add-region")
        
        Region.objects.create(region_name=region_name)
        return redirect("region_list")
    return render(request, "crud/add-region.html")



def create_hospital(request):
    region = Region.objects.all()
    if request.method == "POST":
        hospital_name = request.POST.get("hospital_name")
        region_net = request.POST.get("region_net")

        selected_region = get_object_or_404(Region, id=region_net)
        
        Hospital.objects.create(hospital_name=hospital_name, region_net=selected_region)
        return redirect("hospital_list")
    context = {
        "region": region,
    }
    return render(request, "crud/add-hospital.html", context)


def region_detail(request, region_id):
    """Region detallı məlumat səhifəsi"""
    region = get_object_or_404(Region, id=region_id)
    
    # Region ilə əlaqəli məlumatlar
    doctors = Doctors.objects.filter(bolge=region).select_related('city', 'klinika').order_by('ad')
    cities = City.objects.filter(region=region).order_by('city_name')
    hospitals = Hospital.objects.filter(region_net=region).select_related('city').order_by('hospital_name')
    
    # Statistika
    doctor_count = doctors.count()
    city_count = cities.count()
    hospital_count = hospitals.count()
    
    # Həkimlər üzrə statistika
    doctors_by_specialty = {}
    doctors_by_degree = {}
    for doctor in doctors:
        specialty = doctor.get_ixtisas_display()
        degree = doctor.get_derece_display()
        doctors_by_specialty[specialty] = doctors_by_specialty.get(specialty, 0) + 1
        doctors_by_degree[degree] = doctors_by_degree.get(degree, 0) + 1
    
    # Bu ay əlavə olunan yeni həkimlər (son 5-i)
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # Yeni həkimləri tapmaq - created_at field yoxdursa, boş qaytar
    new_doctors = doctors.none()
    try:
        # Django model field-lərini yoxla
        model_fields = [f.name for f in Doctors._meta.get_fields()]
        if 'created_at' in model_fields:
            new_doctors = doctors.filter(created_at__year=current_year, created_at__month=current_month).order_by('-created_at')[:5]
        elif 'date_created' in model_fields:
            new_doctors = doctors.filter(date_created__year=current_year, date_created__month=current_month).order_by('-date_created')[:5]
        elif 'created' in model_fields:
            new_doctors = doctors.filter(created__year=current_year, created__month=current_month).order_by('-created')[:5]
    except Exception as e:
        # Field yoxdursa, boş qaytar
        new_doctors = doctors.none()
    
    new_doctors_list = list(new_doctors)
    new_doctors_count = len(new_doctors_list)
    
    context = {
        'region': region,
        'doctors': doctors,
        'cities': cities,
        'hospitals': hospitals,
        'doctor_count': doctor_count,
        'city_count': city_count,
        'hospital_count': hospital_count,
        'doctors_by_specialty': doctors_by_specialty,
        'doctors_by_degree': doctors_by_degree,
        'new_doctors_count': new_doctors_count,
        'new_doctors': new_doctors_list,
    }
    
    return render(request, 'regions/region_detail.html', context)