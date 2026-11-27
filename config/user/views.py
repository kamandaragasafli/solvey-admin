from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth import authenticate, get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import IntegrityError
from .serializers import RegisterSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

# Qeydiyyat
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": serializer.data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)

# Login (email + şifrə ilə)
class LoginAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Bütün xanaları doldurun"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Username və ya parol səhvdir"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response({"error": "Username və ya parol səhvdir"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response({"username": user.username, "email": user.email})


# Web İstifadəçi İdarəetmə
def user_management_view(request):
    """İstifadəçi idarəetmə səhifəsi - vizit admin panel-dən ayrı"""
    from vizit.models import Istifadeci
    from regions.models import Region
    from django.contrib.auth.decorators import login_required

    if not request.user.is_superuser:
        return redirect('admin')

    if request.method == 'POST':
        # İSTİFADƏÇİ ƏLAVƏ ETMƏ
        if 'add_user' in request.POST:
            login = request.POST.get('login', '').strip()
            sifre = request.POST.get('sifre', '').strip()
            ad = request.POST.get('ad', '').strip()
            rol = request.POST.get('rol', Istifadeci.ROL_NUMAYENDE)
            bolge_ids = request.POST.getlist('bolge_ids')
            valid_bolge_ids = [int(b_id) for b_id in bolge_ids if b_id]

            if login and sifre and ad:
                try:
                    istifadeci = Istifadeci(login=login, ad=ad, rol=rol, aktiv=True)
                    istifadeci.set_password(sifre)
                    istifadeci.save()

                    if valid_bolge_ids:
                        istifadeci.bolgeler.set(valid_bolge_ids)

                    messages.success(request, '✅ İstifadəçi uğurla əlavə edildi.')
                except IntegrityError:
                    messages.error(request, '❌ Xəta: login artıq mövcuddur.')
            else:
                messages.error(request, '❌ Bütün sahələri doldurun.')
            return redirect('user:management')

        # İSTİFADƏÇİ REDAKTƏ
        elif 'save_user' in request.POST:
            try:
                uid = int(request.POST.get('user_id') or 0)
            except (TypeError, ValueError):
                uid = 0
            user = Istifadeci.objects.filter(pk=uid).first()
            if not user:
                messages.error(request, '❌ İstifadəçi tapılmadı.')
                return redirect('user:management')

            login = request.POST.get('login', '').strip()
            sifre = request.POST.get('sifre', '').strip()
            ad = request.POST.get('ad', '').strip()
            rol = request.POST.get('rol', user.rol)
            aktiv = request.POST.get('aktiv') == '1'
            bolge_ids = request.POST.getlist('bolge_ids')
            valid_bolge_ids = [int(b_id) for b_id in bolge_ids if b_id]

            if not login or not ad:
                messages.error(request, '❌ Login və ad mütləqdir.')
                return redirect(f"{reverse('user:management')}?edit_user={uid}")

            if Istifadeci.objects.filter(login=login).exclude(pk=user.pk).exists():
                messages.error(request, '❌ Bu login artıq mövcuddur.')
                return redirect(f"{reverse('user:management')}?edit_user={uid}")

            user.login = login
            user.ad = ad
            user.rol = rol
            user.aktiv = aktiv
            if sifre:
                user.set_password(sifre)
            user.save()
            user.bolgeler.set(valid_bolge_ids)
            messages.success(request, f'✅ İstifadəçi yeniləndi: {user.ad}')
            return redirect('user:management')

    # İSTİFADƏÇİ SİLMƏ
    if 'del_user' in request.GET:
        try:
            uid = int(request.GET['del_user'])
        except (TypeError, ValueError):
            messages.error(request, '❌ Yanlış istifadəçi.')
            return redirect('user:management')

        user = Istifadeci.objects.filter(pk=uid).first()
        if not user:
            messages.error(request, '❌ İstifadəçi tapılmadı.')
            return redirect('user:management')

        ad = user.ad
        try:
            user.delete()
            messages.success(request, f'✅ İstifadəçi silindi: {ad}')
        except Exception as e:
            messages.error(request, f'❌ {ad} silinə bilmədi — {str(e)}')
        return redirect('user:management')

    # SƏHİFƏNİ YÜKLƏMƏ
    edit_user = None
    edit_user_bolge_ids = set()
    edit_user_id = request.GET.get('edit_user')
    if edit_user_id:
        try:
            edit_user = (
                Istifadeci.objects.prefetch_related('bolgeler')
                .filter(pk=int(edit_user_id))
                .first()
            )
            if edit_user:
                edit_user_bolge_ids = set(edit_user.bolgeler.values_list('id', flat=True))
        except (TypeError, ValueError):
            edit_user = None

    return render(
        request,
        'user/user_management.html',
        {
            'edit_user': edit_user,
            'edit_user_bolge_ids': edit_user_bolge_ids,
            'istifadeciler': (
                Istifadeci.objects.exclude(login__contains='__silindi_')
                .prefetch_related('bolgeler')
                .order_by('rol', 'ad')
            ),
            'bolgeler': Region.objects.order_by('region_name'),
        },
    )


def user_activity_view(request):
    """İstifadəçi aktivlik izləmə səhifəsi"""
    from vizit.models import Istifadeci, UserActivityLog
    from django.contrib.auth.decorators import login_required

    if not request.user.is_superuser:
        return redirect('admin')

    from django.utils import timezone
    from datetime import timedelta

    # Son 7 gündəki aktivliklər
    bir_hefte_once = timezone.now() - timedelta(days=7)
    logs = UserActivityLog.objects.filter(
        timestamp__gte=bir_hefte_once
    ).select_related('istifadeci').order_by('-timestamp')

    # Hazırda aktiv istifadəçilər
    active_users = UserActivityLog.objects.filter(
        is_active=True,
        action='login'
    ).select_related('istifadeci').order_by('-timestamp')

    return render(
        request,
        'user/user_activity.html',
        {
            'logs': logs,
            'active_users': active_users,
        },
    )


def user_tracking_view(request):
    """İstifadəçi konum izləmə səhifəsi"""
    from vizit.models import UserActivityLog
    from django.contrib.auth.decorators import login_required

    if not request.user.is_superuser:
        return redirect('admin')

    # Konumu olan aktivliklər
    logs = UserActivityLog.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('istifadeci').order_by('-timestamp')

    return render(
        request,
        'user/tracking.html',
        {
            'logs': logs,
        },
    )