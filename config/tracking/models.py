from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TrackingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_distance = models.FloatField(default=0)  # metr
    total_duration = models.FloatField(default=0)  # saniyə
    
    def __str__(self):
        return f"{self.user.username} - {self.start_time}"

class LocationPoint(models.Model):
    session = models.ForeignKey(TrackingSession, on_delete=models.CASCADE, related_name='locations')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    speed = models.FloatField(default=0)  # m/s
    
    def __str__(self):
        return f"{self.latitude}, {self.longitude}"

class StopPoint(models.Model):
    session = models.ForeignKey(TrackingSession, on_delete=models.CASCADE, related_name='stops')
    latitude = models.FloatField()
    longitude = models.FloatField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.FloatField()  # saniyə
    
    def __str__(self):
        return f"Stop: {self.duration}s"