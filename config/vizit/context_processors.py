from .models import Istifadeci

ROL_LABELS = dict(Istifadeci.ROL_CHOICES)


def vizit_session(request):
    rol = request.session.get('rol', '')
    return {
        'session_ad': request.session.get('ad', ''),
        'session_rol': rol,
        'session_rol_label': ROL_LABELS.get(rol, rol),
    }
