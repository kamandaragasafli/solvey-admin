from django.urls import path
from regions import views


urlpatterns = [
    path("area/",views.region_list, name="region_list"),
    path("add/",views.create_region, name="add-region"),

    path("hospital/",views.hospital_list, name="hospital_list"),
    path("hospital/add/",views.create_hospital, name="add-hospital"),
]