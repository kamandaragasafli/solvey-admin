from rest_framework import serializers
from .models import TrackingSession, LocationPoint, StopPoint

class LocationPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPoint
        fields = '__all__'
        read_only_fields = ('id', 'timestamp')

class StopPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopPoint
        fields = '__all__'
        read_only_fields = ('id',)

class TrackingSessionSerializer(serializers.ModelSerializer):
    locations = LocationPointSerializer(many=True, read_only=True)
    stops = StopPointSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = TrackingSession
        fields = '__all__'
        read_only_fields = ('id', 'start_time', 'user')