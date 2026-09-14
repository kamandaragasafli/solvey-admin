from django.contrib import admin

from .models import Depo, Drug, SalesRecord, UploadedReport


@admin.register(Depo)
class DepoAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(UploadedReport)
class UploadedReportAdmin(admin.ModelAdmin):
    list_display = ("depo", "report_date", "uploaded_at", "file")
    list_filter = ("depo", "report_date")
    date_hierarchy = "report_date"
    readonly_fields = ("uploaded_at",)


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ("report", "drug", "city", "quantity")
    list_filter = ("report", "city")
    search_fields = ("drug__name", "city")
