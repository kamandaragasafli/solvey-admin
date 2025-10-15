
from django.urls import path
from core import views



urlpatterns = [
    
    path("admin",views.index,name='index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='user_logout'),

    path('region-drug-data/other/', views.region_drug_data_other, name='region-drug-data-other'),
    path('region-drug-data/baku/', views.region_drug_data_baku, name='region-drug-data-baku'),

    path('export-excel-region/', views.export_excel_ayliq_region, name='export_excel_ayliq_region'),
    path('export-excel-bakı/', views.export_excel_ayliq_baki, name='export_excel_ayliq_baki'),

]
