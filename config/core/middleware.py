from django.conf import settings
from django.shortcuts import redirect

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Statik və media faylları bypass et
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith('/media/'):
            return self.get_response(request)

        # Vizit modulu öz sessiyası ilə işləyir — Django auth tələb olunmur
        if request.path.startswith('/vizit/'):
            return self.get_response(request)

        # /login və /logout üçün trailing slash fərqi olmamalıdır (mobil brauzerlərdə tez-tez /login yazılır)
        normalized_path = request.path.rstrip('/') or '/'
        if not request.user.is_authenticated and normalized_path not in ['/login', '/logout']:
            return redirect('/login/')

        return self.get_response(request)
