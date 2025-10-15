# project_root/middleware/restrict_user.py

from django.shortcuts import redirect
from django.urls import resolve

class RestrictNormalUserMiddleware:
    """
    Normal istifadəçilərin yalnız 'movqe_gonder_view' və ya icazəli URL-lərə daxil olmasını təmin edir.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # İstifadəçi login olub, normal istifadəçi qrupundadırsa
        if request.user.is_authenticated and request.user.groups.filter(name="İstifadəçi").exists():
            # Hal-hazırki URL adını al
            url_name = resolve(request.path_info).url_name

            # Yalnız 'movqe_gonder_view' icazəlidir
            allowed_urls = ['movqe_gonder_view', 'user_logout']  # logout da əlavə edin

            # Əgər icazəsiz URL-dirsə, redirect edin
            if url_name not in allowed_urls:
                return redirect('movqe_gonder_view')

        response = self.get_response(request)
        return response
