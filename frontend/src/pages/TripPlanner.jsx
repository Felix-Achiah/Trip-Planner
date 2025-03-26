import React, { useState } from 'react';

import TripForm from '../components/TripForm.jsx';
import RouteMap from '../components/RouteMap.jsx';
import { calculateRoute } from '../services/api';

const TripPlanner = () => {
  const [tripId, setTripId] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTripCreated = async (newTripId) => {
    setTripId(newTripId);
    await handleCalculateRoute(newTripId);
  };

  const handleCalculateRoute = async (id = tripId) => {
    setLoading(true);
    try {
      const routeResponse = await calculateRoute(id);
      setRouteData(routeResponse.data);
    } catch (error) {
      console.error('Error calculating route:', error);
      alert('Failed to calculate route or generate logs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Trip Planner</h1>
        <TripForm onTripCreated={handleTripCreated} />
      </div>

      {tripId && (
        <div className="space-y-6">
          <button
            onClick={() => handleCalculateRoute()}
            disabled={loading}
            className={`flex items-center justify-center w-full sm:w-auto px-6 py-3 rounded-md text-white font-medium transition duration-200 ${
              loading
                ? 'bg-indigo-400 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 shadow-md hover:shadow-lg'
            }`}
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Recalculate Route & Logs
              </>
            )}
          </button>

          {routeData && (
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600">
                <h2 className="text-xl font-bold text-white">Route Map</h2>
              </div>
              <div className="p-6">
                <RouteMap routeData={routeData} />
              </div>
            </div>
          )}
        </div>
      )}
      
      {!tripId && (
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-blue-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h3 className="text-lg font-medium text-blue-800 mb-2">Ready to Plan Your Trip?</h3>
          <p className="text-blue-600">Fill out the form above to create a new trip and see your route.</p>
        </div>
      )}
    </div>
  );
};

export default TripPlanner;