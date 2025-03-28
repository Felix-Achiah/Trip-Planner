/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useRef } from 'react';
import { format, subDays, addDays } from 'date-fns';
import { toast } from 'react-toastify';

import { getDailyLogs, getTrips } from '../services/api';
import { getUser } from '../utils/fetchUser';

// TripsPage Component
const TripsPage = () => {
  const [trips, setTrips] = useState([]);
  const [dailyLogs, setDailyLogs] = useState({}); // Store daily logs for each trip
  const [isLoadingTrips, setIsLoadingTrips] = useState(true);
  const [isLoadingLogs, setIsLoadingLogs] = useState({}); // Track loading state for each trip's logs
  const [errorTrips, setErrorTrips] = useState(null);
  const [errorLogs, setErrorLogs] = useState({}); // Track errors for each trip's logs
  const [expandedTrip, setExpandedTrip] = useState(null); // Track which trip's logs are expanded
  const [expandedLog, setExpandedLog] = useState(null); // Track which daily log is expanded
  const [currentPageTrips, setCurrentPageTrips] = useState(1); // Pagination for trips
  const [currentPageLogs, setCurrentPageLogs] = useState({}); // Pagination for each trip's logs
  const [searchTerm, setSearchTerm] = useState(''); // Search term for filtering trips
  const user = getUser();
  const tripsPerPage = 5; // Number of trips per page
  const logsPerPage = 5; // Number of logs per page
  const canvasRefs = useRef({}); // Store canvas refs for each daily log per trip

  useEffect(() => {
    fetchTrips();
  }, []);

  const fetchTrips = async () => {
    setIsLoadingTrips(true);
    setErrorTrips(null);
    try {
      const response = await getTrips();
      setTrips(response.data || []);
    } catch (err) {
      console.error('Error fetching trips:', err);
      setErrorTrips('Failed to load trips. Please try again later.');
      toast.error('Failed to load trips');
    } finally {
      setIsLoadingTrips(false);
    }
  };

  const fetchDailyLogs = async (tripId) => {
    setIsLoadingLogs((prev) => ({ ...prev, [tripId]: true }));
    setErrorLogs((prev) => ({ ...prev, [tripId]: null }));

    try {
      const params = {
        trip: tripId,
        start_date: format(subDays(new Date(), 7), 'yyyy-MM-dd'),
        end_date: format(new Date(), 'yyyy-MM-dd'),
      };

      const response = await getDailyLogs(params);
      setDailyLogs((prev) => ({
        ...prev,
        [tripId]: response.data || [],
      }));
    } catch (err) {
      console.error(`Error fetching daily logs for trip ${tripId}:`, err);
      setErrorLogs((prev) => ({
        ...prev,
        [tripId]: 'Failed to load daily logs. Please try again later.',
      }));
      toast.error('Failed to load daily logs');
    } finally {
      setIsLoadingLogs((prev) => ({ ...prev, [tripId]: false }));
    }
  };

  useEffect(() => {
    // Draw grids for all expanded trips' logs
    if (expandedTrip && dailyLogs[expandedTrip]) {
      const logs = dailyLogs[expandedTrip];
      logs.forEach((dailyLog, index) => {
        drawGrid(dailyLog, expandedTrip, index);
      });
    }
  }, [dailyLogs, expandedTrip, expandedLog]);

  const toggleTripLogs = (tripId) => {
    if (expandedTrip === tripId) {
      setExpandedTrip(null); // Collapse if already expanded
      setExpandedLog(null);
    } else {
      setExpandedTrip(tripId);
      setExpandedLog(null);
      setCurrentPageLogs((prev) => ({ ...prev, [tripId]: 1 }));
      if (!dailyLogs[tripId]) {
        fetchDailyLogs(tripId); // Fetch logs if not already fetched
      }
    }
  };

  const toggleExpandLog = (logId) => {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  const handlePageChangeTrips = (page) => {
    setCurrentPageTrips(page);
    setExpandedTrip(null);
    setExpandedLog(null);
  };

  const handlePageChangeLogs = (tripId, page) => {
    setCurrentPageLogs((prev) => ({ ...prev, [tripId]: page }));
    setExpandedLog(null);
  };

  const calculateCycleTotals = (tripId, currentLogDate) => {
    const logs = dailyLogs[tripId] || [];
    const currentDate = new Date(currentLogDate);
    const startDate = subDays(currentDate, 7);

    const logsInCycle = logs.filter((log) => {
      const logDate = new Date(log.date);
      return logDate >= startDate && logDate <= currentDate;
    });

    const totalDriving = logsInCycle.reduce((sum, log) => {
      return sum + (typeof log.total_driving_hours === 'number' ? log.total_driving_hours : 0);
    }, 0);

    const totalOnDutyNotDriving = logsInCycle.reduce((sum, log) => {
      return sum + (typeof log.total_on_duty_hours === 'number' ? log.total_on_duty_hours : 0);
    }, 0);

    const totalOnDuty = totalDriving + totalOnDutyNotDriving;

    return {
      driving: totalDriving.toFixed(2),
      onDuty: totalOnDuty.toFixed(2),
    };
  };

  const drawGrid = (dailyLog, tripId, index) => {
    const canvas = canvasRefs.current[`${tripId}-${index}`];
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width; // 960px (24 hours * 40px/hour)
    const height = canvas.height; // 120px (4 status lines * 30px/line)

    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 1;

    for (let i = 0; i <= 96; i++) {
      const x = i * (width / 96);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      if (i % 4 === 0) {
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = '#d1d5db';
        ctx.lineWidth = 1;
      }
      ctx.stroke();
    }

    for (let i = 0; i <= 4; i++) {
      const y = i * (height / 4);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.strokeStyle = '#d1d5db';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    const statusToY = {
      off_duty: height * 0.125,
      sleeper_berth: height * 0.375,
      driving: height * 0.625,
      on_duty_not_driving: height * 0.875,
    };

    const statusColors = {
      off_duty: '#3b82f6',
      sleeper_berth: '#22c55e',
      driving: '#ef4444',
      on_duty_not_driving: '#f59e0b',
    };

    let lastX = 0;
    let lastStatus = 'off_duty';
    let lastY = statusToY[lastStatus];

    ctx.lineWidth = 2;

    dailyLog?.log_data?.forEach((entry, idx) => {
      const x = (entry.time / 1440) * width; // Convert minutes to fraction of 24 hours
      const status = entry.status || 'off_duty';
      const y = statusToY[status];

      ctx.beginPath();
      ctx.strokeStyle = statusColors[lastStatus];
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(x, lastY);
      ctx.stroke();

      if (lastStatus !== status) {
        ctx.beginPath();
        ctx.strokeStyle = statusColors[status];
        ctx.moveTo(x, lastY);
        ctx.lineTo(x, y);
        ctx.stroke();
      }

      lastX = x;
      lastY = y;
      lastStatus = status;
    });

    ctx.beginPath();
    ctx.strokeStyle = statusColors[lastStatus];
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(width, lastY);
    ctx.stroke();
  };

  // Filter trips based on search term
  const filteredTrips = trips.filter((trip) => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    const tripTitle = (trip.title || 'Unnamed Trip').toLowerCase();
    return tripTitle.includes(searchLower);
  });

  // Paginate filtered trips
  const indexOfLastTrip = currentPageTrips * tripsPerPage;
  const indexOfFirstTrip = indexOfLastTrip - tripsPerPage;
  const currentTrips = filteredTrips.slice(indexOfFirstTrip, indexOfLastTrip);
  const totalPagesTrips = Math.ceil(filteredTrips.length / tripsPerPage);

  const getCurrentLogs = (tripId) => {
    const logs = dailyLogs[tripId] || [];
    const page = currentPageLogs[tripId] || 1;
    const indexOfLastLog = page * logsPerPage;
    const indexOfFirstLog = indexOfLastLog - logsPerPage;
    return {
      currentLogs: logs.slice(indexOfFirstLog, indexOfLastLog),
      totalPages: Math.ceil(logs.length / logsPerPage),
      indexOfFirstLog,
      indexOfLastLog,
      totalLogs: logs.length,
    };
  };

  return (
    <div className="min-h-screen pt-16 bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Trips</h1>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <input
              type="text"
              placeholder="Search trips by name..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPageTrips(1); // Reset to first page on search
                setExpandedTrip(null); // Collapse any expanded logs
                setExpandedLog(null);
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
            <svg
              className="absolute right-3 top-2.5 h-5 w-5 text-gray-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Trips List */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {isLoadingTrips ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mb-2"></div>
              <p className="text-gray-500">Loading trips...</p>
            </div>
          ) : errorTrips ? (
            <div className="p-8 text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-12 w-12 mx-auto text-red-500 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p className="text-red-500 font-medium">{errorTrips}</p>
              <button
                className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                onClick={fetchTrips}
              >
                Try Again
              </button>
            </div>
          ) : filteredTrips.length === 0 ? (
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-gray-500">
                {searchTerm ? 'No trips match your search' : 'No trips found'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {currentTrips.map((trip) => (
                <div
                  key={trip.id}
                  className="p-6 hover:bg-gray-50 transition-colors duration-150"
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
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                      </div>
                      <div className="ml-4">
                        <h3 className="text-lg font-medium text-gray-800">
                          {trip.title || 'Unnamed Trip'}
                        </h3>
                        <p className="text-sm text-gray-500">
                          Start: {format(new Date(trip.start_time), 'MMMM dd, yyyy HH:mm')}
                        </p>
                        <p className="text-sm text-gray-500">
                          End: {trip.end_time ? format(new Date(trip.end_time), 'MMMM dd, yyyy HH:mm') : 'Ongoing'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => toggleTripLogs(trip.id)}
                        className="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors flex items-center"
                      >
                        <svg
                          className="h-4 w-4 mr-1"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                        {expandedTrip === trip.id ? 'Hide Logs' : 'View Logs'}
                      </button>
                    </div>
                  </div>

                  {/* Daily Logs Section */}
                  {expandedTrip === trip.id && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      {isLoadingLogs[trip.id] ? (
                        <div className="p-8 text-center">
                          <div className="inline-block animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mb-2"></div>
                          <p className="text-gray-500">Loading logs...</p>
                        </div>
                      ) : errorLogs[trip.id] ? (
                        <div className="p-8 text-center">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-12 w-12 mx-auto text-red-500 mb-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                            />
                          </svg>
                          <p className="text-red-500 font-medium">{errorLogs[trip.id]}</p>
                          <button
                            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                            onClick={() => fetchDailyLogs(trip.id)}
                          >
                            Try Again
                          </button>
                        </div>
                      ) : !dailyLogs[trip.id] || dailyLogs[trip.id].length === 0 ? (
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
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <p className="text-gray-500">No logs found for this trip</p>
                        </div>
                      ) : (
                        <div className="divide-y divide-gray-200">
                          {getCurrentLogs(trip.id).currentLogs.map((log, index) => (
                            <div
                              key={log.id}
                              className="p-6 hover:bg-gray-50 transition-colors duration-150"
                            >
                              <div
                                className="flex items-center justify-between cursor-pointer"
                                onClick={() => toggleExpandLog(log.id)}
                              >
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
                                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                                      />
                                    </svg>
                                  </div>
                                  <div className="ml-4">
                                    <h3 className="text-lg font-medium text-gray-800">
                                      {format(new Date(log.date), 'EEEE, MMMM dd, yyyy')}
                                    </h3>
                                    <p className="text-sm text-gray-500">
                                      Trip: {log?.trip_title || 'Unnamed Trip'}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex items-center">
                                  <div className="flex space-x-2 mr-4">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                      {log.total_driving_hours.toFixed(1)}h Driving
                                    </span>
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                      {log.total_off_duty_hours.toFixed(1)}h Off
                                    </span>
                                  </div>
                                  <svg
                                    className={`h-5 w-5 text-gray-500 transform transition-transform duration-200 ${
                                      expandedLog === log.id ? 'rotate-180' : ''
                                    }`}
                                    viewBox="0 0 20 20"
                                    fill="currentColor"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                </div>
                              </div>

                              {expandedLog === log.id && (
                                <div className="mt-4 pt-4 border-t border-gray-100">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                    <div>
                                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                                        Duty Status Summary
                                      </h4>
                                      <div className="space-y-2">
                                        <div className="flex items-center">
                                          <div className="h-3 w-3 rounded-full bg-green-500 mr-2"></div>
                                          <span className="text-sm text-gray-600">
                                            Driving: {log.total_driving_hours.toFixed(2)} hours
                                          </span>
                                        </div>
                                        <div className="flex items-center">
                                          <div className="h-3 w-3 rounded-full bg-yellow-500 mr-2"></div>
                                          <span className="text-sm text-gray-600">
                                            On Duty: {log.total_on_duty_hours.toFixed(2)} hours
                                          </span>
                                        </div>
                                        <div className="flex items-center">
                                          <div className="h-3 w-3 rounded-full bg-blue-500 mr-2"></div>
                                          <span className="text-sm text-gray-600">
                                            Off Duty: {log.total_off_duty_hours.toFixed(2)} hours
                                          </span>
                                        </div>
                                        <div className="flex items-center">
                                          <div className="h-3 w-3 rounded-full bg-purple-500 mr-2"></div>
                                          <span className="text-sm text-gray-600">
                                            Sleeper Berth: {log.total_sleeper_berth_hours.toFixed(2)} hours
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                    <div>
                                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                                        Odometer Readings
                                      </h4>
                                      <div className="space-y-2">
                                        <div className="text-sm text-gray-600">
                                          Start:{' '}
                                          {log.starting_odometer !== null
                                            ? `${log.starting_odometer} miles`
                                            : 'N/A'}
                                        </div>
                                        <div className="text-sm text-gray-600">
                                          End:{' '}
                                          {log.ending_odometer !== null
                                            ? `${log.ending_odometer} miles`
                                            : 'N/A'}
                                        </div>
                                        <div className="text-sm text-gray-600">
                                          Total:{' '}
                                          {log.starting_odometer !== null &&
                                          log.ending_odometer !== null
                                            ? `${log.ending_odometer - log.starting_odometer} miles`
                                            : 'N/A'}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="mt-6">
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                                      Daily Log Sheet
                                    </h4>
                                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                                      {Array.from({ length: 25 }).map((_, hour) => (
                                        <span key={hour} className={hour % 2 === 0 ? 'font-bold' : ''}>
                                          {hour}
                                        </span>
                                      ))}
                                    </div>
                                    <div className="relative">
                                      <div className="absolute top-0 left-0 h-full flex flex-col justify-between text-xs text-gray-500">
                                        <span>1. Off Duty</span>
                                        <span>2. Sleeper Berth</span>
                                        <span>3. Driving</span>
                                        <span>4. On Duty Not Driving</span>
                                      </div>
                                      <div className="ml-24">
                                        <canvas
                                          ref={(el) => (canvasRefs.current[`${trip.id}-${index}`] = el)}
                                          width={960}
                                          height={120}
                                          className="border border-gray-300"
                                        />
                                      </div>
                                    </div>
                                  </div>
                                  <div className="mt-4">
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                                      70-Hour/8-Day Cycle
                                    </h4>
                                    <div className="grid grid-cols-2 gap-4">
                                      <p className="text-sm text-gray-600">
                                        <strong>Driving:</strong> {calculateCycleTotals(trip.id, log.date).driving} hrs
                                      </p>
                                      <p className="text-sm text-gray-600">
                                        <strong>On Duty:</strong> {calculateCycleTotals(trip.id, log.date).onDuty} hrs
                                      </p>
                                    </div>
                                  </div>
                                  <div className="mt-4 flex justify-end space-x-2">
                                    <button
                                      className="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        window.print();
                                      }}
                                    >
                                      <div className="flex items-center">
                                        <svg
                                          xmlns="http://www.w3.org/2000/svg"
                                          className="h-4 w-4 mr-1"
                                          fill="none"
                                          viewBox="0 0 24 24"
                                          stroke="currentColor"
                                        >
                                          <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                                          />
                                        </svg>
                                        Print Log
                                      </div>
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Pagination for Logs */}
                      {dailyLogs[trip.id] && dailyLogs[trip.id].length > 0 && (
                        <div className="mt-6 flex items-center justify-between">
                          <div className="flex-1 flex justify-between sm:hidden">
                            <button
                              onClick={() => handlePageChangeLogs(trip.id, (currentPageLogs[trip.id] || 1) - 1)}
                              disabled={(currentPageLogs[trip.id] || 1) === 1}
                              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Previous
                            </button>
                            <button
                              onClick={() => handlePageChangeLogs(trip.id, (currentPageLogs[trip.id] || 1) + 1)}
                              disabled={(currentPageLogs[trip.id] || 1) === getCurrentLogs(trip.id).totalPages}
                              className="ml-3 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Next
                            </button>
                          </div>
                          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                            <p className="text-sm text-gray-700">
                              Showing <span className="font-medium">{getCurrentLogs(trip.id).indexOfFirstLog + 1}</span> to{' '}
                              <span className="font-medium">
                                {Math.min(getCurrentLogs(trip.id).indexOfLastLog, getCurrentLogs(trip.id).totalLogs)}
                              </span>{' '}
                              of <span className="font-medium">{getCurrentLogs(trip.id).totalLogs}</span> logs
                            </p>
                            <nav
                              className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
                              aria-label="Pagination"
                            >
                              <button
                                onClick={() => handlePageChangeLogs(trip.id, (currentPageLogs[trip.id] || 1) - 1)}
                                disabled={(currentPageLogs[trip.id] || 1) === 1}
                                className="px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <svg
                                  className="h-5 w-5"
                                  xmlns="http://www.w3.org/2000/svg"
                                  viewBox="0 0 20 20"
                                  fill="currentColor"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              </button>
                              {Array.from({ length: getCurrentLogs(trip.id).totalPages }, (_, i) => i + 1).map((page) => (
                                <button
                                  key={page}
                                  onClick={() => handlePageChangeLogs(trip.id, page)}
                                  className={`px-4 py-2 border border-gray-300 text-sm font-medium ${
                                    (currentPageLogs[trip.id] || 1) === page
                                      ? 'bg-indigo-50 border-indigo-500 text-indigo-600'
                                      : 'bg-white text-gray-500 hover:bg-gray-50'
                                  }`}
                                >
                                  {page}
                                </button>
                              ))}
                              <button
                                onClick={() => handlePageChangeLogs(trip.id, (currentPageLogs[trip.id] || 1) + 1)}
                                disabled={(currentPageLogs[trip.id] || 1) === getCurrentLogs(trip.id).totalPages}
                                className="px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <svg
                                  className="h-5 w-5"
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
                              </button>
                            </nav>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination for Trips */}
        {!isLoadingTrips && !errorTrips && filteredTrips.length > 0 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChangeTrips(currentPageTrips - 1)}
                disabled={currentPageTrips === 1}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChangeTrips(currentPageTrips + 1)}
                disabled={currentPageTrips === totalPagesTrips}
                className="ml-3 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{indexOfFirstTrip + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(indexOfLastTrip, filteredTrips.length)}
                </span>{' '}
                of <span className="font-medium">{filteredTrips.length}</span> trips
              </p>
              <nav
                className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
                aria-label="Pagination"
              >
                <button
                  onClick={() => handlePageChangeTrips(currentPageTrips - 1)}
                  disabled={currentPageTrips === 1}
                  className="px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg
                    className="h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                {Array.from({ length: totalPagesTrips }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => handlePageChangeTrips(page)}
                    className={`px-4 py-2 border border-gray-300 text-sm font-medium ${
                      currentPageTrips === page
                        ? 'bg-indigo-50 border-indigo-500 text-indigo-600'
                        : 'bg-white text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                ))}
                <button
                  onClick={() => handlePageChangeTrips(currentPageTrips + 1)}
                  disabled={currentPageTrips === totalPagesTrips}
                  className="px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg
                    className="h-5 w-5"
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
                </button>
              </nav>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TripsPage;