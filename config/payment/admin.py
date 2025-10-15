from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import MonthlyDoctorReport, Sale, Payment_doctor, Financial_document




admin.site.register(Sale)

admin.site.register(Financial_document)

admin.site.register(Payment_doctor)

class MonthFilter(admin.SimpleListFilter):
    title = _('Ay')  # Filterin başlığı
    parameter_name = 'month'  # URL parametri adı

    def lookups(self, request, model_admin):
        # Ayların siyahısını qaytarır (qiymət, ad)
        return [
            (1, _('Yanvar')),
            (2, _('Fevral')),
            (3, _('Mart')),
            (4, _('Aprel')),
            (5, _('May')),
            (6, _('İyun')),
            (7, _('İyul')),
            (8, _('Avqust')),
            (9, _('Sentyabr')),
            (10, _('Oktyabr')),
            (11, _('Noyabr')),
            (12, _('Dekabr')),
        ]

    def queryset(self, request, queryset):
        if self.value():
            # Seçilmiş ay üçün filterlə
            return queryset.filter(report_month__month=self.value())
        return queryset

class YearFilter(admin.SimpleListFilter):
    title = _('İl')  # Filterin başlığı
    parameter_name = 'year'  # URL parametri adı

    def lookups(self, request, model_admin):
        # Mövcud illəri gətir
        years = MonthlyDoctorReport.objects.dates('report_month', 'year')
        return [(year.year, year.year) for year in years]

    def queryset(self, request, queryset):
        if self.value():
            # Seçilmiş il üçün filterlə
            return queryset.filter(report_month__year=self.value())
        return queryset

class MonthlyDoctorReportAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'region', 'report_month', 'yekun_borc', 'hesablanan_miqdar', 'hekimden_silinen', 'investisiya', 'avans',  'recipe_total_drugs',)
    
    # Xüsusi filterləri əlavə et
    list_filter = (
        'region',  # Bölgə filteri
        MonthFilter,  # Xüsusi ay filteri
        YearFilter,  # Xüsusi il filteri
        'doctor',  # Həkim filteri
    )
    
    search_fields = ('doctor__ad', 'region__region_name')
    date_hierarchy = 'report_month'
    list_per_page = 50

admin.site.register(MonthlyDoctorReport, MonthlyDoctorReportAdmin)