from django.conf import settings
from django.shortcuts import redirect

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Statik və media faylları bypass et
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith('/media/'):
            return self.get_response(request)

        if not request.user.is_authenticated and request.path not in ['/login/', '/logout/']:
            return redirect('/login/')

        return self.get_response(request)
