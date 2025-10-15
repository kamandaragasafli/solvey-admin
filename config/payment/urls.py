from django.urls import path
from payment import views
from doctors.views import del_payments



urlpatterns = [
    path("add-pay-dr/", views.add_pay_dr, name="add-pay-dr"),
    path("add-pay-dr/<int:region_id>/", views.add_pay_dr, name="add-pay-dr-region"),
    path("document-add/", views.document_add, name="document_add"),
     path('financial-documents/', views.financial_documents, name='financial_documents'),
    path("ajax/get-doctors/", views.get_doctors_by_region, name="get-doctors-by-region"),
    path('report/', views.report_list, name='report'),
    path('ajax/region-report/', views.ajax_region_report, name='ajax_region_report'),
    path('export-region-report-excel/', views.export_region_report_excel, name='export_region_report_excel'),
    path("addsells/",views.create_sale, name ="add-sell"),
    path("sales/",views.sales, name ="sales"),
    path('hesabat-bagla/', views.hesabat_bagla, name='hesabat_bagla'),


    path('closed-accounts/', views.kohne_hesabat, name='closed_accounts'),
    path('ajax/closed-accounts/', views.kohne_region_ajax, name='ajax_closed_accounts'),
    # path("export-region-report-excel/", views.export_excel, name="export_region_excel"), 


]