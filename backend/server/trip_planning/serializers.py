# serializers.py

from rest_framework import serializers
from .models import Trip, Route, Location, Waypoint, LogEntry, DailyLog


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'address']


class WaypointSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    
    class Meta:
        model = Waypoint
        fields = [
            'id', 'route', 'location', 'waypoint_type', 'sequence',
            'estimated_arrival', 'planned_duration', 'notes'
        ]


class RouteSerializer(serializers.ModelSerializer):
    waypoints = WaypointSerializer(many=True, read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'trip', 'total_distance', 'estimated_driving_time',
            'created_at', 'updated_at', 'route_data', 'waypoints'
        ]


class LogEntrySerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    duration = serializers.FloatField(read_only=True)
    
    class Meta:
        model = LogEntry
        fields = [
            'id', 'trip', 'start_time', 'end_time', 'status', 
            'location', 'activity', 'notes', 'duration'
        ]


class DailyLogSerializer(serializers.ModelSerializer):
    trip_title = serializers.SerializerMethodField()
    class Meta:
        model = DailyLog
        fields = [
            'id', 'trip', 'trip_title', 'date', 'starting_odometer', 'ending_odometer',
            'total_driving_hours', 'total_on_duty_hours', 
            'total_off_duty_hours', 'total_sleeper_berth_hours',
            'log_data'
        ]

    def get_trip_title(self, obj):
        return obj.trip.title if obj.trip else None

class TripSerializer(serializers.ModelSerializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    route = RouteSerializer(read_only=True)
    daily_logs = DailyLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'id', 'user', 'title', 'created_at', 'updated_at',
            'current_location', 'pickup_location', 'dropoff_location',
            'start_time', 'estimated_end_time', 'current_cycle_hours',
            'status', 'notes', 'route', 'daily_logs'
        ]
    
    def create(self, validated_data):
        # Extract nested location data
        current_location_data = validated_data.pop('current_location')
        pickup_location_data = validated_data.pop('pickup_location')
        dropoff_location_data = validated_data.pop('dropoff_location')
        
        # Create or update locations
        current_location, _ = Location.objects.get_or_create(**current_location_data)
        pickup_location, _ = Location.objects.get_or_create(**pickup_location_data)
        dropoff_location, _ = Location.objects.get_or_create(**dropoff_location_data)
        
        # Create trip with location references
        trip = Trip.objects.create(
            current_location=current_location,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            **validated_data
        )
        
        return trip
    
    def update(self, instance, validated_data):
        # Handle nested location data if present
        if 'current_location' in validated_data:
            current_location_data = validated_data.pop('current_location')
            current_location, _ = Location.objects.get_or_create(**current_location_data)
            instance.current_location = current_location
        
        if 'pickup_location' in validated_data:
            pickup_location_data = validated_data.pop('pickup_location')
            pickup_location, _ = Location.objects.get_or_create(**pickup_location_data)
            instance.pickup_location = pickup_location
        
        if 'dropoff_location' in validated_data:
            dropoff_location_data = validated_data.pop('dropoff_location')
            dropoff_location, _ = Location.objects.get_or_create(**dropoff_location_data)
            instance.dropoff_location = dropoff_location
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance