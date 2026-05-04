from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from regions.models import Region
from core.models import DeletedRecipeDrugLog
from .models import Doctors, Recipe, RecipeDrug, RealSales, RealSalesDrug


class RecipeDailyBulkDeleteForm(forms.Form):
    """Tarix üçün brauzer təqvimi (native date picker)."""

    region = forms.ModelChoiceField(
        queryset=Region.objects.none(),
        empty_label="— Seçin —",
        label="Bölgə",
        required=True,
    )
    recipe_date = forms.DateField(
        label="Resept tarixi",
        required=True,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "style": "max-width:14rem;padding:0.35rem 0.5rem;"},
        ),
    )
    confirm = forms.BooleanField(
        required=True,
        label="Təsdiq",
        help_text=(
            "Başa düşürəm ki, bu əməliyyat geri qaytarıla bilməz və seçilmiş tarix üçün "
            "həmin bölgədəki bütün resept qeydiyyatları silinəcək."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].queryset = Region.objects.order_by("region_name")

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
            'fields': ('ad', 'barkod', 'bolge', 'city', 'kategoriya', 'ixtisas')
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

class RegionFilter(admin.SimpleListFilter):
    title = 'Bölgə'
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        from regions.models import Region
        return [(r.id, r.region_name) for r in Region.objects.order_by('region_name')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(recipe__region_id=self.value())
        return queryset


@admin.register(RecipeDrug)
class RecipeDrugAdmin(admin.ModelAdmin):
    change_list_template = "admin/doctors/recipedrug/change_list.html"

    list_display = (
        'id',
        'get_doctor_name',
        'get_region_name',
        'colored_drug',
        'colored_number',
        'get_recipe_date',
        'colored_created_at',
    )
    list_filter = (RegionFilter, 'drug', 'created_at')
    search_fields = (
        'recipe__dr__ad',
        'drug__med_name',
        'recipe__region__region_name',
    )
    ordering = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'
    list_select_related = ('recipe__dr', 'recipe__region', 'drug')

    actions = ['toplu_sil_action']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "delete-daily-by-region/",
                self.admin_site.admin_view(self.delete_daily_by_region_view),
                name="doctors_recipedrug_delete_daily_by_region",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["delete_daily_url"] = reverse(
            "admin:doctors_recipedrug_delete_daily_by_region"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def delete_daily_by_region_view(self, request):
        if not request.user.has_perm("doctors.delete_recipedrug"):
            raise PermissionDenied
        title = "Günlük bölgə üzrə qeydiyyatı sil"

        if request.method != "POST":
            form = RecipeDailyBulkDeleteForm()
            return render(
                request,
                "admin/doctors/recipedrug/delete_daily_region.html",
                {"title": title, "form": form},
            )

        form = RecipeDailyBulkDeleteForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "admin/doctors/recipedrug/delete_daily_region.html",
                {"title": title, "form": form},
            )

        region = form.cleaned_data["region"]
        target_date = form.cleaned_data["recipe_date"]
        region_id = region.pk

        recipe_qs = Recipe.objects.filter(region_id=region_id, date=target_date)
        recipe_count = recipe_qs.count()
        line_qs = RecipeDrug.objects.filter(
            recipe__region_id=region_id, recipe__date=target_date
        ).select_related("drug", "recipe")

        line_count = line_qs.count()
        if recipe_count == 0:
            messages.warning(
                request,
                f"{region.region_name} — {target_date.strftime('%d.%m.%Y')} üçün silinəcək qeydiyyat yoxdur.",
            )
            return redirect("admin:doctors_recipedrug_changelist")

        with transaction.atomic():
            batch = []
            batch_size = 500
            for rd in line_qs.iterator(chunk_size=batch_size):
                batch.append(
                    DeletedRecipeDrugLog(
                        drug_name=str(rd.drug),
                        recipe_id=rd.recipe_id,
                        deleted_by=request.user if request.user.is_authenticated else None,
                    )
                )
                if len(batch) >= batch_size:
                    DeletedRecipeDrugLog.objects.bulk_create(batch)
                    batch = []
            if batch:
                DeletedRecipeDrugLog.objects.bulk_create(batch)
            deleted = recipe_qs.delete()

        messages.success(
            request,
            f"{region.region_name} • {target_date.strftime('%d.%m.%Y')}: "
            f"{recipe_count} resept silindi ({line_count} dərman sətri); "
            f"cəmi qeydə alınmış obyekt: {deleted[0]}",
        )
        return redirect("admin:doctors_recipedrug_changelist")

    def get_doctor_name(self, obj):
        return format_html(
            '<span style="color:#60a5fa; font-weight:bold;">{}</span>',
            obj.recipe.dr.ad
        )
    get_doctor_name.short_description = 'Həkim'
    get_doctor_name.admin_order_field = 'recipe__dr__ad'

    def get_region_name(self, obj):
        return obj.recipe.region.region_name
    get_region_name.short_description = 'Bölgə'
    get_region_name.admin_order_field = 'recipe__region__region_name'

    def colored_drug(self, obj):
        return format_html(
            '<span style="color:#f59e0b; font-weight:bold;">{}</span>',
            obj.drug.med_name
        )
    colored_drug.short_description = 'Dərman'
    colored_drug.admin_order_field = 'drug__med_name'

    def colored_number(self, obj):
        return format_html(
            '<span style="color:#34d399; font-weight:bold;">{}</span>',
            obj.number
        )
    colored_number.short_description = 'Say'
    colored_number.admin_order_field = 'number'

    def get_recipe_date(self, obj):
        return obj.recipe.date.strftime('%d.%m.%Y')
    get_recipe_date.short_description = 'Resept tarixi'
    get_recipe_date.admin_order_field = 'recipe__date'

    def colored_created_at(self, obj):
        return format_html(
            '<span style="color:#94a3b8;">{}</span>',
            obj.created_at.strftime('%d.%m.%Y %H:%M')
        )
    colored_created_at.short_description = 'Əlavə tarixi'
    colored_created_at.admin_order_field = 'created_at'

    def toplu_sil_action(self, request, queryset):
        logs = [
            DeletedRecipeDrugLog(
                drug_name=str(rd.drug),
                recipe_id=rd.recipe.id,
                deleted_by=request.user,
            )
            for rd in queryset.select_related('drug', 'recipe')
        ]
        DeletedRecipeDrugLog.objects.bulk_create(logs)
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} qeydiyyat silindi və log-a yazıldı.')
    toplu_sil_action.short_description = 'Seçilmiş qeydiyyatları sil (log ilə)'

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
