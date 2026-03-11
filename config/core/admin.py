from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import DeletedRecipeDrugLog
from doctors.models import Recipe


class DeletedByFilter(admin.SimpleListFilter):
    title = _('Silən istifadəçi')
    parameter_name = 'deleted_by'

    def lookups(self, request, model_admin):
        users = (
            DeletedRecipeDrugLog.objects
            .exclude(deleted_by=None)
            .select_related('deleted_by')
            .values_list('deleted_by__id', 'deleted_by__username')
            .distinct()
        )
        return [(uid, uname) for uid, uname in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(deleted_by__id=self.value())
        return queryset


@admin.register(DeletedRecipeDrugLog)
class DeletedRecipeDrugLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'colored_drug_name',
        'get_doctor_name',
        'get_region_name',
        'recipe_id',
        'colored_deleted_at',
        'colored_deleted_by',
    )
    list_filter = ('deleted_at', DeletedByFilter)
    search_fields = ('drug_name', 'deleted_by__username')
    ordering = ('-deleted_at',)
    list_per_page = 50
    date_hierarchy = 'deleted_at'
    readonly_fields = ('drug_name', 'recipe_id', 'deleted_at', 'deleted_by', 'get_doctor_name', 'get_region_name')

    actions = ['toplu_sil']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('deleted_by')

    # ── Rəngli sütunlar ────────────────────────────────────────────────────────

    def colored_drug_name(self, obj):
        return format_html(
            '<span style="color:#f59e0b; font-weight:bold;">{}</span>',
            obj.drug_name
        )
    colored_drug_name.short_description = 'Dərman'
    colored_drug_name.admin_order_field = 'drug_name'

    def colored_deleted_at(self, obj):
        return format_html(
            '<span style="color:#94a3b8;">{}</span>',
            obj.deleted_at.strftime('%d.%m.%Y %H:%M')
        )
    colored_deleted_at.short_description = 'Silinmə tarixi'
    colored_deleted_at.admin_order_field = 'deleted_at'

    def colored_deleted_by(self, obj):
        if obj.deleted_by:
            return format_html(
                '<span style="color:#ef4444; font-weight:bold;">{}</span>',
                obj.deleted_by.username
            )
        return format_html('<span style="color:#6b7280;">—</span>')
    colored_deleted_by.short_description = 'Silən'
    colored_deleted_by.admin_order_field = 'deleted_by__username'

    # ── Recipe-dən həkim və bölgə məlumatı ────────────────────────────────────

    def _get_recipe(self, obj):
        if not hasattr(obj, '_cached_recipe'):
            try:
                obj._cached_recipe = Recipe.objects.select_related('dr', 'region').get(id=obj.recipe_id)
            except Recipe.DoesNotExist:
                obj._cached_recipe = None
        return obj._cached_recipe

    def get_doctor_name(self, obj):
        recipe = self._get_recipe(obj)
        if recipe:
            return format_html(
                '<span style="color:#60a5fa; font-weight:bold;">{}</span>',
                recipe.dr.ad
            )
        return format_html('<span style="color:#6b7280;">—</span>')
    get_doctor_name.short_description = 'Həkim'

    def get_region_name(self, obj):
        recipe = self._get_recipe(obj)
        if recipe:
            return recipe.region.region_name
        return '—'
    get_region_name.short_description = 'Bölgə'

    # ── Toplu sil action ──────────────────────────────────────────────────────

    def toplu_sil(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} log qeydi uğurla silindi.')
    toplu_sil.short_description = 'Seçilmiş log qeydlərini sil'

    # ── Detail view-də əlavə sahələr ─────────────────────────────────────────

    def get_fields(self, request, obj=None):
        return ('drug_name', 'get_doctor_name', 'get_region_name', 'recipe_id', 'deleted_at', 'deleted_by')
