from django.urls import path
from .views import RegisterView, LoginAPIView, me, user_management_view, user_activity_view, user_tracking_view

app_name = 'user'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('me/', me, name='user-me'),
    path('management/', user_management_view, name='management'),
    path('activity/', user_activity_view, name='activity'),
    path('tracking/', user_tracking_view, name='tracking'),
]
