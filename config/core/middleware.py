from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # Bu path-lar Django auth tələb etmir (öz daxili login sistemimiz var)
    EXEMPT_PATHS = [
        '/login',
        '/logout',
        '/groups/login',
        '/groups/logout',
        '/groups-drugs/login',
        '/groups-drugs/logout',
    ]

    def __call__(self, request):
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith('/media/'):
            return self.get_response(request)

        if request.path.startswith('/vizit/'):
            return self.get_response(request)

        # Groups modulu öz sessiyası ilə işləyir
        if request.path.startswith('/groups/'):
            return self.get_response(request)

        normalized_path = request.path.rstrip('/') or '/'

        if not request.user.is_authenticated and normalized_path not in self.EXEMPT_PATHS:
            return redirect('/login/')

        # Əsas admin yalnız staff/superuser — vizit hesabları buraya gire bilməz
        if (
            request.user.is_authenticated
            and normalized_path not in self.EXEMPT_PATHS
            and not (request.user.is_staff or request.user.is_superuser)
        ):
            logout(request)
            return redirect('/login/')

        # Aktiv vizit (İstifadeci) login-i ilə eyni username → adminə icazə yoxdur
        if (
            request.user.is_authenticated
            and not request.user.is_superuser
            and normalized_path not in self.EXEMPT_PATHS
        ):
            try:
                from vizit.models import Istifadeci
                if Istifadeci.objects.filter(
                    login__iexact=request.user.username,
                    aktiv=True,
                ).exists():
                    logout(request)
                    return redirect('/vizit/login/')
            except Exception:
                pass

        return self.get_response(request)