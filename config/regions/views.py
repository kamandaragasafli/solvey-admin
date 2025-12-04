from django.shortcuts import render, redirect,get_object_or_404
from .models import Region, Hospital, City
from django.contrib import messages
from doctors.models import Doctors

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