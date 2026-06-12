import os
from pathlib import Path
from django.conf import settings
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
        # Statik və media faylları bypass et
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith('/media/'):
            return self.get_response(request)

        # Vizit modulu öz sessiyası ilə işləyir — Django auth tələb olunmur
        if request.path.startswith('/vizit/'):
            return self.get_response(request)

        # Trailing slash fərqi olmamalıdır (mobil brauzerlərdə tez-tez /login yazılır)
        normalized_path = request.path.rstrip('/') or '/'

        if not request.user.is_authenticated and normalized_path not in self.EXEMPT_PATHS:
            return redirect('/login/')

        return self.get_response(request)