import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta, time
import math
import logging

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

    log_entries = []
    daily_logs = []
    
    # Start with trip start time
    current_time = trip.start_time
    
    # Convert waypoints to chronological list of events
    events = []
    
    # Add pickup event
    pickup_waypoint = waypoints.filter(waypoint_type='pickup').first()
    if pickup_waypoint:
        events.append({
            'type': 'pickup',
            'time': pickup_waypoint.estimated_arrival,
            'duration': pickup_waypoint.planned_duration,
            'location': pickup_waypoint.location
        })
    
    # Add all rest stops and fuel stops
    for waypoint in waypoints.filter(waypoint_type__in=['rest', 'fuel', 'overnight']).order_by('estimated_arrival'):
        events.append({
            'type': waypoint.waypoint_type,
            'time': waypoint.estimated_arrival,
            'duration': waypoint.planned_duration,
            'location': waypoint.location
        })
    
    # Add dropoff event
    dropoff_waypoint = waypoints.filter(waypoint_type='dropoff').first()
    if dropoff_waypoint:
        events.append({
            'type': 'dropoff',
            'time': dropoff_waypoint.estimated_arrival,
            'duration': dropoff_waypoint.planned_duration,
            'location': dropoff_waypoint.location
        })
    
    # Sort events by time
    events.sort(key=lambda x: x['time'])
    
    # Initialize current state
    current_date = trip.start_time.date()
    current_status = None
    status_start_time = None
    
    # Create a daily log for the first day
    daily_log = {
        'date': current_date,
        'starting_odometer': 0,  # Would be calculated in production
        'ending_odometer': 0,
        'total_driving_hours': 0,
        'total_on_duty_hours': 0,
        'total_off_duty_hours': 0,
        'total_sleeper_berth_hours': 0,
        'log_data': initialize_log_grid()
    }
    
    # Process each event chronologically
    for i, event in enumerate(events):
        # If this is the first event, add driving time from trip start to first event
        if i == 0 and event['type'] == 'pickup':
            # Driver is driving from current location to pickup
            driving_duration = (event['time'] - trip.start_time).total_seconds() / 3600
            
            # Add driving log entry
            log_entries.append({
                'start_time': trip.start_time,
                'end_time': event['time'],
                'status': 'driving',
                'location_id': trip.current_location.id,
                'notes': f"Driving to pickup location"
            })
            
            # Update daily log
            daily_log['total_driving_hours'] += driving_duration
            update_log_grid(daily_log['log_data'], trip.start_time, event['time'], 'driving')
            
            current_status = 'driving'
            status_start_time = trip.start_time
        
        # Process event based on type
        if event['type'] == 'pickup':
            # Change status to on_duty_not_driving for pickup
            if current_status != 'on_duty_not_driving':
                # End previous status
                if current_status and status_start_time:
                    log_entries.append({
                        'start_time': status_start_time,
                        'end_time': event['time'],
                        'status': current_status,
                        'location_id': event['location'].id,
                        'notes': f"En route to {event['type']}"
                    })
                
                # Update daily log
                if current_status == 'driving':
                    duration = (event['time'] - status_start_time).total_seconds() / 3600
                    daily_log['total_driving_hours'] += duration
                    update_log_grid(daily_log['log_data'], status_start_time, event['time'], 'driving')
                
                # Start new status
                current_status = 'on_duty_not_driving'
                status_start_time = event['time']
            
            # Add on-duty log entry for pickup
            pickup_end_time = event['time'] + timedelta(hours=event['duration'])
            log_entries.append({
                'start_time': event['time'],
                'end_time': pickup_end_time,
                'status': 'on_duty_not_driving',
                'location_id': event['location'].id,
                'activity': 'Loading',
                'notes': f"Loading at pickup location"
            })
            
            # Update daily log
            daily_log['total_on_duty_hours'] += event['duration']
            update_log_grid(daily_log['log_data'], event['time'], pickup_end_time, 'on_duty_not_driving')
            
            # After pickup, driver starts driving
            current_status = 'driving'
            status_start_time = pickup_end_time
            
        elif event['type'] == 'rest':
            # End previous status
            if current_status and status_start_time:
                log_entries.append({
                    'start_time': status_start_time,
                    'end_time': event['time'],
                    'status': current_status,
                    'location_id': event['location'].id
                })
                
                # Update daily log
                if current_status == 'driving':
                    duration = (event['time'] - status_start_time).total_seconds() / 3600
                    daily_log['total_driving_hours'] += duration
                    update_log_grid(daily_log['log_data'], status_start_time, event['time'], 'driving')
            
            # Add off-duty log entry for rest
            rest_end_time = event['time'] + timedelta(hours=event['duration'])
            log_entries.append({
                'start_time': event['time'],
                'end_time': rest_end_time,
                'status': 'off_duty',
                'location_id': event['location'].id,
                'notes': f"Mandatory rest break"
            })
            
            # Update daily log
            daily_log['total_off_duty_hours'] += event['duration']
            update_log_grid(daily_log['log_data'], event['time'], rest_end_time, 'off_duty')
            
            # After rest, driver starts driving again
            current_status = 'driving'
            status_start_time = rest_end_time
            
        elif event['type'] == 'fuel':
            # End previous status
            if current_status and status_start_time:
                log_entries.append({
                    'start_time': status_start_time,
                    'end_time': event['time'],
                    'status': current_status,
                    'location_id': event['location'].id
                })
                
                # Update daily log
                if current_status == 'driving':
                    duration = (event['time'] - status_start_time).total_seconds() / 3600
                    daily_log['total_driving_hours'] += duration
                    update_log_grid(daily_log['log_data'], status_start_time, event['time'], 'driving')
            
            # Add on-duty log entry for fueling
            fuel_end_time = event['time'] + timedelta(hours=event['duration'])
            log_entries.append({
                'start_time': event['time'],
                'end_time': fuel_end_time,
                'status': 'on_duty_not_driving',
                'location_id': event['location'].id,
                'activity': 'Fueling',
                'notes': f"Fuel stop"
            })
            
            # Update daily log
            daily_log['total_on_duty_hours'] += event['duration']
            update_log_grid(daily_log['log_data'], event['time'], fuel_end_time, 'on_duty_not_driving')
            
            # After fueling, driver starts driving again
            current_status = 'driving'
            status_start_time = fuel_end_time
            
        elif event['type'] == 'overnight':
            # End previous status
            if current_status and status_start_time:
                log_entries.append({
                    'start_time': status_start_time,
                    'end_time': event['time'],
                    'status': current_status,
                    'location_id': event['location'].id
                })
                
                # Update daily log
                if current_status == 'driving':
                    duration = (event['time'] - status_start_time).total_seconds() / 3600
                    daily_log['total_driving_hours'] += duration
                    update_log_grid(daily_log['log_data'], status_start_time, event['time'], 'driving')
            
            # Add sleeper berth log entry for overnight rest
            overnight_end_time = event['time'] + timedelta(hours=event['duration'])
            log_entries.append({
                'start_time': event['time'],
                'end_time': overnight_end_time,
                'status': 'sleeper_berth',
                'location_id': event['location'].id,
                'notes': f"10-hour reset"
            })
            
            # Check if rest period spans multiple days
            if event['time'].date() != overnight_end_time.date():
                # Finalize current day's log
                daily_log['ending_odometer'] = calculate_odometer(0, daily_log['total_driving_hours'])
                daily_logs.append(daily_log)
                
                # Create new daily log for the next day
                current_date = overnight_end_time.date()
                daily_log = {
                    'date': current_date,
                    'starting_odometer': daily_log['ending_odometer'],
                    'ending_odometer': 0,
                    'total_driving_hours': 0,
                    'total_on_duty_hours': 0,
                    'total_off_duty_hours': 0,
                    'total_sleeper_berth_hours': 0,
                    'log_data': initialize_log_grid()
                }
            
            # Calculate how much sleeper berth time falls on each day
            current_time = event['time']
            while current_time < overnight_end_time:
                next_day = datetime.combine(current_time.date() + timedelta(days=1), time.min)
                end_segment = min(next_day, overnight_end_time)
                
                segment_duration = (end_segment - current_time).total_seconds() / 3600
                daily_log['total_sleeper_berth_hours'] += segment_duration
                update_log_grid(daily_log['log_data'], current_time, end_segment, 'sleeper_berth')
                
                if end_segment < overnight_end_time:
                    # Finalize this day's log
                    daily_log['ending_odometer'] = calculate_odometer(daily_log['starting_odometer'], daily_log['total_driving_hours'])
                    daily_logs.append(daily_log)
                    
                    # Create new log for next day
                    current_date = end_segment.date()
                    daily_log = {
                        'date': current_date,
                        'starting_odometer': daily_log['ending_odometer'],
                        'ending_odometer': 0,
                        'total_driving_hours': 0,
                        'total_on_duty_hours': 0,
                        'total_off_duty_hours': 0,
                        'total_sleeper_berth_hours': 0,
                        'log_data': initialize_log_grid()
                    }
                
                current_time = end_segment
            
            # After overnight rest, driver starts driving again
            current_status = 'driving'
            status_start_time = overnight_end_time
            
        elif event['type'] == 'dropoff':
            # End previous status
            if current_status and status_start_time:
                log_entries.append({
                    'start_time': status_start_time,
                    'end_time': event['time'],
                    'status': current_status,
                    'location_id': event['location'].id
                })
                
                # Update daily log
                if current_status == 'driving':
                    duration = (event['time'] - status_start_time).total_seconds() / 3600
                    daily_log['total_driving_hours'] += duration
                    update_log_grid(daily_log['log_data'], status_start_time, event['time'], 'driving')
            
            # Add on-duty log entry for dropoff
            dropoff_end_time = event['time'] + timedelta(hours=event['duration'])
            log_entries.append({
                'start_time': event['time'],
                'end_time': dropoff_end_time,
                'status': 'on_duty_not_driving',
                'location_id': event['location'].id,
                'activity': 'Unloading',
                'notes': f"Unloading at delivery location"
            })
            
            # Update daily log
            daily_log['total_on_duty_hours'] += event['duration']
            update_log_grid(daily_log['log_data'], event['time'], dropoff_end_time, 'on_duty_not_driving')
            
            # After dropoff, trip is complete
            current_status = 'off_duty'
            status_start_time = dropoff_end_time
    
    # Finalize the last daily log
    daily_log['ending_odometer'] = calculate_odometer(daily_log['starting_odometer'], daily_log['total_driving_hours'])
    daily_logs.append(daily_log)
    
    logger.info(f"Generated {len(log_entries)} log entries and {len(daily_logs)} daily logs for trip {trip.id}")
    
    return {
        'log_entries': log_entries,
        'daily_logs': daily_logs
    }

def initialize_log_grid():
    """Initialize a 24-hour log grid with 15-minute intervals"""
    grid = []
    for hour in range(24):
        for minute in range(0, 60, 15):
            timestamp = hour * 100 + minute if minute > 0 else hour * 100
            grid.append({
                'time': timestamp,
                'status': None
            })
    return grid

def update_log_grid(grid, start_time, end_time, status):
    """Update log grid with status for the given time period"""
    # Convert datetime to grid time format (HHMM)
    start_grid_time = start_time.hour * 100 + (start_time.minute // 15) * 15
    end_grid_time = end_time.hour * 100 + (end_time.minute // 15) * 15
    
    # Handle overnight periods
    if start_time.date() != end_time.date():
        # Update until end of day
        for cell in grid:
            if cell['time'] >= start_grid_time and cell['time'] <= 2345:
                cell['status'] = status
        return
    
    # Update grid cells within the time range
    for cell in grid:
        if cell['time'] >= start_grid_time and cell['time'] <= end_grid_time:
            cell['status'] = status

def calculate_odometer(starting_odometer, driving_hours):
    """Calculate ending odometer based on driving hours (assuming avg speed of 55 mph)"""
    avg_speed = 55  # mph
    distance_driven = driving_hours * avg_speed
    return starting_odometer + round(distance_driven)