import React, { useState } from 'react';
import { format } from 'date-fns';

const DailyLogViewer = ({ dailyLogs }) => {
  const [expandedLog, setExpandedLog] = useState(null);

  const toggleExpand = (logId) => {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  // Helper to determine status colors
  const getStatusColor = (status) => {
    if (!status) return 'bg-gray-200';
    
    switch(status.toLowerCase()) {
      case 'driving':
        return 'bg-green-500';
      case 'on_duty':
        return 'bg-yellow-500';
      case 'off_duty':
        return 'bg-blue-400';
      case 'sleeper_berth':
        return 'bg-purple-400';
      default:
        return 'bg-gray-200';
    }
  };

  const renderLogGrid = (logData) => {
    if (!logData || !logData.length) return null;

    return (
      <div className="grid grid-cols-24 gap-0.5 mt-4">
        {Array.from({ length: 24 }).map((_, hour) => (
          <div key={`hour-${hour}`} className="text-xs text-center text-gray-500 -mb-1">
            {hour}
          </div>
        ))}
        
        {logData.map((cell, index) => {
          // eslint-disable-next-line no-unused-vars
          const hour = Math.floor(index / 4);
          return (
            <div
              key={index}
              className={`h-6 ${getStatusColor(cell.status)} rounded-sm`}
              title={`${cell.time}: ${cell.status || 'No status'}`}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600">
        <h2 className="text-xl font-bold text-white flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Daily Logs
        </h2>
      </div>
      
      <div className="divide-y divide-gray-200">
        {dailyLogs.map((log) => (
          <div key={log.id} className="p-4 hover:bg-gray-50 transition-colors duration-150">
            <div 
              className="flex items-center justify-between cursor-pointer"
              onClick={() => toggleExpand(log.id)}
            >
              <h3 className="text-lg font-medium text-gray-800">
                {format(new Date(log.date), 'EEEE, MMMM dd, yyyy')}
              </h3>
              <div className="flex items-center">
                <div className="flex space-x-2 mr-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {log.total_driving_hours.toFixed(1)}h driving
                  </span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {log.total_off_duty_hours.toFixed(1)}h off-duty
                  </span>
                </div>
                <svg 
                  className={`h-5 w-5 text-gray-500 transform transition-transform duration-200 ${expandedLog === log.id ? 'rotate-180' : ''}`}
                  xmlns="http://www.w3.org/2000/svg" 
                  viewBox="0 0 20 20" 
                  fill="currentColor"
                >
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            
            {expandedLog === log.id && (
              <div className="mt-4 animated fadeIn">
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-white p-4 rounded-lg shadow-sm">
                      <div className="text-sm font-medium text-gray-500 mb-1">Driving Hours</div>
                      <div className="flex items-end">
                        <div className="text-2xl font-bold text-green-600">{log.total_driving_hours.toFixed(1)}</div>
                        <div className="text-sm text-gray-500 ml-1 mb-0.5">hours</div>
                      </div>
                    </div>
                    
                    <div className="bg-white p-4 rounded-lg shadow-sm">
                      <div className="text-sm font-medium text-gray-500 mb-1">On-Duty Hours</div>
                      <div className="flex items-end">
                        <div className="text-2xl font-bold text-yellow-600">{log.total_on_duty_hours.toFixed(1)}</div>
                        <div className="text-sm text-gray-500 ml-1 mb-0.5">hours</div>
                      </div>
                    </div>
                    
                    <div className="bg-white p-4 rounded-lg shadow-sm">
                      <div className="text-sm font-medium text-gray-500 mb-1">Off-Duty Hours</div>
                      <div className="flex items-end">
                        <div className="text-2xl font-bold text-blue-600">{log.total_off_duty_hours.toFixed(1)}</div>
                        <div className="text-sm text-gray-500 ml-1 mb-0.5">hours</div>
                      </div>
                    </div>
                    
                    <div className="bg-white p-4 rounded-lg shadow-sm">
                      <div className="text-sm font-medium text-gray-500 mb-1">Sleeper Berth</div>
                      <div className="flex items-end">
                        <div className="text-2xl font-bold text-purple-600">{log.total_sleeper_berth_hours.toFixed(1)}</div>
                        <div className="text-sm text-gray-500 ml-1 mb-0.5">hours</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-4 bg-white p-4 rounded-lg shadow-sm">
                    <div className="flex justify-between items-center mb-2">
                      <div className="text-sm font-medium text-gray-500">Odometer</div>
                      <div className="text-sm bg-gray-100 rounded-full px-3 py-1">
                        <span className="font-medium">{(log.ending_odometer - log.starting_odometer).toFixed(1)}</span> miles
                      </div>
                    </div>
                    <div className="relative pt-1">
                      <div className="flex mb-2 items-center justify-between">
                        <div className="text-xs font-semibold text-gray-600">{log.starting_odometer}</div>
                        <div className="text-right">
                          <span className="text-xs font-semibold text-gray-600">{log.ending_odometer}</span>
                        </div>
                      </div>
                      <div className="overflow-hidden h-2 text-xs flex rounded bg-gray-200">
                        <div className="w-full shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-indigo-500"></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Hour-by-Hour Status</h4>
                  <div className="flex mb-2">
                    <div className="flex items-center mr-4">
                      <div className="w-3 h-3 rounded-sm bg-green-500 mr-1"></div>
                      <span className="text-xs text-gray-600">Driving</span>
                    </div>
                    <div className="flex items-center mr-4">
                      <div className="w-3 h-3 rounded-sm bg-yellow-500 mr-1"></div>
                      <span className="text-xs text-gray-600">On Duty</span>
                    </div>
                    <div className="flex items-center mr-4">
                      <div className="w-3 h-3 rounded-sm bg-blue-400 mr-1"></div>
                      <span className="text-xs text-gray-600">Off Duty</span>
                    </div>
                    <div className="flex items-center">
                      <div className="w-3 h-3 rounded-sm bg-purple-400 mr-1"></div>
                      <span className="text-xs text-gray-600">Sleeper Berth</span>
                    </div>
                  </div>
                  {renderLogGrid(log.log_data)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {dailyLogs.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No daily logs available yet.</p>
        </div>
      )}
    </div>
  );
};

export default DailyLogViewer;