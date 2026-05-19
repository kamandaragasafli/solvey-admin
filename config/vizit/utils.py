from functools import wraps

from django.shortcuts import redirect, render


def vizit_giris_yoxla(request):
    if not request.session.get('istifadeci_id'):
        return redirect('vizit:login')
    return None


def vizit_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        redirect_response = vizit_giris_yoxla(request)
        if redirect_response:
            return redirect_response
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def menecer_rehber_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        redirect_response = vizit_giris_yoxla(request)
        if redirect_response:
            return redirect_response
        if request.session.get('rol') not in ('menecer', 'rehber'):
            return redirect('vizit:index')
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def rehber_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('istifadeci_id'):
            return redirect('vizit:login')
        if request.session.get('rol') != 'rehber':
            return render(request, 'vizit/errors/403.html', status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def vizit_session_yaz(request, istifadeci):
    for key, value in istifadeci.session_dict().items():
        request.session[key] = value


def vizit_session_temizle(request):
    for key in ('istifadeci_id', 'ad', 'rol', 'bolge_id'):
        request.session.pop(key, None)
