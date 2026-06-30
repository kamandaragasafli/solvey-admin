from django.urls import path
from .views import login_user, hesablamalar, admin_page, logout_user, reports_list, report_detail_json, report_export_excel

app_name = 'calculate'

urlpatterns = [
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
    path('calculate/', hesablamalar, name='hesablamalar'),
    path('report/', reports_list, name='reports_list'),
    path('reports/<int:report_id>/detail/', report_detail_json, name='report_detail_json'),
    path('reports/<int:report_id>/export-excel/', report_export_excel, name='report_export_excel'),
    path('admin/', admin_page, name='admin_page'),
]