from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("🎉 SAYT İŞLƏYİR! Bütün custom apps comment-də.")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('/login/')),  
    path('test/', test_view),
    path('', include("core.urls")),
    path('drugs/', include("medicine.urls")),
    path('dashboard/', include("export.urls")),
    path('reports/', include("payment.urls")),
    path('regions/', include("regions.urls")),
    path('doctors/', include("doctors.urls")),
    path('api/', include("tracking.urls")),
    path('users/', include("user.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
