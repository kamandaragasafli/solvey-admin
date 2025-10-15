
from django.urls import path
from export import views



urlpatterns = [
    path("settings/", views.admin_view, name="admin"),
    path("import-drug/", views.import_drug_from_excel, name="import_drug"),
    path("import/", views.imports, name="import"),
    path("import-region/", views.import_region_from_excel, name="import_region"),
    path("import-hospital/", views.import_hospital_from_excel, name="import_hospital"),
    path("import-doctors/", views.import_doctors_from_excel, name="import_doctors"),
    path("import_debts/", views.import_debts_from_excel, name="import_debts"),
    path("import-recipes/",views.import_recipes_from_excel, name="import_recipes"),
    path("import-finans/",views.import_avn_inv_from_excel, name="import_finance"),
    path('create-backup/', views.create_backup, name='create_backup'),
    path('restore-backup/<int:backup_id>/', views.restore_backup, name='restore_backup'),
    path('admin-recipe-del/<int:id>/', views.admin_recipes_delete, name='admin_recipe_del'),
    path('borc-sifirla/', views.borc_sifirla, name='borc_sifirla'),
    path("yeni-istifadeci/", views.yeni_istifadeci_elave_et, name="yeni_istifadeci"),
    path("delete-user/<int:user_id>/", views.delete_user, name="delete_user"),




    


]
