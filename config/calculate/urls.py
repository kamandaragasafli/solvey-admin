from django.urls import path
from .views import login_user, hesablamalar, admin_page, logout_user

app_name = 'calculate'

urlpatterns = [
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
    path('calculate/', hesablamalar, name='hesablamalar'),
    path('admin/', admin_page, name='admin_page'),
]