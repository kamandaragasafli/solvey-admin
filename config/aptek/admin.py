from django.contrib import admin

from .models import AnbarHereket, Aptek, Qaime


@admin.register(Aptek)
class AptekAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class AnbarHereketInline(admin.TabularInline):
    model = AnbarHereket
    extra = 0
    fields = ('drug', 'movement_type', 'quantity', 'date', 'note')


@admin.register(Qaime)
class QaimeAdmin(admin.ModelAdmin):
    list_display = ('number', 'document_type', 'aptek', 'doc_date', 'total', 'created_at')
    list_filter = ('document_type', 'aptek', 'doc_date', 'created_at')
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
    list_display = ('drug', 'movement_type', 'quantity', 'date', 'aptek', 'qaime')
    list_filter = ('movement_type', 'date', 'aptek')
    search_fields = ('drug__med_name', 'note')
    date_hierarchy = 'date'
