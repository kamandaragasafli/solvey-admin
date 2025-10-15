from django.urls import path
from doctors import views



urlpatterns = [
    path("list/",views.doctors_list, name ="doctors"),
    path("dell_al/",views.del_all, name ="dell"),
    path("add/",views.create_doctor, name ="add-doctor"),
    path('details/update/<int:pk>/', views.update_doctor, name='update-doctor'),

    path('ajax/get-hospitals/', views.get_hospitals_by_region, name='get-hospitals'),
    path('ajax/get-cities/', views.get_cities_by_region, name='get-cities'),
    path('ajax/load-cities-hospitals/', views.load_cities_hospitals, name='ajax-load-cities-hospitals'),
    path('payments/delete/<int:id>/', views.del_payments, name='del_payments'),
    

    path("details/<str:doctor_id>/",views.doctor_detail, name ="doctor_detail"),
    path('add-data/', views.create_recipe, name='create_recipe'),
    path('add-recipe-data/', views.create_detail_recipe, name='create_detail_recipe'),
    path('remove-data/<int:id>/',views.del_recipe, name='del_recipe'),
    path('details/update-data/<int:id>/', views.update_recipe, name='update_recipe'),

    path('real-sales/', views.create_real_sales, name='create_real_sales'),
    path('razilasma/', views.create_razilasma, name='razilasma'),
    path('datasiya/', views.create_datasiya, name='datasiya'),
    path('finance_view/', views.finance_view, name='finance_view'),
    path('ajax/doctors/', views.ajax_doctors_by_region, name='ajax_doctors_by_region'),
    path('ajax/add-data/', views.ajax_doctors_by_region, name='ajax_doctors_by_region'),
    path('ajax/region-data/', views.ajax_region_data, name='ajax_region_data'),
    path('drug-data/', views.data_list, name='data_list'),
    path('export-region-excel/', views.export_region_excel, name='export_region_excel'),

    path('reg/',views.get_region, name='test'),
    path('regs/<int:region_id>', views.region_report, name='region_report')




]