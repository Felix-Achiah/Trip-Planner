import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta, time
import math
import logging
from django.utils import timezone

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Constants for HOS regulations
MAX_DRIVING_TIME = 11  # hours
MAX_ON_DUTY_TIME = 14  # hours
MAX_CYCLE_TIME = 70  # hours in 8-day cycle
MANDATORY_BREAK_TIME = 0.5  # 30-minute break
MAX_DRIVING_BEFORE_BREAK = 8  # hours
FUEL_STOP_DURATION = 0.5  # 30 minutes for fueling
MAX_DISTANCE_BEFORE_FUEL = 1000  # miles
PICKUP_DROPOFF_TIME = 1  # hour
MANDATORY_RESET_BREAK = 10  # hours (assumed for resetting the 11-hour driving and 14-hour on-duty limits)
AVERAGE_SPEED = 55  # mph

# Mapping API configuration
MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')

def calculate_route_service(current_location, pickup_location, dropoff_location, current_cycle_hours):
    """
    Calculate route information using the Mapbox Directions API
    
    Args:
        current_location (tuple): (lat, lng) of current location
        pickup_location (tuple): (lat, lng) of pickup location
        dropoff_location (tuple): (lat, lng) of dropoff location
        current_cycle_hours (float): Current cycle hours used
        
    Returns:
        dict: Route data including total distance, driving time, and route details
    """
    # Create waypoints for the route
    waypoints = [
        f"{current_location[1]},{current_location[0]}",  # Format is lng,lat for Mapbox
        f"{pickup_location[1]},{pickup_location[0]}",
        f"{dropoff_location[1]},{dropoff_location[0]}"
    ]
    
    
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{';'.join(waypoints)}"
    params = {
        'access_token': MAPBOX_API_KEY,
        'geometries': 'geojson',
        'overview': 'full',
        'steps': 'true'
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Mapbox API error: {response.status_code} - {response.text}")
    data = response.json()
    if not data.get('routes'):
        raise Exception("No routes found in Mapbox response")
    
    # Extract route data
    route_data = data['routes'][0]
    
    # Convert to miles and hours for the application
    total_distance_miles = route_data['distance'] / 1609.34
    total_driving_time_hours = route_data['duration'] / 3600
    
    # Create segments for easier processing
    segments = []
    for i, leg in enumerate(route_data['legs']):
        segment = {
            'index': i,
            'distance': leg['distance'] / 1609.34,  # Convert to miles
            'duration': leg['duration'] / 3600,  # Convert to hours
            'start_coord': route_data['geometry']['coordinates'][i],
            'end_coord': route_data['geometry']['coordinates'][i+1]
        }
        segments.append(segment)
    
    return {
        'total_distance': total_distance_miles,
        'estimated_driving_time': total_driving_time_hours,
        'route_data': data,
        'segments': segments
    }

def interpolate_coordinates(start_coord, end_coord, fraction):
    """
    Interpolate coordinates along a segment based on the fraction of the distance traveled.
    
    Args:
        start_coord (tuple): Starting coordinates (longitude, latitude)
        end_coord (tuple): Ending coordinates (longitude, latitude)
        fraction (float): Fraction of the distance traveled (0 to 1)
    
    Returns:
        tuple: Interpolated coordinates (longitude, latitude)
    """
    start_lon, start_lat = start_coord
    end_lon, end_lat = end_coord
    interpolated_lon = start_lon + (end_lon - start_lon) * fraction
    interpolated_lat = start_lat + (end_lat - start_lat) * fraction
    return (interpolated_lon, interpolated_lat)

def calculate_rest_stops(route_data, current_cycle_hours):
    """
    Calculate rest stops based on route data and HOS regulations.
    
    Args:
        route_data (dict): Route data from calculate_route_service
        current_cycle_hours (float): Current cycle hours used
        
    Returns:
        list: List of rest stops (rest, fuel, overnight)
    """
    segments = route_data['segments']
    total_distance = route_data['total_distance']
    
    # Start time (should ideally be the trip's start time, but using datetime.now() as per original code)
    current_time = datetime.now()
    remaining_drive_time = MAX_DRIVING_TIME
    remaining_on_duty_time = MAX_ON_DUTY_TIME
    remaining_cycle_time = MAX_CYCLE_TIME - current_cycle_hours
    time_since_break = 0
    distance_since_fuel = 0
    
    rest_stops = []
    current_position = None
    
    logger.info(f"Calculating rest stops: drive_time={remaining_drive_time}, on_duty={remaining_on_duty_time}, cycle={remaining_cycle_time}")
    
    for i, segment in enumerate(segments):
        if i == 0:
            current_position = segment['start_coord']
            # Account for pickup time
            current_time += timedelta(hours=PICKUP_DROPOFF_TIME)
            remaining_on_duty_time -= PICKUP_DROPOFF_TIME
            remaining_cycle_time -= PICKUP_DROPOFF_TIME
            current_position = segment['end_coord']
            if remaining_on_duty_time <= 0 or remaining_cycle_time <= 0:
                # Insert an overnight stop immediately after pickup if HOS limits are exceeded
                rest_stops.append({
                    'name': f"Overnight Rest {len(rest_stops) + 1}",
                    'type': 'overnight',
                    'latitude': current_position[1],
                    'longitude': current_position[0],
                    'estimated_arrival': current_time,
                    'duration': MANDATORY_RESET_BREAK
                })
                current_time += timedelta(hours=MANDATORY_RESET_BREAK)
                remaining_drive_time = MAX_DRIVING_TIME
                remaining_on_duty_time = MAX_ON_DUTY_TIME
                remaining_cycle_time = MAX_CYCLE_TIME  # Reset cycle time after a 10-hour break
                time_since_break = 0
                distance_since_fuel = 0
                logger.info(f"Added overnight stop after pickup due to HOS limits")
        
        possible_distance = segment['distance']
        segment_time = segment['duration']
        start_coord = segment['start_coord']
        end_coord = segment['end_coord']
        distance_covered = 0  # Track distance covered within the segment
        
        logger.info(f"Segment {i}: distance={possible_distance}, time={segment_time}, time_since_break={time_since_break}")
        
        while segment_time > 0:
            # Calculate the time and distance that can be driven before hitting any HOS limit
            time_before_break = max(0, MAX_DRIVING_BEFORE_BREAK - time_since_break)
            time_before_fuel = max(0, (MAX_DISTANCE_BEFORE_FUEL - distance_since_fuel) / AVERAGE_SPEED)
            time_before_drive_limit = max(0, remaining_drive_time)
            time_before_duty_limit = max(0, remaining_on_duty_time)
            time_before_cycle_limit = max(0, remaining_cycle_time)
            
            # Find the earliest limit that will be hit
            drive_time = min(
                segment_time,
                time_before_break,
                time_before_fuel,
                time_before_drive_limit,
                time_before_duty_limit,
                time_before_cycle_limit
            )
            
            if drive_time <= 0:
                # If no driving is possible due to HOS limits, insert an overnight stop
                fraction = distance_covered / possible_distance if possible_distance > 0 else 0
                current_position = interpolate_coordinates(start_coord, end_coord, fraction)
                rest_stops.append({
                    'name': f"Overnight Rest {len(rest_stops) + 1}",
                    'type': 'overnight',
                    'latitude': current_position[1],
                    'longitude': current_position[0],
                    'estimated_arrival': current_time,
                    'duration': MANDATORY_RESET_BREAK
                })
                current_time += timedelta(hours=MANDATORY_RESET_BREAK)
                remaining_drive_time = MAX_DRIVING_TIME
                remaining_on_duty_time = MAX_ON_DUTY_TIME
                remaining_cycle_time = MAX_CYCLE_TIME  # Reset cycle time after a 10-hour break
                time_since_break = 0
                distance_since_fuel = 0
                logger.info(f"Added overnight stop: remaining_segment_time={segment_time}")
                continue
            
            # Drive for the allowed time
            drive_distance = (drive_time / segment_time) * possible_distance if segment_time > 0 else 0
            distance_covered += drive_distance
            fraction = distance_covered / possible_distance if possible_distance > 0 else 0
            current_position = interpolate_coordinates(start_coord, end_coord, fraction)
            
            # Check which limit was hit and insert the appropriate stop
            if time_since_break + drive_time >= MAX_DRIVING_BEFORE_BREAK:
                rest_stops.append({
                    'name': f"Rest Break {len(rest_stops) + 1}",
                    'type': 'rest',
                    'latitude': current_position[1],
                    'longitude': current_position[0],
                    'estimated_arrival': current_time + timedelta(hours=drive_time),
                    'duration': MANDATORY_BREAK_TIME
                })
                current_time += timedelta(hours=drive_time + MANDATORY_BREAK_TIME)
                time_since_break = 0
                remaining_drive_time -= drive_time
                remaining_on_duty_time -= (drive_time + MANDATORY_BREAK_TIME)
                remaining_cycle_time -= drive_time
                distance_since_fuel += drive_distance
                segment_time -= drive_time
                possible_distance -= drive_distance
                logger.info(f"Added rest stop: remaining_segment_time={segment_time}")
            
            elif distance_since_fuel + drive_distance >= MAX_DISTANCE_BEFORE_FUEL:
                rest_stops.append({
                    'name': f"Fuel Stop {len(rest_stops) + 1}",
                    'type': 'fuel',
                    'latitude': current_position[1],
                    'longitude': current_position[0],
                    'estimated_arrival': current_time + timedelta(hours=drive_time),
                    'duration': FUEL_STOP_DURATION
                })
                current_time += timedelta(hours=drive_time + FUEL_STOP_DURATION)
                time_since_break += drive_time
                remaining_drive_time -= drive_time
                remaining_on_duty_time -= (drive_time + FUEL_STOP_DURATION)
                remaining_cycle_time -= drive_time
                distance_since_fuel = 0
                segment_time -= drive_time
                possible_distance -= drive_distance
                logger.info(f"Added fuel stop: remaining_segment_time={segment_time}")
            
            elif (remaining_drive_time <= drive_time or 
                  remaining_on_duty_time <= drive_time or 
                  remaining_cycle_time <= drive_time):
                rest_stops.append({
                    'name': f"Overnight Rest {len(rest_stops) + 1}",
                    'type': 'overnight',
                    'latitude': current_position[1],
                    'longitude': current_position[0],
                    'estimated_arrival': current_time + timedelta(hours=drive_time),
                    'duration': MANDATORY_RESET_BREAK
                })
                current_time += timedelta(hours=drive_time + MANDATORY_RESET_BREAK)
                remaining_drive_time = MAX_DRIVING_TIME
                remaining_on_duty_time = MAX_ON_DUTY_TIME
                remaining_cycle_time = MAX_CYCLE_TIME  # Reset cycle time after a 10-hour break
                time_since_break = 0
                distance_since_fuel = 0
                segment_time -= drive_time
                possible_distance -= drive_distance
                logger.info(f"Added overnight stop: remaining_segment_time={segment_time}")
            
            else:
                # No limits hit, complete the segment
                current_time += timedelta(hours=drive_time)
                time_since_break += drive_time
                remaining_drive_time -= drive_time
                remaining_on_duty_time -= drive_time
                remaining_cycle_time -= drive_time
                distance_since_fuel += drive_distance
                segment_time -= drive_time
                possible_distance -= drive_distance
                current_position = end_coord
                logger.info(f"Completed segment: time_since_break={time_since_break}")
    
    if segments:
        # Account for dropoff time
        remaining_on_duty_time -= PICKUP_DROPOFF_TIME
        remaining_cycle_time -= PICKUP_DROPOFF_TIME
        if remaining_on_duty_time <= 0 or remaining_cycle_time <= 0:
            # Insert an overnight stop after dropoff if HOS limits are exceeded
            rest_stops.append({
                'name': f"Overnight Rest {len(rest_stops) + 1}",
                'type': 'overnight',
                'latitude': current_position[1],
                'longitude': current_position[0],
                'estimated_arrival': current_time,
                'duration': MANDATORY_RESET_BREAK
            })
            current_time += timedelta(hours=MANDATORY_RESET_BREAK)
            remaining_drive_time = MAX_DRIVING_TIME
            remaining_on_duty_time = MAX_ON_DUTY_TIME
            remaining_cycle_time = MAX_CYCLE_TIME
            time_since_break = 0
            distance_since_fuel = 0
            logger.info(f"Added overnight stop after dropoff due to HOS limits")
    
    logger.info(f"Rest stops calculated: {rest_stops}")
    return rest_stops
def generate_eld_logs_service(trip, route, waypoints, current_cycle_hours, user):
    """
    Generate ELD logs for the trip based on pre-calculated waypoints.
    
    Args:
        trip: Trip model instance
        route: Route model instance
        waypoints: QuerySet of Waypoint instances (including rest stops from calculate_rest_stops)
        current_cycle_hours: Current cycle hours used (for reference, not used for enforcement)
        user: The authenticated user (for validation)
        
    Returns:
        dict: ELD log data including log entries and daily logs
        
    Raises:
        ValueError: If the trip does not belong to the user or required waypoints are missing
    """
    # Validate that the trip belongs to the user
    if trip.user != user:
        logger.error(f"User {user.id} attempted to generate logs for trip {trip.id} that does not belong to them")
        raise ValueError("Trip does not belong to the authenticated user")

    # Validate that waypoints belong to the trip's route
    if waypoints.filter(route_id=route.id).count() != waypoints.count():
        logger.error(f"Waypoints provided for trip {trip.id} do not all belong to route {route.id}")
        raise ValueError("Some waypoints do not belong to the trip's route")

    logger.info(f"Generating ELD logs for trip {trip.id} for user {user.id}")

    # Initialize variables
    log_entries = []
    daily_logs = {}
    
    # Ensure trip.start_time is timezone-aware
    trip_start_time = timezone.make_aware(trip.start_time) if not timezone.is_aware(trip.start_time) else trip.start_time
    current_date = trip_start_time.date()
    
    # Initialize daily log for the first day
    daily_logs[current_date] = initialize_daily_log(current_date)
    
    # Convert waypoints to chronological list of events
    events = []
    
    # Add pickup event
    pickup_waypoint = waypoints.filter(waypoint_type='pickup').first()
    if not pickup_waypoint:
        logger.error(f"No pickup waypoint found for trip {trip.id}")
        raise ValueError("No pickup waypoint found for the trip")
    pickup_time = timezone.make_aware(pickup_waypoint.estimated_arrival) if not timezone.is_aware(pickup_waypoint.estimated_arrival) else pickup_waypoint.estimated_arrival
    events.append({
        'type': 'pickup',
        'time': pickup_time,
        'duration': pickup_waypoint.planned_duration,
        'location': pickup_waypoint.location
    })
    
    # Add all rest stops, fuel stops, overnight stops, and mandatory breaks
    for waypoint in waypoints.filter(waypoint_type__in=['rest', 'fuel', 'overnight', 'mandatory_break']).order_by('estimated_arrival'):
        waypoint_time = timezone.make_aware(waypoint.estimated_arrival) if not timezone.is_aware(waypoint.estimated_arrival) else waypoint.estimated_arrival
        events.append({
            'type': waypoint.waypoint_type,
            'time': waypoint_time,
            'duration': waypoint.planned_duration,
            'location': waypoint.location
        })
    
    # Add dropoff event
    dropoff_waypoint = waypoints.filter(waypoint_type='dropoff').first()
    if not dropoff_waypoint:
        logger.error(f"No dropoff waypoint found for trip {trip.id}")
        raise ValueError("No dropoff waypoint found for the trip")
    dropoff_time = timezone.make_aware(dropoff_waypoint.estimated_arrival) if not timezone.is_aware(dropoff_waypoint.estimated_arrival) else dropoff_waypoint.estimated_arrival
    events.append({
        'type': 'dropoff',
        'time': dropoff_time,
        'duration': dropoff_waypoint.planned_duration,
        'location': dropoff_waypoint.location
    })
    
    # Sort events by time
    events.sort(key=lambda x: x['time'])
    logger.info(f"Events to process: {events}")

    # Initialize status tracking
    current_status = 'off_duty'
    status_start_time = trip_start_time
    
    # Process each event chronologically
    for i, event in enumerate(events):
        logger.info(f"Processing event {i}: {event}")
        
        # If this is the first event, add driving time from trip start to first event
        if i == 0 and event['type'] == 'pickup':
            driving_duration = (event['time'] - trip.start_time).total_seconds() / 3600
            logger.info(f"Initial driving duration: {driving_duration} hours")
            if driving_duration > 0:
                current_time = trip.start_time
                while current_time < event['time']:
                    current_date = current_time.date()
                    if current_date not in daily_logs:
                        daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                    next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                    end_segment = min(next_day, event['time'])
                    segment_duration = (end_segment - current_time).total_seconds() / 3600
                    
                    log_entries.append({
                        'start_time': current_time,
                        'end_time': end_segment,
                        'status': 'driving',
                        'location_id': trip.current_location.id if hasattr(trip.current_location, 'id') else None,
                        'notes': "Driving to pickup location"
                    })
                    daily_logs[current_date]['total_driving_hours'] += segment_duration
                    daily_logs[current_date]['total_on_duty_hours'] += segment_duration  # Driving counts as on-duty
                    update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                    logger.info(f"Added initial driving on {current_date}: {segment_duration} hours")
                    current_time = end_segment
            current_status = 'driving'
            status_start_time = event['time']
        
        # Process driving time before the event (if any)
        if current_status and status_start_time and event['time'] > status_start_time:
            duration = (event['time'] - status_start_time).total_seconds() / 3600
            if duration > 0:
                current_time = status_start_time
                while current_time < event['time']:
                    current_date = current_time.date()
                    if current_date not in daily_logs:
                        daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                    next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                    end_segment = min(next_day, event['time'])
                    segment_duration = (end_segment - current_time).total_seconds() / 3600
                    
                    log_entries.append({
                        'start_time': current_time,
                        'end_time': end_segment,
                        'status': current_status,
                        'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                        'notes': f"En route to {event['type']}"
                    })
                    if current_status == 'driving':
                        daily_logs[current_date]['total_driving_hours'] += segment_duration
                        daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                        update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                        logger.info(f"Added driving before {event['type']} on {current_date}: {segment_duration} hours")
                    current_time = end_segment
        
        # Process the event based on its type
        if event['type'] == 'pickup':
            current_status = 'on_duty_not_driving'
            status_start_time = event['time']
            event_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, event_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'on_duty_not_driving',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'activity': 'Loading',
                    'notes': "Loading at pickup location"
                })
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'on_duty_not_driving')
                current_time = end_segment
            current_status = 'driving'
            status_start_time = event_end_time
        
        elif event['type'] in ['rest', 'fuel', 'mandatory_break']:
            current_status = 'off_duty'
            status_start_time = event['time']
            event_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, event_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'off_duty',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'notes': f"{event['type'].capitalize()} stop"
                })
                daily_logs[current_date]['total_off_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'off_duty')
                current_time = end_segment
            current_status = 'driving'
            status_start_time = event_end_time
        
        elif event['type'] == 'overnight':
            current_status = 'sleeper_berth'
            status_start_time = event['time']
            event_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, event_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'sleeper_berth',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'notes': "Overnight stop"
                })
                daily_logs[current_date]['total_sleeper_berth_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'sleeper_berth')
                current_time = end_segment
            current_status = 'driving'
            status_start_time = event_end_time
        
        elif event['type'] == 'dropoff':
            current_status = 'on_duty_not_driving'
            status_start_time = event['time']
            event_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, event_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'on_duty_not_driving',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'activity': 'Unloading',
                    'notes': "Unloading at delivery location"
                })
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'on_duty_not_driving')
                current_time = end_segment
            current_status = 'off_duty'
            status_start_time = event_end_time
    
    # Finalize daily logs
    daily_logs_list = []
    for date in sorted(daily_logs.keys()):
        daily_log = daily_logs[date]
        daily_log['ending_odometer'] = calculate_odometer(daily_log['starting_odometer'], daily_log['total_driving_hours'])
        daily_logs_list.append(daily_log)
    
    total_on_duty_hours = sum(log['total_on_duty_hours'] for log in daily_logs_list)
    logger.info(f"Generated {len(log_entries)} log entries and {len(daily_logs_list)} daily logs for trip {trip.id}")
    
    return {
        'message': "ELD logs generated successfully",
        'total_on_duty_hours': total_on_duty_hours,
        'daily_logs': daily_logs_list,
        'log_entries': log_entries,
    }

def initialize_log_grid():
    """Initialize a log grid with 15-minute intervals for a 24-hour day."""
    return [{'time': minute, 'status': None} for minute in range(0, 1440, 15)]

def update_log_grid(log_data, start_time, end_time, status):
    """Update the log grid with the given status between start_time and end_time."""
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if start_time.date() != end_time.date():
        end_minutes = 1440  # End of the day for start_time's date
    
    start_index = start_minutes // 15
    end_index = end_minutes // 15
    
    for i in range(start_index, min(end_index, len(log_data))):
        log_data[i]['status'] = status

def calculate_odometer(starting_odometer, driving_hours):
    """Calculate the ending odometer based on driving hours (assuming 55 mph)."""
    miles_driven = driving_hours * AVERAGE_SPEED
    return int(starting_odometer + miles_driven)

def initialize_daily_log(current_date, previous_date=None, daily_logs=None):
    """Helper function to initialize a daily log entry with all required keys."""
    starting_odometer = 0
    if previous_date and daily_logs and previous_date in daily_logs:
        starting_odometer = daily_logs[previous_date]['ending_odometer']
    
    return {
        'date': current_date,
        'starting_odometer': starting_odometer,
        'ending_odometer': 0,
        'total_driving_hours': 0,
        'total_on_duty_hours': 0,
        'total_off_duty_hours': 0,
        'total_sleeper_berth_hours': 0,
        'log_data': initialize_log_grid()
    }