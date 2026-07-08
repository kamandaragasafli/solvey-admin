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


@admin.register(AnbarHereket)
class AnbarHereketAdmin(admin.ModelAdmin):
    list_display = ('drug', 'movement_type', 'quantity', 'date', 'aptek', 'qaime')
    list_filter = ('movement_type', 'date', 'aptek')
    search_fields = ('drug__med_name', 'note')
    date_hierarchy = 'date'
