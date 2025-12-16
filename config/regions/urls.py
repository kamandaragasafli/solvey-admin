from django.urls import path
from regions import views


urlpatterns = [
    path("area/",views.region_list, name="region_list"),
    path("area/<int:region_id>/", views.region_detail, name="region_detail"),
    path("add/",views.create_region, name="add-region"),

    path("hospital/",views.hospital_list, name="hospital_list"),
    path("hospital/add/",views.create_hospital, name="add-hospital"),
    path("cities/", views.city_list, name="city_list"),
    path("cities/add/", views.create_city, name="add-city"),
]