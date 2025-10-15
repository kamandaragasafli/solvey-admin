from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import TrackingSession, LocationPoint, StopPoint

class LocationPointInline(admin.TabularInline):
    model = LocationPoint
    extra = 0
    readonly_fields = ('latitude', 'longitude', 'speed', 'timestamp')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class StopPointInline(admin.TabularInline):
    model = StopPoint
    extra = 0
    readonly_fields = ('latitude', 'longitude', 'start_time', 'end_time', 'duration')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'user', 
        'start_time', 
        'end_time', 
        'total_distance_km', 
        'total_duration_formatted',
        'locations_count',
        'stops_count'
    )
    list_filter = ('start_time', 'user', 'end_time')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('start_time', 'total_distance', 'total_duration')
    inlines = [LocationPointInline, StopPointInline]
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Əsas Məlumatlar', {
            'fields': ('user', 'start_time', 'end_time')
        }),
        ('Statistikalar', {
            'fields': ('total_distance', 'total_duration'),
            'classes': ('collapse',)
        }),
    )
    
    def total_distance_km(self, obj):
        return f"{(obj.total_distance / 1000):.2f} km"
    total_distance_km.short_description = 'Ümumi Məsafə'
    
    def total_duration_formatted(self, obj):
        if obj.total_duration:
            hours = int(obj.total_duration // 3600)
            minutes = int((obj.total_duration % 3600) // 60)
            seconds = int(obj.total_duration % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    total_duration_formatted.short_description = 'Ümumi Müddət'
    
    def locations_count(self, obj):
        return obj.locations.count()
    locations_count.short_description = 'Mövqe Sayı'
    
    def stops_count(self, obj):
        return obj.stops.count()
    stops_count.short_description = 'Dayanma Sayı'

class LocationPointAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'session_user',
        'latitude',
        'longitude', 
        'speed_kmh',
        'timestamp',
        'session_start'
    )
    list_filter = ('timestamp', 'session__user', 'session__start_time')
    search_fields = (
        'session__user__username', 
        'session__user__email',
        'latitude',
        'longitude'
    )
    readonly_fields = ('session', 'latitude', 'longitude', 'speed', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def session_user(self, obj):
        return obj.session.user.username
    session_user.short_description = 'İstifadəçi'
    
    def speed_kmh(self, obj):
        return f"{(obj.speed * 3.6):.1f} km/s" if obj.speed else "0 km/s"
    speed_kmh.short_description = 'Sürət'
    
    def session_start(self, obj):
        return obj.session.start_time
    session_start.short_description = 'Sessiya Başlama'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

class StopPointAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'session_user',
        'latitude',
        'longitude',
        'duration_formatted',
        'start_time',
        'end_time'
    )
    list_filter = ('start_time', 'session__user', 'session__start_time')
    search_fields = (
        'session__user__username',
        'session__user__email', 
        'latitude',
        'longitude'
    )
    readonly_fields = ('session', 'latitude', 'longitude', 'start_time', 'end_time', 'duration')
    date_hierarchy = 'start_time'
    
    def session_user(self, obj):
        return obj.session.user.username
    session_user.short_description = 'İstifadəçi'
    
    def duration_formatted(self, obj):
        if obj.duration:
            minutes = int(obj.duration // 60)
            seconds = int(obj.duration % 60)
            return f"{minutes} dəq {seconds} san"
        return "0 dəq"
    duration_formatted.short_description = 'Dayanma Müddəti'

# User modelini dəyişdirmək üçün custom admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'date_joined', 'tracking_sessions_count')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    
    def tracking_sessions_count(self, obj):
        return obj.trackingsession_set.count()
    tracking_sessions_count.short_description = 'İzləmə Sessiyaları'

# Admin paneldə göstərmək üçün qeydiyyat
admin.site.register(TrackingSession, TrackingSessionAdmin)
admin.site.register(LocationPoint, LocationPointAdmin)
admin.site.register(StopPoint, StopPointAdmin)

# Default User admini ləğv edib custom admini qeyd et
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin panel konfiqurasiyası
admin.site.site_header = "GPS İzləmə Sistemi Admin Paneli"
admin.site.site_title = "GPS İzləmə Sistemi"
admin.site.index_title = "Sistem İdarəetməsi"