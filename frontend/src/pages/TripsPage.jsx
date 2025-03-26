import React, { useState, useEffect, useRef, useCallback } from 'react';
import { format, parseISO } from 'date-fns';
import { toast } from 'react-toastify';
import { getTrips } from '../services/api';

const TripsPage = () => {
  const [trips, setTrips] = useState([]);
  const [filteredTrips, setFilteredTrips] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTrip, setSelectedTrip] = useState(null);
  const [filters, setFilters] = useState({
    searchTerm: '',
    startDate: '',
    endDate: '',
  });
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const limit = 10; // Number of trips per page

  const observer = useRef();

  // Intersection Observer callback to load more trips when the last trip is visible
  const lastTripElementRef = useCallback(
    (node) => {
      if (isLoading) return;
      if (observer.current) observer.current.disconnect();
      observer.current = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasMore) {
          setPage((prevPage) => prevPage + 1);
        }
      });
      if (node) observer.current.observe(node);
    },
    [isLoading, hasMore]
  );

  useEffect(() => {
    fetchTrips();
  }, [page]);

  useEffect(() => {
    applyFilters();
  }, [trips, filters]);

  const fetchTrips = async () => {
    if (!hasMore) return;

    setIsLoading(true);
    setError(null);

    try {
      const params = {
        page,
        limit,
        sort: '-start_time', // Sort by start_time in descending order
      };
      const response = await getTrips(params);
      const newTrips = response.data || [];

      setTrips((prevTrips) => {
        // Avoid duplicates by filtering out trips already in the list
        const existingIds = new Set(prevTrips.map((trip) => trip.id));
        const uniqueNewTrips = newTrips.filter((trip) => !existingIds.has(trip.id));
        return [...prevTrips, ...uniqueNewTrips];
      });

      // Check if there are more trips to load
      setHasMore(newTrips.length === limit);
    } catch (err) {
      console.error('Error fetching trips:', err);
      setError('Failed to load trips. Please try again later.');
      toast.error('Failed to load trips');
    } finally {
      setIsLoading(false);
    }
  };

  const applyFilters = () => {
    let result = trips;

    if (filters.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      result = result.filter(
        (trip) =>
          trip.title.toLowerCase().includes(searchLower) ||
          trip.description?.toLowerCase().includes(searchLower)
      );
    }

    if (filters.startDate) {
      result = result.filter(
        (trip) =>
          trip.start_time &&
          new Date(trip.start_time) >= new Date(filters.startDate)
      );
    }

    if (filters.endDate) {
      result = result.filter(
        (trip) =>
          trip.estimated_end_time &&
          new Date(trip.estimated_end_time) <= new Date(filters.endDate)
      );
    }

    setFilteredTrips(result);
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Reset pagination when filters change
    setPage(1);
    setTrips([]);
    setHasMore(true);
  };

  const handleTripSelect = (trip) => {
    setSelectedTrip(trip);
  };

  const formatDate = (dateString) => {
    try {
      return dateString
        ? format(parseISO(dateString), 'MMM dd, yyyy')
        : 'N/A';
    } catch (error) {
      console.error('Invalid date format:', dateString, error);
      return 'N/A';
    }
  };

  const renderTripDetails = () => {
    if (!selectedTrip) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-8 relative">
          <button
            onClick={() => setSelectedTrip(null)}
            className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>

          <h2 className="text-2xl font-bold text-gray-900 mb-4">{selectedTrip.title}</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Start Date:</strong> {formatDate(selectedTrip.start_time)}
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>End Date:</strong> {formatDate(selectedTrip.estimated_end_time)}
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Total Distance:</strong>{' '}
                {selectedTrip.total_miles || 'N/A'} miles
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Status:</strong>
                <span
                  className={`ml-2 px-2 py-1 rounded-full text-xs ${
                    selectedTrip.status === 'Completed'
                      ? 'bg-green-100 text-green-800'
                      : selectedTrip.status === 'In Progress'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {selectedTrip.status || 'Pending'}
                </span>
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Origin:</strong>{' '}
                {selectedTrip.current_location?.name || 'N/A'}
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Destination:</strong>{' '}
                {selectedTrip.dropoff_location?.name || 'N/A'}
              </p>
            </div>
          </div>

          {selectedTrip.description && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Trip Description
              </h3>
              <p className="text-sm text-gray-600">{selectedTrip.description}</p>
            </div>
          )}

          <div className="mt-6 flex justify-end space-x-3">
            <button
              onClick={() => setSelectedTrip(null)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
            <button
              onClick={() => {
                window.location.href = `/daily-logs?trip=${selectedTrip.id}`;
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
            >
              View Daily Logs
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen pt-16 bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Trips</h1>
          <p className="mt-2 text-sm text-gray-600">View and manage your trips</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-grow">
              <input
                type="text"
                name="searchTerm"
                placeholder="Search trips..."
                value={filters.searchTerm}
                onChange={handleFilterChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <input
                type="date"
                name="startDate"
                value={filters.startDate}
                onChange={handleFilterChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <input
                type="date"
                name="endDate"
                value={filters.endDate}
                onChange={handleFilterChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {filteredTrips.length === 0 && !isLoading ? (
            <div className="p-8 text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-12 w-12 mx-auto text-gray-400 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              <p className="text-gray-500">No trips found</p>
              {(filters.searchTerm || filters.startDate || filters.endDate) && (
                <button
                  onClick={() =>
                    setFilters({ searchTerm: '', startDate: '', endDate: '' })
                  }
                  className="mt-4 px-4 py-2 text-sm text-indigo-600 border border-indigo-600 rounded-md hover:bg-indigo-50"
                >
                  Clear Filters
                </button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredTrips.map((trip, index) => {
                const isLastTrip = filteredTrips.length === index + 1;
                return (
                  <div
                    key={trip.id}
                    ref={isLastTrip ? lastTripElementRef : null}
                    className="p-6 hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
                    onClick={() => handleTripSelect(trip)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-md bg-indigo-100 flex items-center justify-center text-indigo-600">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-6 w-6"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                          </svg>
                        </div>
                        <div className="ml-4">
                          <h3 className="text-lg font-medium text-gray-800">
                            {trip.title}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {formatDate(trip.start_time)} -{' '}
                            {formatDate(trip.estimated_end_time)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center">
                        <span
                          className={`px-2 py-1 rounded-full text-xs ${
                            trip.status === 'Completed'
                              ? 'bg-green-100 text-green-800'
                              : trip.status === 'In Progress'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {trip.status || 'Pending'}
                        </span>
                        <svg
                          className="ml-2 h-5 w-5 text-gray-400"
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                );
              })}
              {isLoading && (
                <div className="p-8 text-center">
                  <div className="inline-block animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mb-2"></div>
                  <p className="text-gray-500">Loading more trips...</p>
                </div>
              )}
              {error && (
                <div className="p-8 text-center">
                  <p className="text-red-500">{error}</p>
                  <button
                    onClick={() => setPage((prevPage) => prevPage + 1)}
                    className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                  >
                    Retry
                  </button>
                </div>
              )}
              {!hasMore && filteredTrips.length > 0 && (
                <div className="p-8 text-center">
                  <p className="text-gray-500">No more trips to load</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedTrip && renderTripDetails()}
    </div>
  );
};

export default TripsPage;