from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tracking/sessions', views.TrackingSessionViewSet, basename='tracking-session')
router.register(r'tracking/locations', views.LocationPointViewSet, basename='location-point')
router.register(r'tracking/stops', views.StopPointViewSet, basename='stop-point')

urlpatterns = [
    path('', include(router.urls)),
    path('movqe-gonder/', views.tracking_list, name='movqe-gonder'),
]