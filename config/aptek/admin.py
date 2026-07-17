from django.contrib import admin

from .models import AnbarHereket, Aptek, Depo, DrugPrice, Qaime


@admin.register(Depo)
class DepoAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name',)


@admin.register(DrugPrice)
class DrugPriceAdmin(admin.ModelAdmin):
    list_display = ('drug', 'depo', 'price', 'expiry_date')
    search_fields = ('drug__med_name',)
    raw_id_fields = ('drug',)


@admin.register(Aptek)
class AptekAdmin(admin.ModelAdmin):
    list_display = ('name', 'depo')
    list_filter = ('depo',)
    search_fields = ('name',)


class AnbarHereketInline(admin.TabularInline):
    model = AnbarHereket
    extra = 0
    fields = ('drug', 'movement_type', 'quantity', 'date', 'note')


@admin.register(Qaime)
class QaimeAdmin(admin.ModelAdmin):
    list_display = ('number', 'document_type', 'depo', 'aptek', 'doc_date', 'total', 'created_at')
    list_filter = ('document_type', 'depo', 'aptek', 'doc_date', 'created_at')
    search_fields = ('number', 'aptek__name')
    inlines = [AnbarHereketInline]

    def delete_model(self, request, obj):
        # CASCADE anbar hərəkətlərini silir; PDF faylı da təmizlə
        if obj.pdf:
            obj.pdf.delete(save=False)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.pdf:
                obj.pdf.delete(save=False)
        super().delete_queryset(request, queryset)


@admin.register(AnbarHereket)
class AnbarHereketAdmin(admin.ModelAdmin):
    list_display = ('drug', 'movement_type', 'quantity', 'date', 'depo', 'aptek', 'qaime')
    list_filter = ('movement_type', 'depo', 'date', 'aptek')
    search_fields = ('drug__med_name', 'note')
    date_hierarchy = 'date'
