from django.urls import path

from .views import (
    admin_panel_view,
    ajax_compat_view,
    excel_export_view,
    get_hekimler_api,
    get_rayonlar_api,
    hesabat_view,
    login_view,
    logout_view,
    yeni_vizit_view,
    bolge_stat_view,
)

app_name = 'vizit'

urlpatterns = [
    path('', yeni_vizit_view, name='index'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin_panel_view, name='admin_panel'),
    path('api/rayonlar/', get_rayonlar_api, name='api_rayonlar'),
    path('api/hekimler/', get_hekimler_api, name='api_hekimler'),
    # ajax.php uyğunluğu (?action=rayonlar|hekimler)
    path('ajax/', ajax_compat_view, name='ajax'),
    path('hesabat/', hesabat_view, name='hesabat'),
    path('export/', excel_export_view, name='export_excel'),
    path('bolge-statistika/', bolge_stat_view, name='bolge_statistika'),
]
