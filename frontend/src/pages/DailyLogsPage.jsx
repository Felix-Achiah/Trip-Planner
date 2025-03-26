/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-unused-vars */
import React, { useState, useEffect, useRef } from 'react';
import { format, subDays, addDays } from 'date-fns';
import { toast } from 'react-toastify';

import { getDailyLogs, getTrips } from '../services/api';
import { getUser } from '../utils/fetchUser';


const DailyLogsPage = () => {
  const [dailyLogs, setDailyLogs] = useState([]);
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState({ start: subDays(new Date(), 7), end: new Date() });
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedLog, setExpandedLog] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const user = getUser();
  const logsPerPage = 5;
  const canvasRefs = useRef([]); // Store canvas refs for each daily log

  useEffect(() => {
    const fetchInitialData = async () => {
      await fetchTrips();
      const urlTripId = new URLSearchParams(window.location.search).get('trip');
      if (urlTripId) {
        setSelectedTripId(urlTripId);
      }
    };
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (selectedTripId) {
      fetchDailyLogs();
    } else {
      setDailyLogs([]);
      setIsLoading(false);
    }
  }, [dateRange, selectedTripId]);

  useEffect(() => {
    if (dailyLogs.length > 0) {
      dailyLogs.forEach((dailyLog, index) => {
        drawGrid(dailyLog, index);
      });
    }
  }, [dailyLogs, expandedLog]);

  const fetchTrips = async () => {
    try {
      const response = await getTrips();
      setTrips(response.data || []);
    } catch (err) {
      console.error('Error fetching trips:', err);
      setError('Failed to load trips. Please try again later.');
      toast.error('Failed to load trips');
    }
  };

  const fetchDailyLogs = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = {
        start_date: format(dateRange.start, 'yyyy-MM-dd'),
        end_date: format(dateRange.end, 'yyyy-MM-dd'),
      };

      if (selectedTripId) {
        params.trip = selectedTripId;
      }

      const response = await getDailyLogs(params);
      setDailyLogs(response.data || []);
    } catch (err) {
      console.error('Error fetching daily logs:', err);
      setError('Failed to load daily logs. Please try again later.');
      toast.error('Failed to load daily logs');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreviousWeek = () => {
    setDateRange({
      start: subDays(dateRange.start, 7),
      end: subDays(dateRange.end, 7),
    });
    setCurrentPage(1);
  };

  const handleNextWeek = () => {
    const newEndDate = addDays(dateRange.end, 7);
    if (newEndDate > new Date()) {
      return;
    }
    setDateRange({
      start: addDays(dateRange.start, 7),
      end: newEndDate,
    });
    setCurrentPage(1);
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const toggleExpand = (logId) => {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  const handleTripChange = (e) => {
    const tripId = e.target.value;
    setSelectedTripId(tripId || null);
    setCurrentPage(1);
    const url = new URL(window.location);
    if (tripId) {
      url.searchParams.set('trip', tripId);
    } else {
      url.searchParams.delete('trip');
    }
    window.history.pushState({}, '', url);
  };

  const filteredLogs = dailyLogs?.filter((log) => {
    if (!searchTerm) return true;
    const searchLower = searchTerm.toLowerCase();
    const dateStr = format(new Date(log.date), 'MMMM dd, yyyy').toLowerCase();
    return (
      dateStr.includes(searchLower) ||
      log.id.toString().includes(searchLower) ||
      (log?.trip_title && log?.trip_title.toLowerCase().includes(searchLower))
    );
  });

  const indexOfLastLog = currentPage * logsPerPage;
  const indexOfFirstLog = indexOfLastLog - logsPerPage;
  const currentLogs = filteredLogs?.slice(indexOfFirstLog, indexOfLastLog);
  const totalPages = Math.ceil(filteredLogs.length / logsPerPage);

  const handlePageChange = (page) => {
    setCurrentPage(page);
    setExpandedLog(null);
  };

  const calculateCycleTotals = (currentLogDate) => {
    // Parse the current log's date
    const currentDate = new Date(currentLogDate);
    
    // Calculate the start of the 8-day window (7 days before the current date)
    const startDate = subDays(currentDate, 7);
  
    // Filter dailyLogs to include only those within the 8-day window
    const logsInCycle = dailyLogs.filter((log) => {
      const logDate = new Date(log.date);
      return logDate >= startDate && logDate <= currentDate;
    });
  
    // Sum the driving and on-duty hours
    const totalDriving = logsInCycle.reduce((sum, log) => {
      return sum + (typeof log.total_driving_hours === 'number' ? log.total_driving_hours : 0);
    }, 0);
  
    const totalOnDutyNotDriving = logsInCycle.reduce((sum, log) => {
      return sum + (typeof log.total_on_duty_hours === 'number' ? log.total_on_duty_hours : 0);
    }, 0);
  
    // Total on-duty time includes both driving and on-duty-not-driving
    const totalOnDuty = totalDriving + totalOnDutyNotDriving;
  
    return {
      driving: totalDriving.toFixed(2),
      onDuty: totalOnDuty.toFixed(2),
    };
  };

  const drawGrid = (dailyLog, index) => {
    const canvas = canvasRefs.current[index];
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width; // 960px (24 hours * 40px/hour)
    const height = canvas.height; // 120px (4 status lines * 30px/line)

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = '#d1d5db'; // Gray-300
    ctx.lineWidth = 1;

    // Vertical lines (every 15 minutes)
    for (let i = 0; i <= 96; i++) {
      const x = i * (width / 96); // 96 intervals (24 hours * 4)
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      if (i % 4 === 0) {
        ctx.strokeStyle = '#9ca3af'; // Gray-400 for hour lines
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = '#d1d5db';
        ctx.lineWidth = 1;
      }
      ctx.stroke();
    }

    // Horizontal lines (status lines)
    for (let i = 0; i <= 4; i++) {
      const y = i * (height / 4);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.strokeStyle = '#d1d5db';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw status changes using log_data
    const statusToY = {
      off_duty: height * 0.125, // Center of line 1
      sleeper_berth: height * 0.375, // Center of line 2
      driving: height * 0.625, // Center of line 3
      on_duty_not_driving: height * 0.875, // Center of line 4
    };

    const statusColors = {
      off_duty: '#3b82f6', // Blue
      sleeper_berth: '#22c55e', // Green
      driving: '#ef4444', // Red
      on_duty_not_driving: '#f59e0b', // Yellow
    };

    let lastX = 0;
    let lastStatus = 'off_duty'; // Default starting status
    let lastY = statusToY[lastStatus];

    ctx.lineWidth = 2;

    dailyLog?.log_data?.forEach((entry, idx) => {
      const x = (entry.time / 2400) * width; // Convert HHMM to fraction of 24 hours
      const status = entry.status || 'off_duty';
      const y = statusToY[status];

      // Draw horizontal line for previous status
      ctx.beginPath();
      ctx.strokeStyle = statusColors[lastStatus];
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(x, lastY);
      ctx.stroke();

      // Draw vertical jump to new status
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
    });+

    // Draw final segment to end of day
    ctx.beginPath();
    ctx.strokeStyle = statusColors[lastStatus];
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(width, lastY);
    ctx.stroke();
  };

  return (
    <div className="min-h-screen pt-16 bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Daily Logs</h1>
          <p className="mt-2 text-sm text-gray-600">
            Select a trip to view its driving and duty status logs
          </p>
        </div>

        {/* Filters and Controls */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center space-x-2">
              <button
                onClick={handlePreviousWeek}
                className="p-2 rounded-md hover:bg-gray-100 transition-colors"
                title="Previous Week"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-gray-600"
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
              <div className="text-sm font-medium text-gray-700">
                {format(dateRange.start, 'MMM d, yyyy')} - {format(dateRange.end, 'MMM d, yyyy')}
              </div>
              <button
                onClick={handleNextWeek}
                className="p-2 rounded-md hover:bg-gray-100 transition-colors"
                title="Next Week"
                disabled={dateRange.end >= new Date()}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className={`h-5 w-5 ${
                    dateRange.end >= new Date() ? 'text-gray-300' : 'text-gray-600'
                  }`}
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
            </div>
            <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
              <select
                value={selectedTripId || ''}
                onChange={handleTripChange}
                className="w-full sm:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select a Trip</option>
                {trips?.map((trip) => (
                  <option key={trip.id} value={trip.id}>
                    {trip?.title}
                  </option>
                ))}
              </select>
              <div className="relative w-full sm:w-64">
                <input
                  type="text"
                  placeholder="Search by date or trip..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={searchTerm}
                  onChange={handleSearch}
                />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 text-gray-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Daily Logs List */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full mb-2"></div>
              <p className="text-gray-500">Loading...</p>
            </div>
          ) : error ? (
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
              <p className="text-red-500 font-medium">{error}</p>
              <button
                className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                onClick={fetchDailyLogs}
              >
                Try Again
              </button>
            </div>
          ) : !selectedTripId ? (
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
              <p className="text-gray-500">Please select a trip to view its logs.</p>
            </div>
          ) : filteredLogs.length === 0 ? (
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
              <p className="text-gray-500">No logs found for this trip and date range.</p>
              {searchTerm && (
                <button
                  className="mt-4 px-4 py-2 text-sm text-indigo-600 border border-indigo-600 rounded-md hover:bg-indigo-50 transition-colors"
                  onClick={() => setSearchTerm('')}
                >
                  Clear Search
                </button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {currentLogs?.map((log, index) => (
                <div
                  key={log.id}
                  className="p-6 hover:bg-gray-50 transition-colors duration-150"
                >
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleExpand(log.id)}
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
                              ref={(el) => (canvasRefs.current[index] = el)}
                              width={960} // 24 hours * 40px/hour
                              height={120} // 4 status lines * 30px/line
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
                            <strong>Driving:</strong> {calculateCycleTotals().driving} hrs
                          </p>
                          <p className="text-sm text-gray-600">
                            <strong>On Duty:</strong> {calculateCycleTotals().onDuty} hrs
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
        </div>

        {/* Pagination */}
        {!isLoading && !error && selectedTripId && filteredLogs.length > 0 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="ml-3 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{indexOfFirstLog + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(indexOfLastLog, filteredLogs.length)}
                </span>{' '}
                of <span className="font-medium">{filteredLogs.length}</span> logs
              </p>
              <nav
                className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
                aria-label="Pagination"
              >
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
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
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => handlePageChange(page)}
                    className={`px-4 py-2 border border-gray-300 text-sm font-medium ${
                      currentPage === page
                        ? 'bg-indigo-50 border-indigo-500 text-indigo-600'
                        : 'bg-white text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                ))}
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
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

export default DailyLogsPage;