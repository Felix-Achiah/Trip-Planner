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
            current_time += timedelta(hours=PICKUP_DROPOFF_TIME)
            remaining_on_duty_time -= PICKUP_DROPOFF_TIME
            remaining_cycle_time -= PICKUP_DROPOFF_TIME
            current_position = segment['end_coord']
        
        possible_distance = segment['distance']
        segment_time = segment['duration']
        
        logger.info(f"Segment {i}: distance={possible_distance}, time={segment_time}, time_since_break={time_since_break}")
        
        while segment_time > 0:
            if time_since_break + segment_time > MAX_DRIVING_BEFORE_BREAK:
                drive_time_before_break = MAX_DRIVING_BEFORE_BREAK - time_since_break
                drive_distance_before_break = (drive_time_before_break / segment['duration']) * possible_distance
                
                rest_stops.append({
                    'name': f"Rest Break {len(rest_stops) + 1}",
                    'type': 'rest',
                    'latitude': segment['start_coord'][1],
                    'longitude': segment['start_coord'][0],
                    'estimated_arrival': current_time + timedelta(hours=drive_time_before_break),
                    'duration': MANDATORY_BREAK_TIME
                })
                
                current_time += timedelta(hours=drive_time_before_break + MANDATORY_BREAK_TIME)
                time_since_break = 0
                remaining_on_duty_time -= (drive_time_before_break + MANDATORY_BREAK_TIME)
                remaining_cycle_time -= drive_time_before_break
                distance_since_fuel += drive_distance_before_break
                segment_time -= drive_time_before_break
                possible_distance -= drive_distance_before_break
                logger.info(f"Added rest stop: remaining_segment_time={segment_time}")
            
            elif distance_since_fuel + possible_distance > MAX_DISTANCE_BEFORE_FUEL:
                distance_before_fuel = MAX_DISTANCE_BEFORE_FUEL - distance_since_fuel
                time_before_fuel = (distance_before_fuel / possible_distance) * segment_time
                
                rest_stops.append({
                    'name': f"Fuel Stop {len(rest_stops) + 1}",
                    'type': 'fuel',
                    'latitude': segment['start_coord'][1],
                    'longitude': segment['start_coord'][0],
                    'estimated_arrival': current_time + timedelta(hours=time_before_fuel),
                    'duration': FUEL_STOP_DURATION
                })
                
                current_time += timedelta(hours=time_before_fuel + FUEL_STOP_DURATION)
                time_since_break += time_before_fuel
                remaining_on_duty_time -= (time_before_fuel + FUEL_STOP_DURATION)
                remaining_cycle_time -= (time_before_fuel + FUEL_STOP_DURATION)
                distance_since_fuel = 0
                segment_time -= time_before_fuel
                possible_distance -= distance_before_fuel
                logger.info(f"Added fuel stop: remaining_segment_time={segment_time}")
            
            elif remaining_on_duty_time < segment_time or remaining_drive_time < segment_time:
                rest_stops.append({
                    'name': f"Overnight Rest {len(rest_stops) + 1}",
                    'type': 'overnight',
                    'latitude': segment['start_coord'][1],
                    'longitude': segment['start_coord'][0],
                    'estimated_arrival': current_time,
                    'duration': 10
                })
                
                current_time += timedelta(hours=10)
                remaining_drive_time = MAX_DRIVING_TIME
                remaining_on_duty_time = MAX_ON_DUTY_TIME
                time_since_break = 0
                logger.info(f"Added overnight stop: remaining_segment_time={segment_time}")
            
            else:
                current_time += timedelta(hours=segment_time)
                time_since_break += segment_time
                remaining_drive_time -= segment_time
                remaining_on_duty_time -= segment_time
                remaining_cycle_time -= segment_time
                distance_since_fuel += possible_distance
                segment_time = 0
                current_position = segment['end_coord']
                logger.info(f"Completed segment: time_since_break={time_since_break}")
    
    if segments:
        remaining_on_duty_time -= PICKUP_DROPOFF_TIME
        remaining_cycle_time -= PICKUP_DROPOFF_TIME
    
    logger.info(f"Rest stops calculated: {rest_stops}")
    return rest_stops
def generate_eld_logs_service(trip, route, waypoints, current_cycle_hours, user):
    """
    Generate ELD logs for the trip
    
    Args:
        trip: Trip model instance
        route: Route model instance
        waypoints: QuerySet of Waypoint instances
        current_cycle_hours: Current cycle hours used
        user: The authenticated user (for validation)
        
    Returns:
        dict: ELD log data including log entries and daily logs
        
    Raises:
        ValueError: If the trip does not belong to the user
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
    
    # Add all rest stops, fuel stops, and overnight stops
    for waypoint in waypoints.filter(waypoint_type__in=['rest', 'fuel', 'overnight']).order_by('estimated_arrival'):
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

    # Insert fuel stops based on distance
    total_distance = 0
    last_fuel_stop_time = trip_start_time
    i = 0
    while i < len(events) - 1:
        start_event = events[i]
        end_event = events[i + 1]
        driving_duration = (end_event['time'] - (start_event['time'] + timedelta(hours=start_event['duration']))).total_seconds() / 3600
        if driving_duration > 0:
            distance = driving_duration * AVERAGE_SPEED
            total_distance += distance
            if total_distance >= MAX_DISTANCE_BEFORE_FUEL:
                # Calculate the time to drive MAX_DISTANCE_BEFORE_FUEL miles since the last fuel stop
                remaining_distance = MAX_DISTANCE_BEFORE_FUEL - (total_distance - distance)
                time_to_fuel = remaining_distance / AVERAGE_SPEED
                fuel_stop_time = start_event['time'] + timedelta(hours=start_event['duration']) + timedelta(hours=time_to_fuel)
                if fuel_stop_time < end_event['time']:
                    events.insert(i + 1, {
                        'type': 'fuel',
                        'time': fuel_stop_time,
                        'duration': FUEL_STOP_DURATION,
                        'location': start_event['location']
                    })
                    total_distance = 0
                    last_fuel_stop_time = fuel_stop_time
                    i += 1  # Increment i to account for the newly inserted event
                    logger.info(f"Inserted fuel stop at {fuel_stop_time}")
        i += 1
    
    # Re-sort events after adding fuel stops
    events.sort(key=lambda x: x['time'])
    
    # Initialize status tracking
    current_status = 'off_duty'
    status_start_time = trip_start_time
    cycle_driving_hours = 0  # Track driving hours in the current duty cycle
    cycle_on_duty_hours = 0  # Track total on-duty hours (driving + on_duty_not_driving)
    driving_since_last_break = 0  # Track driving hours since the last 30-minute break
    total_cycle_hours = current_cycle_hours  # Track 8-day cycle hours
    last_reset_time = trip_start_time  # Track the last time a 10-hour reset occurred
    current_odometer = 0  # Track odometer for fuel stop calculations
    
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
                    
                    # Enforce 11-hour driving limit
                    if cycle_driving_hours + segment_duration > MAX_DRIVING_TIME:
                        segment_duration = MAX_DRIVING_TIME - cycle_driving_hours
                        end_segment = current_time + timedelta(hours=segment_duration)
                        # Insert a mandatory 10-hour reset break
                        break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                        events.insert(i + 1, {
                            'type': 'reset_break',
                            'time': end_segment,
                            'duration': MANDATORY_RESET_BREAK,
                            'location': event['location']
                        })
                        events.sort(key=lambda x: x['time'])
                        cycle_driving_hours = 0
                        cycle_on_duty_hours = 0
                        driving_since_last_break = 0
                        last_reset_time = break_end
                        logger.info(f"Inserted mandatory 10-hour reset break at {end_segment}")
                        break  # Exit the loop to reprocess with the new event
                    
                    # Enforce 14-hour on-duty limit
                    if cycle_on_duty_hours + segment_duration > MAX_ON_DUTY_TIME:
                        segment_duration = MAX_ON_DUTY_TIME - cycle_on_duty_hours
                        end_segment = current_time + timedelta(hours=segment_duration)
                        # Insert a mandatory 10-hour reset break
                        break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                        events.insert(i + 1, {
                            'type': 'reset_break',
                            'time': end_segment,
                            'duration': MANDATORY_RESET_BREAK,
                            'location': event['location']
                        })
                        events.sort(key=lambda x: x['time'])
                        cycle_driving_hours = 0
                        cycle_on_duty_hours = 0
                        driving_since_last_break = 0
                        last_reset_time = break_end
                        logger.info(f"Inserted mandatory 10-hour reset break due to 14-hour limit at {end_segment}")
                        break
                    
                    # Enforce 8-hour driving limit before a 30-minute break
                    if driving_since_last_break + segment_duration > MAX_DRIVING_BEFORE_BREAK:
                        segment_duration = MAX_DRIVING_BEFORE_BREAK - driving_since_last_break
                        end_segment = current_time + timedelta(hours=segment_duration)
                        # Insert a mandatory 30-minute break
                        break_end = end_segment + timedelta(hours=MANDATORY_BREAK_TIME)
                        events.insert(i + 1, {
                            'type': 'mandatory_break',
                            'time': end_segment,
                            'duration': MANDATORY_BREAK_TIME,
                            'location': event['location']
                        })
                        events.sort(key=lambda x: x['time'])
                        driving_since_last_break = 0
                        logger.info(f"Inserted mandatory 30-minute break at {end_segment}")
                        break
                    
                    # Enforce 70-hour cycle limit
                    if total_cycle_hours + segment_duration > MAX_CYCLE_TIME:
                        segment_duration = MAX_CYCLE_TIME - total_cycle_hours
                        end_segment = current_time + timedelta(hours=segment_duration)
                        # Insert a mandatory 10-hour reset break
                        break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                        events.insert(i + 1, {
                            'type': 'reset_break',
                            'time': end_segment,
                            'duration': MANDATORY_RESET_BREAK,
                            'location': event['location']
                        })
                        events.sort(key=lambda x: x['time'])
                        total_cycle_hours = 0
                        cycle_driving_hours = 0
                        cycle_on_duty_hours = 0
                        driving_since_last_break = 0
                        last_reset_time = break_end
                        logger.info(f"Inserted mandatory 10-hour reset break due to 70-hour cycle limit at {end_segment}")
                        break

                    log_entries.append({
                        'start_time': current_time,
                        'end_time': end_segment,
                        'status': 'driving',
                        'location_id': trip.current_location.id if hasattr(trip.current_location, 'id') else None,
                        'notes': f"Driving to pickup location"
                    })
                    daily_logs[current_date]['total_driving_hours'] += segment_duration
                    daily_logs[current_date]['total_on_duty_hours'] += segment_duration  # Driving counts as on-duty
                    cycle_driving_hours += segment_duration
                    cycle_on_duty_hours += segment_duration
                    driving_since_last_break += segment_duration
                    total_cycle_hours += segment_duration
                    current_odometer += (segment_duration * AVERAGE_SPEED)
                    update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                    logger.info(f"Added initial driving on {current_date}: {segment_duration} hours")
                    current_time = end_segment
            current_status = 'driving'
            status_start_time = event['time']
        
        # Process event based on type
        if event['type'] == 'pickup':
            if current_status != 'on_duty_not_driving':
                if current_status and status_start_time:
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
                            
                            # Enforce 11-hour driving limit
                            if current_status == 'driving' and cycle_driving_hours + segment_duration > MAX_DRIVING_TIME:
                                segment_duration = MAX_DRIVING_TIME - cycle_driving_hours
                                end_segment = current_time + timedelta(hours=segment_duration)
                                # Insert a mandatory 10-hour reset break
                                break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                                events.insert(i + 1, {
                                    'type': 'reset_break',
                                    'time': end_segment,
                                    'duration': MANDATORY_RESET_BREAK,
                                    'location': event['location']
                                })
                                events.sort(key=lambda x: x['time'])
                                cycle_driving_hours = 0
                                cycle_on_duty_hours = 0
                                driving_since_last_break = 0
                                last_reset_time = break_end
                                logger.info(f"Inserted mandatory 10-hour reset break at {end_segment}")
                                break
                            
                            # Enforce 14-hour on-duty limit
                            if cycle_on_duty_hours + segment_duration > MAX_ON_DUTY_TIME:
                                segment_duration = MAX_ON_DUTY_TIME - cycle_on_duty_hours
                                end_segment = current_time + timedelta(hours=segment_duration)
                                # Insert a mandatory 10-hour reset break
                                break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                                events.insert(i + 1, {
                                    'type': 'reset_break',
                                    'time': end_segment,
                                    'duration': MANDATORY_RESET_BREAK,
                                    'location': event['location']
                                })
                                events.sort(key=lambda x: x['time'])
                                cycle_driving_hours = 0
                                cycle_on_duty_hours = 0
                                driving_since_last_break = 0
                                last_reset_time = break_end
                                logger.info(f"Inserted mandatory 10-hour reset break due to 14-hour limit at {end_segment}")
                                break
                            
                            # Enforce 8-hour driving limit before a 30-minute break
                            if current_status == 'driving' and driving_since_last_break + segment_duration > MAX_DRIVING_BEFORE_BREAK:
                                segment_duration = MAX_DRIVING_BEFORE_BREAK - driving_since_last_break
                                end_segment = current_time + timedelta(hours=segment_duration)
                                # Insert a mandatory 30-minute break
                                break_end = end_segment + timedelta(hours=MANDATORY_BREAK_TIME)
                                events.insert(i + 1, {
                                    'type': 'mandatory_break',
                                    'time': end_segment,
                                    'duration': MANDATORY_BREAK_TIME,
                                    'location': event['location']
                                })
                                events.sort(key=lambda x: x['time'])
                                driving_since_last_break = 0
                                logger.info(f"Inserted mandatory 30-minute break at {end_segment}")
                                break
                            
                            # Enforce 70-hour cycle limit
                            if total_cycle_hours + segment_duration > MAX_CYCLE_TIME:
                                segment_duration = MAX_CYCLE_TIME - total_cycle_hours
                                end_segment = current_time + timedelta(hours=segment_duration)
                                # Insert a mandatory 10-hour reset break
                                break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                                events.insert(i + 1, {
                                    'type': 'reset_break',
                                    'time': end_segment,
                                    'duration': MANDATORY_RESET_BREAK,
                                    'location': event['location']
                                })
                                events.sort(key=lambda x: x['time'])
                                total_cycle_hours = 0
                                cycle_driving_hours = 0
                                cycle_on_duty_hours = 0
                                driving_since_last_break = 0
                                last_reset_time = break_end
                                logger.info(f"Inserted mandatory 10-hour reset break due to 70-hour cycle limit at {end_segment}")
                                break
                            
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
                                cycle_driving_hours += segment_duration
                                cycle_on_duty_hours += segment_duration
                                driving_since_last_break += segment_duration
                                total_cycle_hours += segment_duration
                                current_odometer += (segment_duration * AVERAGE_SPEED)
                                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                                logger.info(f"Added driving before pickup on {current_date}: {segment_duration} hours")
                            current_time = end_segment
                current_status = 'on_duty_not_driving'
                status_start_time = event['time']
            
            pickup_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < pickup_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, pickup_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'on_duty_not_driving',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'activity': 'Loading',
                    'notes': f"Loading at pickup location"
                })
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                cycle_on_duty_hours += segment_duration
                total_cycle_hours += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'on_duty_not_driving')
                current_time = end_segment
            
            current_status = 'driving'
            status_start_time = pickup_end_time
        
        elif event['type'] in ['rest', 'fuel', 'mandatory_break']:
            if current_status and status_start_time:
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
                        
                        # Enforce 11-hour driving limit
                        if current_status == 'driving' and cycle_driving_hours + segment_duration > MAX_DRIVING_TIME:
                            segment_duration = MAX_DRIVING_TIME - cycle_driving_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break at {end_segment}")
                            break
                        
                        # Enforce 14-hour on-duty limit
                        if cycle_on_duty_hours + segment_duration > MAX_ON_DUTY_TIME:
                            segment_duration = MAX_ON_DUTY_TIME - cycle_on_duty_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 14-hour limit at {end_segment}")
                            break
                        
                        # Enforce 8-hour driving limit before a 30-minute break
                        if current_status == 'driving' and driving_since_last_break + segment_duration > MAX_DRIVING_BEFORE_BREAK:
                            segment_duration = MAX_DRIVING_BEFORE_BREAK - driving_since_last_break
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 30-minute break
                            break_end = end_segment + timedelta(hours=MANDATORY_BREAK_TIME)
                            events.insert(i + 1, {
                                'type': 'mandatory_break',
                                'time': end_segment,
                                'duration': MANDATORY_BREAK_TIME,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            driving_since_last_break = 0
                            logger.info(f"Inserted mandatory 30-minute break at {end_segment}")
                            break
                        
                        # Enforce 70-hour cycle limit
                        if total_cycle_hours + segment_duration > MAX_CYCLE_TIME:
                            segment_duration = MAX_CYCLE_TIME - total_cycle_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            total_cycle_hours = 0
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 70-hour cycle limit at {end_segment}")
                            break
                        
                        log_entries.append({
                            'start_time': current_time,
                            'end_time': end_segment,
                            'status': current_status,
                            'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                            'notes': f"Driving to {event['type']} stop"
                        })
                        if current_status == 'driving':
                            daily_logs[current_date]['total_driving_hours'] += segment_duration
                            daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                            cycle_driving_hours += segment_duration
                            cycle_on_duty_hours += segment_duration
                            driving_since_last_break += segment_duration
                            total_cycle_hours += segment_duration
                            current_odometer += (segment_duration * AVERAGE_SPEED)
                            update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                            logger.info(f"Added driving before {event['type']} on {current_date}: {segment_duration} hours")
                        current_time = end_segment
            
            rest_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < rest_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, rest_end_time)
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
            
            if event['type'] in ['rest', 'mandatory_break']:
                driving_since_last_break = 0  # Reset the 8-hour driving counter after a break
            
            current_status = 'driving'
            status_start_time = rest_end_time
        
        elif event['type'] == 'overnight':
            if current_status and status_start_time:
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
                        
                        # Enforce 11-hour driving limit
                        if current_status == 'driving' and cycle_driving_hours + segment_duration > MAX_DRIVING_TIME:
                            segment_duration = MAX_DRIVING_TIME - cycle_driving_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break at {end_segment}")
                            break
                        
                        # Enforce 14-hour on-duty limit
                        if cycle_on_duty_hours + segment_duration > MAX_ON_DUTY_TIME:
                            segment_duration = MAX_ON_DUTY_TIME - cycle_on_duty_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 14-hour limit at {end_segment}")
                            break
                        
                        # Enforce 8-hour driving limit before a 30-minute break
                        if current_status == 'driving' and driving_since_last_break + segment_duration > MAX_DRIVING_BEFORE_BREAK:
                            segment_duration = MAX_DRIVING_BEFORE_BREAK - driving_since_last_break
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 30-minute break
                            break_end = end_segment + timedelta(hours=MANDATORY_BREAK_TIME)
                            events.insert(i + 1, {
                                'type': 'mandatory_break',
                                'time': end_segment,
                                'duration': MANDATORY_BREAK_TIME,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            driving_since_last_break = 0
                            logger.info(f"Inserted mandatory 30-minute break at {end_segment}")
                            break
                        
                        # Enforce 70-hour cycle limit
                        if total_cycle_hours + segment_duration > MAX_CYCLE_TIME:
                            segment_duration = MAX_CYCLE_TIME - total_cycle_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            total_cycle_hours = 0
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 70-hour cycle limit at {end_segment}")
                            break
                        
                        log_entries.append({
                            'start_time': current_time,
                            'end_time': end_segment,
                            'status': current_status,
                            'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                            'notes': f"Driving to overnight stop"
                        })
                        if current_status == 'driving':
                            daily_logs[current_date]['total_driving_hours'] += segment_duration
                            daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                            cycle_driving_hours += segment_duration
                            cycle_on_duty_hours += segment_duration
                            driving_since_last_break += segment_duration
                            total_cycle_hours += segment_duration
                            current_odometer += (segment_duration * AVERAGE_SPEED)
                            update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                            logger.info(f"Added driving before overnight on {current_date}: {segment_duration} hours")
                        current_time = end_segment
            
            overnight_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            total_break_duration = 0
            while current_time < overnight_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, overnight_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'sleeper_berth',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'notes': "Overnight stop"
                })
                daily_logs[current_date]['total_sleeper_berth_hours'] += segment_duration
                total_break_duration += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'sleeper_berth')
                current_time = end_segment
            
            # Check if the overnight stop was long enough to reset the cycle
            if total_break_duration >= MANDATORY_RESET_BREAK:
                cycle_driving_hours = 0
                cycle_on_duty_hours = 0
                driving_since_last_break = 0
                total_cycle_hours = 0
                last_reset_time = overnight_end_time
                logger.info(f"Overnight stop at {event['time']} reset the duty cycle")
            
            current_status = 'driving'
            status_start_time = overnight_end_time
        
        elif event['type'] == 'reset_break':
            current_time = event['time']
            break_end_time = event['time'] + timedelta(hours=event['duration'])
            while current_time < break_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, break_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'off_duty',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'notes': "Mandatory HOS reset break"
                })
                daily_logs[current_date]['total_off_duty_hours'] += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'off_duty')
                current_time = end_segment
            
            cycle_driving_hours = 0
            cycle_on_duty_hours = 0
            driving_since_last_break = 0
            total_cycle_hours = 0
            last_reset_time = break_end_time
            current_status = 'driving'
            status_start_time = break_end_time

        elif event['type'] == 'dropoff':
            if current_status and status_start_time:
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
                        
                        # Enforce 11-hour driving limit
                        if current_status == 'driving' and cycle_driving_hours + segment_duration > MAX_DRIVING_TIME:
                            segment_duration = MAX_DRIVING_TIME - cycle_driving_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break at {end_segment}")
                            break
                        
                        # Enforce 14-hour on-duty limit
                        if cycle_on_duty_hours + segment_duration > MAX_ON_DUTY_TIME:
                            segment_duration = MAX_ON_DUTY_TIME - cycle_on_duty_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 14-hour limit at {end_segment}")
                            break
                        
                        # Enforce 8-hour driving limit before a 30-minute break
                        if current_status == 'driving' and driving_since_last_break + segment_duration > MAX_DRIVING_BEFORE_BREAK:
                            segment_duration = MAX_DRIVING_BEFORE_BREAK - driving_since_last_break
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 30-minute break
                            break_end = end_segment + timedelta(hours=MANDATORY_BREAK_TIME)
                            events.insert(i + 1, {
                                'type': 'mandatory_break',
                                'time': end_segment,
                                'duration': MANDATORY_BREAK_TIME,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            driving_since_last_break = 0
                            logger.info(f"Inserted mandatory 30-minute break at {end_segment}")
                            break
                        
                        # Enforce 70-hour cycle limit
                        if total_cycle_hours + segment_duration > MAX_CYCLE_TIME:
                            segment_duration = MAX_CYCLE_TIME - total_cycle_hours
                            end_segment = current_time + timedelta(hours=segment_duration)
                            # Insert a mandatory 10-hour reset break
                            break_end = end_segment + timedelta(hours=MANDATORY_RESET_BREAK)
                            events.insert(i + 1, {
                                'type': 'reset_break',
                                'time': end_segment,
                                'duration': MANDATORY_RESET_BREAK,
                                'location': event['location']
                            })
                            events.sort(key=lambda x: x['time'])
                            total_cycle_hours = 0
                            cycle_driving_hours = 0
                            cycle_on_duty_hours = 0
                            driving_since_last_break = 0
                            last_reset_time = break_end
                            logger.info(f"Inserted mandatory 10-hour reset break due to 70-hour cycle limit at {end_segment}")
                            break
                        
                        log_entries.append({
                            'start_time': current_time,
                            'end_time': end_segment,
                            'status': current_status,
                            'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                            'notes': f"Driving to dropoff"
                        })
                        if current_status == 'driving':
                            daily_logs[current_date]['total_driving_hours'] += segment_duration
                            daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                            cycle_driving_hours += segment_duration
                            cycle_on_duty_hours += segment_duration
                            driving_since_last_break += segment_duration
                            total_cycle_hours += segment_duration
                            current_odometer += (segment_duration * AVERAGE_SPEED)
                            update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'driving')
                            logger.info(f"Added driving before dropoff on {current_date}: {segment_duration} hours")
                        current_time = end_segment
            
            dropoff_end_time = event['time'] + timedelta(hours=event['duration'])
            current_time = event['time']
            while current_time < dropoff_end_time:
                current_date = current_time.date()
                if current_date not in daily_logs:
                    daily_logs[current_date] = initialize_daily_log(current_date, current_date - timedelta(days=1), daily_logs)
                next_day = datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=current_time.tzinfo)
                end_segment = min(next_day, dropoff_end_time)
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                log_entries.append({
                    'start_time': current_time,
                    'end_time': end_segment,
                    'status': 'on_duty_not_driving',
                    'location_id': event['location'].id if hasattr(event['location'], 'id') else None,
                    'activity': 'Unloading',
                    'notes': f"Unloading at delivery location"
                })
                daily_logs[current_date]['total_on_duty_hours'] += segment_duration
                cycle_on_duty_hours += segment_duration
                total_cycle_hours += segment_duration
                update_log_grid(daily_logs[current_date]['log_data'], current_time, end_segment, 'on_duty_not_driving')
                current_time = end_segment
            
            current_status = 'off_duty'
            status_start_time = dropoff_end_time
    
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