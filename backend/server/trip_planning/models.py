# models.py
import uuid
from django.conf import settings
from django.db import models


class Location(models.Model):
    """Model to store location details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name


class Trip(models.Model):
    """Model to store trip details"""
    STATUS_CHOICES = (
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Locations
    current_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='current_trips')
    pickup_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='pickup_trips')
    dropoff_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='dropoff_trips')
    
    # Trip timing and HOS details
    start_time = models.DateTimeField()
    estimated_end_time = models.DateTimeField(null=True, blank=True)
    current_cycle_hours = models.FloatField(help_text="Current cycle hours used (in hours)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d')}"


class Route(models.Model):
    """Model to store calculated route details"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='route')
    total_distance = models.FloatField(help_text="Total distance in miles")
    estimated_driving_time = models.FloatField(help_text="Estimated driving time in hours")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    route_data = models.JSONField(help_text="Complete route data from mapping API")
    
    def __str__(self):
        return f"Route for {self.trip.title}"


class Waypoint(models.Model):
    """Model to store waypoints along the route"""
    WAYPOINT_TYPES = (
        ('rest', 'Rest Stop'),
        ('fuel', 'Fuel Stop'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('overnight', 'Overnight Rest'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='waypoints')
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    waypoint_type = models.CharField(max_length=20, choices=WAYPOINT_TYPES)
    sequence = models.IntegerField(help_text="Order in the route")
    
    # Timing details
    estimated_arrival = models.DateTimeField()
    planned_duration = models.FloatField(help_text="Planned duration at this waypoint in hours")
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.get_waypoint_type_display()} at {self.location.name}"


class LogEntry(models.Model):
    """Model to store ELD log entries"""
    LOG_STATUS_CHOICES = (
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty Not Driving'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='log_entries')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=LOG_STATUS_CHOICES)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    
    # For on_duty_not_driving status
    activity = models.CharField(max_length=255, blank=True, null=True, 
                               help_text="Description of activity (loading, unloading, etc.)")
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.get_status_display()} - {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')}"
    
    @property
    def duration(self):
        """Return duration in hours"""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600


class DailyLog(models.Model):
    """Model to represent a daily log sheet"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField()
    starting_odometer = models.IntegerField(null=True, blank=True)
    ending_odometer = models.IntegerField(null=True, blank=True)
    
    # Daily totals
    total_driving_hours = models.FloatField(default=0)
    total_on_duty_hours = models.FloatField(default=0)
    total_off_duty_hours = models.FloatField(default=0)
    total_sleeper_berth_hours = models.FloatField(default=0)
    
    # Log visualization data (JSON representation of the grid)
    log_data = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"Daily Log for {self.trip.title} - {self.date}"