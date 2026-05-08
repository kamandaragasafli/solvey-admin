
from django.urls import path
from core import views



urlpatterns = [
    
    path("admin",views.index,name='index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='user_logout'),

    path('region-drug-data/other/', views.region_drug_data_other, name='region-drug-data-other'),
    path('region-drug-data/baku/', views.region_drug_data_baku, name='region-drug-data-baku'),
    path('region-sales-data/other/', views.region_sales_data_other, name='region-sales-data-other'),
    path('region-sales-data/baku/', views.region_sales_data_baku, name='region-sales-data-baku'),

    path('export-excel-region/', views.export_excel_ayliq_region, name='export_excel_ayliq_region'),
    path(
        "export-excel-seher/",
        views.export_excel_ayliq_seher,
        name="export_excel_ayliq_seher",
    ),
    path('export-excel-bakı/', views.export_excel_ayliq_baki, name='export_excel_ayliq_baki'),
    path('api/openai/chat/', views.openai_chat, name='openai_chat'),
    path('ai-assistant/', views.ai_assistant_page, name='ai-assistant'),
    path('api/ai/analyze-file/', views.ai_analyze_file_api, name='ai_analyze_file_api'),
    path('api/ai/web-search/', views.ai_web_search_api, name='ai_web_search_api'),
    path('api/ai/confirm-action/', views.ai_confirm_action_api, name='ai_confirm_action_api'),
    path('api/ai/cancel-action/', views.ai_cancel_action_api, name='ai_cancel_action_api'),
    path('region-modal-monthly-data/', views.region_modal_monthly_data, name='region-modal-monthly-data'),
    path('baku-modal-monthly-data/', views.baku_modal_monthly_data, name='baku-modal-monthly-data'),

]
