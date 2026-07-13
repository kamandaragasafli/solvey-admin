from django.urls import path
from . import views


app_name = 'aptek'

urlpatterns = [
    path('', views.aptek_list, name='anbar_dashboard'),
    path('export/', views.export_ledger_excel, name='export_ledger'),
    path('evvele-qaliq/', views.evvele_qaliq, name='evvele_qaliq'),
    path('anbara-elave/', views.anbara_elave_form, name='anbara_elave_form'),
    path('anbara-elave/siyahi/', views.anbara_elave_siyahi, name='anbara_elave_siyahi'),
    path('geri-qaytarma/', views.geri_qaytarma, name='geri_qaytarma'),
    path('qaimeler/', views.qaimeler, name='qaimeler'),
    path('qaimeler/<int:pk>/sil/', views.qaime_delete, name='qaime_delete'),
    path('aptekler/', views.aptekler, name='aptekler'),
    path('aptekler/<int:pk>/', views.aptek_detail, name='aptek_detail'),
    path('istisnalar/', views.istisnalar, name='istisnalar'),
]
