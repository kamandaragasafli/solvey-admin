from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from .models import TrackingSession, LocationPoint, StopPoint
from .serializers import TrackingSessionSerializer, LocationPointSerializer, StopPointSerializer
from django.views.decorators.csrf import ensure_csrf_cookie

class TrackingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = TrackingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TrackingSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LocationPointViewSet(viewsets.ModelViewSet):
    serializer_class = LocationPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LocationPoint.objects.filter(session__user=self.request.user)

class StopPointViewSet(viewsets.ModelViewSet):
    serializer_class = StopPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return StopPoint.objects.filter(session__user=self.request.user)
    
@ensure_csrf_cookie
def tracking_list(request):
    return render(request, 'xerite/movqe_gonder.html')