from django.contrib import admin
from .models import (
    Istifadeci,
    Vizit,
    VizitPreparat,
    AptekVizit,
    AptekVizitPreparat,
    WeeklySchedule,
    WeeklyScheduleDay,
    WeeklyScheduleVisit,
    GorulenHekim,
)

# Register your models here.
class IstifadeciAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        # Şifrə sahəsi dəyişibsə, hash et
        if 'sifre' in form.changed_data:
            obj.sifre = Istifadeci.hash_sifre(form.cleaned_data['sifre'])
        super().save_model(request, obj, form, change)

admin.site.register(Istifadeci, IstifadeciAdmin)
admin.site.register(Vizit)
admin.site.register(VizitPreparat)
admin.site.register(AptekVizit)
admin.site.register(AptekVizitPreparat)


class WeeklyScheduleDayInline(admin.TabularInline):
    model = WeeklyScheduleDay
    extra = 0


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ("week_start", "created_by", "menecer_name", "created_at")
    list_filter = ("week_start",)
    inlines = [WeeklyScheduleDayInline]


@admin.register(WeeklyScheduleVisit)
class WeeklyScheduleVisitAdmin(admin.ModelAdmin):
    list_display = ("place_name", "day", "position")
    search_fields = ("place_name",)


@admin.register(GorulenHekim)
class GorulenHekimAdmin(admin.ModelAdmin):
    list_display = ("hekim", "bolge", "istifadeci", "seen_date", "seen_at")
    list_filter = ("seen_date", "bolge")
    search_fields = ("hekim__ad", "istifadeci__ad")







class VizitAdmin(admin.ModelAdmin):
    list_display = ('istifadeci', 'bolge', 'rayon', 'munasibat', 'tarix', 'vaxt')
    list_filter = ('tarix', 'vaxt')
    search_fields = ('istifadeci', 'bolge', 'rayon', 'munasibat')
    list_per_page = 10
    ordering = ('-tarix', '-vaxt')
    readonly_fields = ('created_at',)
    fields = ('istifadeci', 'bolge', 'rayon', 'munasibat', 'tarix', 'vaxt', 'qeyd', 'created_at')
    autocomplete_fields = ('istifadeci', 'bolge', 'rayon')
    list_display_links = ('istifadeci', 'bolge', 'rayon', 'munasibat')
    list_editable = ('tarix', 'vaxt')
    list_select_related = ('istifadeci', 'bolge', 'rayon')
    list_max_show_all = 10
    list_per_page = 10
    ordering = ('-tarix', '-vaxt')


class AptekVizitAdmin(admin.ModelAdmin):
    list_display = ('aptek_ad', 'aptek_nomre', 'tarix', 'vaxt')
    list_filter = ('tarix', 'vaxt')
    search_fields = ('aptek_ad', 'aptek_nomre')
    list_per_page = 10
    ordering = ('-tarix', '-vaxt')
    readonly_fields = ('created_at',)
    fields = ('aptek_ad', 'aptek_nomre', 'tarix', 'vaxt', 'qeyd', 'created_at')
    autocomplete_fields = ('rayon', 'bolge', 'istifadeci')
    list_display_links = ('aptek_ad', 'aptek_nomre')
    list_editable = ('tarix', 'vaxt')
    list_select_related = ('rayon', 'bolge', 'istifadeci')
    list_max_show_all = 10
    list_per_page = 10
    ordering = ('-tarix', '-vaxt')