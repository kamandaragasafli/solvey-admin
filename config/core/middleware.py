from django.shortcuts import redirect

class LoginRequiredMiddleware:
    """
    İstifadəçi login etməyibsə bütün sayt üçün login səhifəsinə yönləndirir.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # login olunmayıbsa və URL login/logout deyil, yönləndir
        if not request.user.is_authenticated and request.path not in ['/login/', '/logout/']:
            return redirect('/login/')
        response = self.get_response(request)
        return response

