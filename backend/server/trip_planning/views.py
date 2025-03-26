from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

from .models import Trip, Route, Location, Waypoint, LogEntry, DailyLog
from .serializers import (
    TripSerializer, RouteSerializer, LocationSerializer, 
    WaypointSerializer, LogEntrySerializer, DailyLogSerializer
)
from .services import (
    calculate_route_service,
    generate_eld_logs_service,
    calculate_rest_stops
)

# Load environment variables
load_dotenv()

class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for Location CRUD operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = LocationSerializer

    def get_queryset(self):
        """
        Filter locations to only those associated with the authenticated user's trips.
        This includes current_location, pickup_location, dropoff_location, and waypoints.
        """
        user = self.request.user
        # Get locations associated with the user's trips
        trip_locations = Location.objects.filter(
            id__in=Trip.objects.filter(user=user).values_list(
                'current_location_id', 'pickup_location_id', 'dropoff_location_id'
            )
        )
        # Get locations associated with waypoints of the user's trips
        waypoint_locations = Location.objects.filter(
            id__in=Waypoint.objects.filter(
                route__trip__user=user
            ).values_list('location_id')
        )
        # Combine the two querysets using | (union)
        return trip_locations | waypoint_locations

    @action(detail=False, methods=['post'])
    def geocode(self, request):
        """Convert address to lat/long using geocoding API"""
        address = request.data.get('address')
        if not address:
            return Response({'error': 'Address is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json?access_token={MAPBOX_API_KEY}"
            response = requests.get(url)
            data = response.json()
            
            if data['features']:
                feature = data['features'][0]
                longitude, latitude = feature['center']
                place_name = feature['place_name']
                
                return Response({
                    'latitude': latitude,
                    'longitude': longitude,
                    'address': place_name
                })
            return Response({'error': 'Location not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TripViewSet(viewsets.ModelViewSet):
    """ViewSet for Trip CRUD operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = TripSerializer

    def get_queryset(self):
        """
        Filter trips to only those belonging to the authenticated user.
        """
        return Trip.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Automatically set the user field to the authenticated user when creating a trip.
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def calculate_route(self, request, pk=None):
        trip = self.get_object()  # This will automatically respect the user filter
        
        try:
            route_data = calculate_route_service(
                current_location=(trip.current_location.latitude, trip.current_location.longitude),
                pickup_location=(trip.pickup_location.latitude, trip.pickup_location.longitude),
                dropoff_location=(trip.dropoff_location.latitude, trip.dropoff_location.longitude),
                current_cycle_hours=trip.current_cycle_hours
            )
        except Exception as e:
            return Response({'error': f'Route calculation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        route, created = Route.objects.get_or_create(
            trip=trip,
            defaults={
                'total_distance': route_data['total_distance'],
                'estimated_driving_time': route_data['estimated_driving_time'],
                'route_data': route_data['route_data']
            }
        )
        
        if not created:
            route.total_distance = route_data['total_distance']
            route.estimated_driving_time = route_data['estimated_driving_time']
            route.route_data = route_data['route_data']
            route.save()
        
        try:
            route.waypoints.all().delete()
            rest_stops = calculate_rest_stops(route_data=route_data, current_cycle_hours=trip.current_cycle_hours)
            
            sequence = 0
            Waypoint.objects.create(
                route=route,
                location=trip.pickup_location,
                waypoint_type='pickup',
                sequence=sequence,
                estimated_arrival=trip.start_time,
                planned_duration=1.0
            )
            sequence += 1
            
            for stop in rest_stops:
                stop_location = Location.objects.create(
                    name=stop['name'],
                    latitude=stop['latitude'],
                    longitude=stop['longitude'],
                    address=stop.get('address', '')
                )
                Waypoint.objects.create(
                    route=route,
                    location=stop_location,
                    waypoint_type=stop['type'],
                    sequence=sequence,
                    estimated_arrival=stop['estimated_arrival'],
                    planned_duration=stop['duration']
                )
                sequence += 1
            
            if rest_stops:
                last_stop_duration = rest_stops[-1]['duration']
                last_arrival = rest_stops[-1]['estimated_arrival']
            else:
                last_stop_duration = 0
                last_arrival = trip.start_time + timedelta(hours=route_data['segments'][0]['duration']/3600 + 1)  # Pickup duration
            
            final_segment_duration = route_data['segments'][-1]['duration'] / 3600
            final_eta = last_arrival + timedelta(hours=last_stop_duration + final_segment_duration)
            
            Waypoint.objects.create(
                route=route,
                location=trip.dropoff_location,
                waypoint_type='dropoff',
                sequence=sequence,
                estimated_arrival=final_eta,
                planned_duration=1.0
            )
            
            trip.estimated_end_time = final_eta + timedelta(hours=1)
            trip.save()
            
            return Response(RouteSerializer(route).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def generate_logs(self, request, pk=None):
        """Generate ELD logs for the trip"""
        trip = self.get_object()  # This will automatically respect the user filter
        
        try:
            # Ensure route has been calculated
            if not hasattr(trip, 'route'):
                return Response(
                    {'error': 'Route must be calculated before generating logs'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete existing logs
            trip.log_entries.all().delete()
            trip.daily_logs.all().delete()
            
            # Call service to generate logs, passing the authenticated user
            logs_data = generate_eld_logs_service(
                trip=trip,
                route=trip.route,
                waypoints=trip.route.waypoints.all(),
                current_cycle_hours=trip.current_cycle_hours,
                user=request.user  # Pass the authenticated user
            )
            
            # Create log entries
            for log_entry in logs_data['log_entries']:
                LogEntry.objects.create(
                    trip=trip,
                    start_time=log_entry['start_time'],
                    end_time=log_entry['end_time'],
                    status=log_entry['status'],
                    location_id=log_entry.get('location_id'),
                    activity=log_entry.get('activity'),
                    notes=log_entry.get('notes')
                )
            
            # Create daily logs
            for daily_log in logs_data['daily_logs']:
                DailyLog.objects.create(
                    trip=trip,
                    date=daily_log['date'],
                    starting_odometer=daily_log.get('starting_odometer'),
                    ending_odometer=daily_log.get('ending_odometer'),
                    total_driving_hours=daily_log['total_driving_hours'],
                    total_on_duty_hours=daily_log['total_on_duty_hours'],
                    total_off_duty_hours=daily_log['total_off_duty_hours'],
                    total_sleeper_berth_hours=daily_log['total_sleeper_berth_hours'],
                    log_data=daily_log['log_data']
                )
            
            return Response({
                'message': 'ELD logs generated successfully',
                'daily_logs': DailyLogSerializer(trip.daily_logs.all(), many=True).data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving Route information"""
    permission_classes = [IsAuthenticated]
    serializer_class = RouteSerializer

    def get_queryset(self):
        """
        Filter routes to only those associated with the authenticated user's trips.
        """
        return Route.objects.filter(trip__user=self.request.user)


class WaypointViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving Waypoint information"""
    permission_classes = [IsAuthenticated]
    serializer_class = WaypointSerializer

    def get_queryset(self):
        """
        Filter waypoints to only those associated with the authenticated user's trips.
        Optionally filter by route_id if provided in query params.
        """
        queryset = Waypoint.objects.filter(route__trip__user=self.request.user)
        route_id = self.request.query_params.get('route', None)
        if route_id:
            queryset = queryset.filter(route_id=route_id)
        return queryset


class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving LogEntry information"""
    permission_classes = [IsAuthenticated]
    serializer_class = LogEntrySerializer

    def get_queryset(self):
        """
        Filter log entries to only those associated with the authenticated user's trips.
        Optionally filter by trip_id if provided in query params.
        """
        queryset = LogEntry.objects.filter(trip__user=self.request.user)
        trip_id = self.request.query_params.get('trip', None)
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)
        return queryset


class DailyLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for retrieving DailyLog information"""
    permission_classes = [IsAuthenticated]
    serializer_class = DailyLogSerializer

    def get_queryset(self):
        """
        Filter daily logs to only those associated with the authenticated user's trips.
        Optionally filter by trip_id if provided in query params.
        """
        queryset = DailyLog.objects.filter(trip__user=self.request.user)
        trip_id = self.request.query_params.get('trip', None)
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)
        return queryset