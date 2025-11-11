from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from .models import Doctors, Recipe, RecipeDrug, RealSales, RealSalesDrug

@admin.register(Doctors)
class DoctorsAdmin(admin.ModelAdmin):
    list_display = ('id','ad', 'previous_debt',  'yekun_borc','bolge_info',  'kategoriya', 'derece', 'ixtisas' , 'avans', 'investisiya',
                   'borc_display', 'action_buttons')
    list_display_links = ('ad', 'bolge_info')
    list_filter = ('bolge', 'kategoriya', 'ixtisas')
    list_editable = ('previous_debt', 'kategoriya', 'derece',)

    search_fields = ('ad','bolge__region_name', )
    ordering = ('bolge__region_name', 'ad')
    list_per_page = 50
    list_select_related = ('bolge',)
    
    # Yalnız barkod readonly olsun
    readonly_fields = ('barkod', 'avans', 'investisiya') 

    actions = ['reset_financial_data', 'export_doctors_data']

    fieldsets = (
        ('Əsas Məlumatlar', {
            'fields': ('ad', 'barkod', 'bolge', 'kategoriya', 'ixtisas')
        }),
        ('Maliyyə Məlumatları', {
            'fields': (
                'previous_debt', 'borc', 'hesablanan_miqdar', 
                'hekimden_silinen', 'razılaşma', 
                'avans', 'investisiya'  # 💥 Buraya əlavə olunur
            )
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }
        js = ('admin/js/custom.js',)
        
    def bolge_info(self, obj):
        if not obj.pk:  # Yeni həkim üçün
            return '-'
        return obj.bolge.region_name if obj.bolge else '-'
    bolge_info.short_description = 'Bölgə'
    bolge_info.admin_order_field = 'bolge__region_name'

    def borc_display(self, obj):
        if not obj.pk:  # Yeni həkim üçün
            return format_html('<span style="color: #999;">0.00 ₼</span>')
        
        borc_str = "{:.2f} ₼".format(obj.borc or 0)
        color = 'red' if (obj.borc or 0) > 0 else 'green'
        return format_html('<span style="color: {};">{}</span>', color, borc_str)
    borc_display.short_description = 'Borc'
    
    def borc_display(self, obj):
        borc_str = "{:.2f} ₼".format(obj.borc or 0)
        color = 'red' if (obj.borc or 0) > 0 else 'green'
        return format_html('<span style="color: {};">{}</span>', color, borc_str)

    
    def borc_display(self, obj):
        borc_str = "{:.2f} ₼".format(obj.borc or 0)
        color = 'red' if (obj.borc or 0) > 0 else 'green'
        return format_html('<span style="color: {};">{}</span>', color, borc_str)


    
    def action_buttons(self, obj):
        # Əgər hələ save olunmayıbsa (primary key yoxdursa)
        if not obj.pk:
            return format_html('<span style="color: #999;">Yeni həkim - əvvəlcə yadda saxlayın</span>')
        
        return format_html(
            '<div class="btn-group">'
            '<a href="{}" class="btn btn-xs btn-info" style="margin-right:2px;">Reseptlər</a>'
            '<a href="{}" class="btn btn-xs btn-warning" style="margin-right:2px;">Satışlar</a>'
            '<a href="{}" class="btn btn-xs btn-success">Redaktə</a>'
            '</div>',
            reverse('admin:doctors_recipe_changelist') + f'?dr__id__exact={obj.id}',
            reverse('admin:doctors_realsales_changelist') + f'?dr_name__id__exact={obj.id}',
            reverse('admin:doctors_doctors_change', args=[obj.id])
        )
    action_buttons.short_description = 'Əməliyyatlar'
    
    def reset_financial_data(self, request, queryset):
        updated = queryset.update(
            investisiya=0,
            hesablanan_miqdar=0,
            hekimden_silinen=0
        )
        self.message_user(request, f"{updated} həkimin maliyyə məlumatları sıfırlandı")
    reset_financial_data.short_description = "Seçilmiş həkimlərin maliyyə məlumatlarını sıfırla"
    
    def export_doctors_data(self, request, queryset):
        self.message_user(request, f"{queryset.count()} həkimin məlumatları eksporta hazırdır")
    export_doctors_data.short_description = "Seçilmiş həkimlərin məlumatlarını eksport et"
    
    def changelist_view(self, request, extra_context=None):
        total_doctors = Doctors.objects.count()
        total_debt = Doctors.objects.aggregate(
            total=Coalesce(Sum('borc'), 0, output_field=DecimalField())
        )['total']
       
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_doctors': total_doctors,
            'total_debt': total_debt,
        })
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('dr', 'region', 'date', 'total_drugs_count')
    list_filter = ('region', 'date')
    search_fields = ('dr__ad', 'region__region_name')
    date_hierarchy = 'date'
    list_select_related = ('dr', 'region')
    
    def total_drugs_count(self, obj):
        return obj.drugs.count()
    total_drugs_count.short_description = 'Dərman Sayı'

@admin.register(RecipeDrug)
class RecipeDrugAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'drug', 'number')
    list_filter = ('drug',)
    search_fields = ('recipe__dr__ad', 'drug__med_name')

@admin.register(RealSales)
class RealSalesAdmin(admin.ModelAdmin):
    list_display = ('dr_name', 'region_n', 'date_sale', 'total_sales_count')
    list_filter = ('region_n', 'date_sale')
    search_fields = ('dr_name__ad', 'region_n__region_name')
    date_hierarchy = 'date_sale'
    
    def total_sales_count(self, obj):
        return obj.drug_name.count()
    total_sales_count.short_description = 'Satış Sayı'

@admin.register(RealSalesDrug)
class RealSalesDrugAdmin(admin.ModelAdmin):
    list_display = ('real_sale', 'drug_name', 'numbers')
    list_filter = ('drug_name',)
    search_fields = ('real_sale__dr_name__ad', 'drug_name__med_name')

# Admin panel başlıqları
admin.site.site_header = "Həkim İdarəetmə Sistemi"
admin.site.site_title = "Həkim Admin Panel"
admin.site.index_title = "Sistem İdarəetməsi"
