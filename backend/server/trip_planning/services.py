import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta, time
import math
import logging
from django.utils import timezone as django_timezone

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

def calculate_rest_stops(route_data, current_cycle_hours, trip_start_time):
    """
    Calculate rest stops based on route data and HOS regulations.
    
    Args:
        route_data (dict): Route data from calculate_route_service
        current_cycle_hours (float): Current cycle hours used
        trip_start_time (datetime): The trip's start time
        
    Returns:
        list: List of rest stops (rest, fuel, overnight)
    """
    segments = route_data['segments']
    total_distance = route_data['total_distance']
    total_driving_time = route_data['estimated_driving_time']  # Total driving time for the trip
    
    # Ensure trip_start_time is timezone-aware
    current_time = trip_start_time
    if not django_timezone.is_aware(current_time):
        current_time = django_timezone.make_aware(current_time, timezone=django_timezone.utc)

    remaining_drive_time = MAX_DRIVING_TIME  # 11 hours
    remaining_on_duty_time = MAX_ON_DUTY_TIME  # 14 hours
    remaining_cycle_time = MAX_CYCLE_TIME - current_cycle_hours
    time_since_break = 0
    distance_since_fuel = 0
    total_time_processed = 0  # Track total driving time processed
    
    rest_stops = []
    current_position = None
    
    logger.info(f"Calculating rest stops: total_driving_time={total_driving_time}, drive_time={remaining_drive_time}, on_duty={remaining_on_duty_time}, cycle={remaining_cycle_time}")
    
    # Process pickup time
    current_position = segments[0]['start_coord']
    current_time += timedelta(hours=PICKUP_DROPOFF_TIME)
    remaining_on_duty_time -= PICKUP_DROPOFF_TIME
    remaining_cycle_time -= PICKUP_DROPOFF_TIME
    current_position = segments[0]['end_coord']
    if remaining_on_duty_time <= 0 or remaining_cycle_time <= 0:
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
        logger.info(f"Added overnight stop after pickup due to HOS limits")

    # Process the entire trip duration
    remaining_trip_time = total_driving_time
    segment_index = 0
    distance_covered = 0
    total_distance_covered = 0

    while remaining_trip_time > 0:
        # Determine the current segment (if any) for coordinate interpolation
        if segment_index < len(segments):
            current_segment = segments[segment_index]
            segment_distance = current_segment['distance']
            segment_time = current_segment['duration']
            start_coord = current_segment['start_coord']
            end_coord = current_segment['end_coord']
        else:
            # If we've processed all segments, continue with the last position
            segment_distance = total_distance - total_distance_covered
            segment_time = remaining_trip_time
            start_coord = current_position
            end_coord = current_position  # No further movement in coordinates

        # Calculate how much time we can drive before hitting a limit
        time_before_break = max(0, MAX_DRIVING_BEFORE_BREAK - time_since_break)
        time_before_fuel = max(0, (MAX_DISTANCE_BEFORE_FUEL - distance_since_fuel) / AVERAGE_SPEED)
        time_before_drive_limit = max(0, remaining_drive_time)
        time_before_duty_limit = max(0, remaining_on_duty_time)
        time_before_cycle_limit = max(0, remaining_cycle_time)

        drive_time = min(
            remaining_trip_time,
            time_before_break,
            time_before_fuel,
            time_before_drive_limit,
            time_before_duty_limit,
            time_before_cycle_limit
        )

        if drive_time <= 0:
            fraction = distance_covered / segment_distance if segment_distance > 0 else 0
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
            remaining_cycle_time = MAX_CYCLE_TIME
            time_since_break = 0
            distance_since_fuel = 0
            logger.info(f"Added overnight stop: remaining_trip_time={remaining_trip_time}")
            continue

        # Calculate distance driven in this period
        drive_distance = (drive_time / total_driving_time) * total_distance if total_driving_time > 0 else 0
        distance_covered += drive_distance
        total_distance_covered += drive_distance
        fraction = distance_covered / segment_distance if segment_distance > 0 else 0
        current_position = interpolate_coordinates(start_coord, end_coord, fraction)

        # Check if we need a rest break (after 8 hours of driving)
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
            remaining_trip_time -= drive_time
            total_time_processed += drive_time
            logger.info(f"Added rest stop: remaining_trip_time={remaining_trip_time}")

        # Check if we need a fuel stop (every 1000 miles)
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
            remaining_trip_time -= drive_time
            total_time_processed += drive_time
            logger.info(f"Added fuel stop: remaining_trip_time={remaining_trip_time}")

        # Check if we hit HOS limits (11-hour driving, 14-hour on-duty, or 70-hour cycle)
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
            remaining_cycle_time = MAX_CYCLE_TIME
            time_since_break = 0
            distance_since_fuel = 0
            remaining_trip_time -= drive_time
            total_time_processed += drive_time
            logger.info(f"Added overnight stop: remaining_trip_time={remaining_trip_time}")

        else:
            current_time += timedelta(hours=drive_time)
            time_since_break += drive_time
            remaining_drive_time -= drive_time
            remaining_on_duty_time -= drive_time
            remaining_cycle_time -= drive_time
            distance_since_fuel += drive_distance
            remaining_trip_time -= drive_time
            total_time_processed += drive_time
            current_position = end_coord
            logger.info(f"Processed driving time: time_since_break={time_since_break}, remaining_trip_time={remaining_trip_time}")

        # Move to the next segment if we've covered the current segment's distance
        if segment_index < len(segments) and distance_covered >= segment_distance:
            segment_index += 1
            distance_covered = 0

    # Account for dropoff time at the end of the trip
    remaining_on_duty_time -= PICKUP_DROPOFF_TIME
    remaining_cycle_time -= PICKUP_DROPOFF_TIME
    if remaining_on_duty_time <= 0 or remaining_cycle_time <= 0:
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
    current_odometer = 0
    
    # Ensure trip.start_time is timezone-aware
    trip_start_time = django_timezone.make_aware(trip.start_time) if not django_timezone.is_aware(trip.start_time) else trip.start_time
    current_time = trip_start_time
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
    pickup_time = django_timezone.make_aware(pickup_waypoint.estimated_arrival) if not django_timezone.is_aware(pickup_waypoint.estimated_arrival) else pickup_waypoint.estimated_arrival
    events.append({
        'type': 'pickup',
        'time': pickup_time,
        'duration': pickup_waypoint.planned_duration,
        'location': pickup_waypoint.location
    })
    
    # Add all rest stops, fuel stops, overnight stops, and mandatory breaks
    for waypoint in waypoints.filter(waypoint_type__in=['rest', 'fuel', 'overnight']).order_by('estimated_arrival'):
        waypoint_time = django_timezone.make_aware(waypoint.estimated_arrival) if not django_timezone.is_aware(waypoint.estimated_arrival) else waypoint.estimated_arrival
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
    dropoff_time = django_timezone.make_aware(dropoff_waypoint.estimated_arrival) if not django_timezone.is_aware(dropoff_waypoint.estimated_arrival) else dropoff_waypoint.estimated_arrival
    events.append({
        'type': 'dropoff',
        'time': dropoff_time,
        'duration': dropoff_waypoint.planned_duration,
        'location': dropoff_waypoint.location
    })
    
    # Sort events by time
    events.sort(key=lambda x: x['time'])
    logger.info(f"Events to process: {events}")

    # Initialize HOS tracking
    remaining_drive_time = MAX_DRIVING_TIME
    remaining_on_duty_time = MAX_ON_DUTY_TIME
    time_since_break = 0
    
    # Process each event chronologically
    for i, event in enumerate(events):
        logger.info(f"Processing event {i}: {event}")
        
        # Calculate driving time to this event (if not the first event)
        if i > 0:
            prev_event = events[i - 1]
            prev_end_time = prev_event['time'] + timedelta(hours=prev_event['duration'])
            driving_duration = (event['time'] - prev_end_time).total_seconds() / 3600.0  # in hours
            
            if driving_duration > 0:
                # Apply HOS limits to driving period
                time_before_break = max(0, MAX_DRIVING_BEFORE_BREAK - time_since_break)
                time_before_drive_limit = max(0, remaining_drive_time)
                time_before_duty_limit = max(0, remaining_on_duty_time)
                
                remaining_driving = driving_duration
                current_segment_start = prev_end_time
                
                while remaining_driving > 0:
                    drive_time = min(
                        remaining_driving,
                        time_before_break,
                        time_before_drive_limit,
                        time_before_duty_limit
                    )
                    
                    if drive_time <= 0:
                        # Should have been handled by calculate_rest_stops, log an error
                        logger.error(f"HOS limit reached without a rest stop: drive_time={remaining_drive_time}, on_duty={remaining_on_duty_time}")
                        break
                    
                    drive_end_time = current_segment_start + timedelta(hours=drive_time)
                    log_entries.append({
                        'start_time': current_segment_start,
                        'end_time': drive_end_time,
                        'status': 'driving',
                        'location_id': prev_event['location'].id if hasattr(prev_event['location'], 'id') else None,
                        'notes': f"Driving to {event['type']}"
                    })
                    
                    # Update daily logs for this driving period
                    current_time_temp = current_segment_start
                    while current_time_temp < drive_end_time:
                        current_date = current_time_temp.date()
                        if current_date not in daily_logs:
                            daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                        next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time_temp.tzinfo)
                        segment_end = min(next_day, drive_end_time)
                        segment_duration = (segment_end - current_time_temp).total_seconds() / 3600.0
                        daily_logs[current_date]['total_driving_hours'] += segment_duration
                        daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                        update_log_grid(daily_logs[current_date]['log_data'], current_time_temp, segment_end, 'driving')
                        current_odometer += segment_duration * AVERAGE_SPEED
                        current_time_temp = segment_end
                    
                    time_since_break += drive_time
                    remaining_drive_time -= drive_time
                    remaining_on_duty_time -= drive_time
                    remaining_driving -= drive_time
                    current_segment_start = drive_end_time
        
        # Process the event itself
        event_end_time = event['time'] + timedelta(hours=event['duration'])
        if event['type'] == 'pickup':
            log_entries.append({
                'start_time': event['time'],
                'end_time': event_end_time,
                'status': 'on_duty_not_driving',
                'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                'activity': 'Loading',
                'notes': "Loading at pickup location"
            })
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                segment_end = min(next_day, event_end_time)
                segment_duration = (segment_end - current_time).total_seconds() / 3600.0
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, segment_end, 'on_duty_not_driving')
                current_time = segment_end
            remaining_on_duty_time -= event['duration']
        
        elif event['type'] in ['rest', 'fuel']:
            log_entries.append({
                'start_time': event['time'],
                'end_time': event_end_time,
                'status': 'off_duty',
                'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                'notes': f"{event['type'].capitalize()} stop"
            })
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                segment_end = min(next_day, event_end_time)
                segment_duration = (segment_end - current_time).total_seconds() / 3600.0
                daily_logs[current_date]['total_off_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, segment_end, 'off_duty')
                current_time = segment_end
            time_since_break = 0
            remaining_on_duty_time -= event['duration']
        
        elif event['type'] == 'overnight':
            log_entries.append({
                'start_time': event['time'],
                'end_time': event_end_time,
                'status': 'sleeper_berth',
                'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                'notes': "Overnight stop"
            })
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                segment_end = min(next_day, event_end_time)
                segment_duration = (segment_end - current_time).total_seconds() / 3600.0
                daily_logs[current_date]['total_sleeper_berth_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, segment_end, 'sleeper_berth')
                current_time = segment_end
            remaining_drive_time = MAX_DRIVING_TIME
            remaining_on_duty_time = MAX_ON_DUTY_TIME
            time_since_break = 0
        
        elif event['type'] == 'dropoff':
            log_entries.append({
                'start_time': event['time'],
                'end_time': event_end_time,
                'status': 'on_duty_not_driving',
                'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                'activity': 'Unloading',
                'notes': "Unloading at delivery location"
            })
            current_time = event['time']
            while current_time < event_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                segment_end = min(next_day, event_end_time)
                segment_duration = (segment_end - current_time).total_seconds() / 3600.0
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, segment_end, 'on_duty_not_driving')
                current_time = segment_end
            remaining_on_duty_time -= event['duration']
    
    # Finalize daily logs
    daily_logs_list = []
    for date in sorted(daily_logs.keys()):
        daily_log = daily_logs[date]
        daily_log['ending_odometer'] = current_odometer
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