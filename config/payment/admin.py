from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import MonthlyDoctorReport, Sale, Payment_doctor, Financial_document


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'colored_region', 'colored_drug', 'colored_quantity', 'colored_sale_date')
    list_filter = ('region', 'sale_date')
    search_fields = ('region__region_name', 'drug__med_name')
    date_hierarchy = 'sale_date'
    ordering = ('-sale_date', 'region__region_name', 'drug__med_name')
    list_per_page = 50
    list_select_related = ('region', 'drug')

    def colored_region(self, obj):
        return format_html('<span style="color:#60a5fa; font-weight:bold;">{}</span>', obj.region.region_name)
    colored_region.short_description = 'Bölgə'
    colored_region.admin_order_field = 'region__region_name'

    def colored_drug(self, obj):
        return format_html('<span style="color:#f59e0b; font-weight:bold;">{}</span>', obj.drug.med_name)
    colored_drug.short_description = 'Dərman'
    colored_drug.admin_order_field = 'drug__med_name'

    def colored_quantity(self, obj):
        return format_html('<span style="color:#34d399; font-weight:bold;">{}</span>', obj.quantity)
    colored_quantity.short_description = 'Miqdar'
    colored_quantity.admin_order_field = 'quantity'

    def colored_sale_date(self, obj):
        return format_html('<span style="color:#94a3b8;">{}</span>', obj.sale_date.strftime('%d.%m.%Y'))
    colored_sale_date.short_description = 'Satış tarixi'
    colored_sale_date.admin_order_field = 'sale_date'

admin.site.register(Financial_document)

@admin.register(Payment_doctor)
class PaymentDoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'payment_type', 'pay', 'date')
    list_filter = ('payment_type', 'doctor__bolge')  
    search_fields = ('doctor__ad', 'doctor__barkod')  
    ordering = ('-date',) 
    list_per_page = 50  
    list_editable = ('payment_type', 'pay',)
    list_select_related = ('doctor',)


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
    list_display = (
        'colored_doctor',
        'colored_region',
        'colored_report_month',
        'colored_yekun_borc',
        'hesablanan_miqdar',
        'hekimden_silinen',
        'investisiya',
        'avans',
        'recipe_total_drugs',
    )
    list_filter = (
        'region',
        MonthFilter,
        YearFilter,
        'doctor',
    )
    search_fields = (
        'doctor__ad',
        'region__region_name',
        'doctor__barkod',
    )
    date_hierarchy = 'report_month'
    list_per_page = 50
    ordering = ('-report_month', 'doctor__ad')
    list_select_related = ('doctor', 'region')

    def colored_doctor(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="color:#60a5fa; font-weight:bold;">{}</span>',
            obj.doctor.ad
        )
    colored_doctor.short_description = 'Həkim'
    colored_doctor.admin_order_field = 'doctor__ad'

    def colored_region(self, obj):
        from django.utils.html import format_html
        return format_html('{}', obj.region.region_name if obj.region else '—')
    colored_region.short_description = 'Bölgə'
    colored_region.admin_order_field = 'region__region_name'

    def colored_report_month(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="color:#94a3b8;">{}</span>',
            obj.report_month.strftime('%B %Y')
        )
    colored_report_month.short_description = 'Hesabat ayı'
    colored_report_month.admin_order_field = 'report_month'

    def colored_yekun_borc(self, obj):
        from django.utils.html import format_html
        color = '#ef4444' if (obj.yekun_borc or 0) > 0 else '#34d399'
        return format_html(
            '<span style="color:{}; font-weight:bold;">{:.2f} ₼</span>',
            color, obj.yekun_borc or 0
        )
    colored_yekun_borc.short_description = 'Yekun borc'
    colored_yekun_borc.admin_order_field = 'yekun_borc'


admin.site.register(MonthlyDoctorReport, MonthlyDoctorReportAdmin)