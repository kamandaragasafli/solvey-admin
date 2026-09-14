from django.urls import path

from . import views

app_name = "depo_sales"

urlpatterns = [
    path("", views.upload_report, name="upload"),
    path("hesabat/<int:report_id>/", views.report_detail, name="report_detail"),
]
