import React, { useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { Map, Source, Layer, Marker, NavigationControl, FullscreenControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const RouteMap = ({ routeData }) => {
  const [viewport, setViewport] = useState({
    latitude: 37.7577,
    longitude: -122.4376,
    zoom: 4,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [activeWaypoint, setActiveWaypoint] = useState(null);

  // eslint-disable-next-line no-undef
  const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

  useEffect(() => {
    if (routeData && routeData.route_data) {
      setIsLoading(true);
      const coordinates = routeData.route_data.routes[0].geometry.coordinates;
      const bounds = coordinates.reduce(
        (bounds, coord) => {
          return bounds.extend(coord);
        },
        new mapboxgl.LngLatBounds(coordinates[0], coordinates[0])
      );

      setViewport({
        ...viewport,
        latitude: (bounds.getNorth() + bounds.getSouth()) / 2,
        longitude: (bounds.getEast() + bounds.getWest()) / 2,
        zoom: 5,
      });
      setIsLoading(false);
    }
  }, [routeData]);

  const routeLayer = {
    id: 'route',
    type: 'line',
    source: 'route',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#4f46e5', // Indigo color
      'line-width': 6,
      'line-opacity': 0.8,
    },
  };

  const handleMarkerClick = (waypoint) => {
    setActiveWaypoint(waypoint);
    
    // Center map on the waypoint with animation
    setViewport({
      ...viewport,
      latitude: waypoint.location.latitude,
      longitude: waypoint.location.longitude,
      zoom: 11,
      transitionDuration: 1000,
    });
  };

  const getWaypointLabel = (index, total) => {
    if (index === 0) return 'Start';
    if (index === total - 1) return 'End';
    return `Stop ${index}`;
  };

  return (
    <div className="relative rounded-lg overflow-hidden border border-gray-200">
      {isLoading && (
        <div className="absolute inset-0 bg-gray-100 bg-opacity-75 flex items-center justify-center z-10">
          <div className="flex flex-col items-center">
            <svg className="animate-spin h-10 w-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="mt-2 text-sm text-gray-600">Loading route data...</p>
          </div>
        </div>
      )}

      <div className="absolute top-4 left-4 z-10 bg-white bg-opacity-90 rounded-lg shadow-md p-3 max-w-xs">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Route Details</h3>
        {routeData?.route_data?.routes[0]?.distance && (
          <div className="text-xs text-gray-600">
            <div className="flex items-center mb-1">
              <svg className="h-3 w-3 mr-1 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Distance: {(routeData.route_data.routes[0].distance / 1609.34).toFixed(1)} miles
            </div>
            <div className="flex items-center">
              <svg className="h-3 w-3 mr-1 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Duration: {Math.floor(routeData.route_data.routes[0].duration / 3600)} hrs {Math.floor((routeData.route_data.routes[0].duration % 3600) / 60)} min
            </div>
          </div>
        )}
      </div>

      <Map
        {...viewport}
        onMove={(evt) => setViewport(evt.viewState)}
        style={{ width: '100%', height: '600px' }}
        mapStyle="mapbox://styles/mapbox/light-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
        attributionControl={false}
      >
        <FullscreenControl position="top-right" />
        <NavigationControl position="top-right" />

        {routeData && (
          <Source
            id="route"
            type="geojson"
            data={routeData.route_data.routes[0].geometry}
          >
            <Layer {...routeLayer} />
          </Source>
        )}
        
        {routeData?.waypoints?.map((wp, index) => (
          <Marker 
            key={index} 
            longitude={wp.location.longitude} 
            latitude={wp.location.latitude}
            anchor="bottom"
            onClick={() => handleMarkerClick(wp)}
          >
            <div className="cursor-pointer transition-transform duration-200 hover:scale-110 transform-gpu">
              <div className="relative flex flex-col items-center">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center 
                  ${index === 0 ? 'bg-green-500' : 
                    index === routeData.waypoints.length - 1 ? 'bg-red-500' : 'bg-indigo-500'} 
                  text-white text-xs font-bold shadow-md z-10`}>
                  {index + 1}
                </div>
                <div className="w-1 h-6 bg-gray-900 rounded-full absolute -bottom-6 z-0"></div>
                <div className="w-3 h-3 bg-gray-900 rounded-full absolute -bottom-3 z-0 animate-ping opacity-75"></div>
              </div>
            </div>
          </Marker>
        ))}

        {activeWaypoint && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-white rounded-lg shadow-lg p-3 z-10 max-w-sm">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-medium text-gray-800">
                  {getWaypointLabel(routeData.waypoints.indexOf(activeWaypoint), routeData.waypoints.length)}
                </h3>
                <p className="text-sm text-gray-600">{activeWaypoint.name || 'Waypoint'}</p>
                {activeWaypoint.eta && (
                  <p className="text-xs text-gray-500 mt-1">
                    ETA: {new Date(activeWaypoint.eta).toLocaleString()}
                  </p>
                )}
              </div>
              <button 
                onClick={() => setActiveWaypoint(null)}
                className="text-gray-400 hover:text-gray-500"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </Map>

      {routeData?.waypoints && routeData.waypoints.length > 0 && (
        <div className="p-4 bg-white border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Waypoints</h3>
          <div className="flex flex-nowrap overflow-x-auto pb-2 -mx-1">
            {routeData.waypoints.map((wp, index) => (
              <div 
                key={index}
                className={`flex-shrink-0 px-1 cursor-pointer`}
                onClick={() => handleMarkerClick(wp)}
              >
                <div className={`px-3 py-2 rounded-md text-xs font-medium 
                  ${activeWaypoint === wp ? 'bg-indigo-100 text-indigo-700 border border-indigo-300' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                  ${index === 0 ? 'border-l-4 border-l-green-500' : 
                    index === routeData.waypoints.length - 1 ? 'border-l-4 border-l-red-500' : ''}`}
              >
                  {getWaypointLabel(index, routeData.waypoints.length)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RouteMap;