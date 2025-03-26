import React, { useState, useEffect, useRef } from 'react';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';

import { getUser } from '../utils/fetchUser';

const DailyLogSheet = ({ dailyLogs, trip }) => {
  const [user, setUser] = useState(null);
  const canvasRefs = useRef([]); // Store canvas refs for each daily log

  useEffect(() => {
    const userDetails = getUser();
    setUser(userDetails);
  }, [trip]);

  useEffect(() => {
    dailyLogs?.forEach((dailyLog, index) => {
      drawGrid(dailyLog, index);
    });
  }, [dailyLogs]);

  const calculateCycleTotals = () => {
    // Mocked for now; query past DailyLog entries in production
    return { driving: 60, onDuty: 65 };
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

    // eslint-disable-next-line no-unused-vars
    dailyLog.log_data.forEach((entry, idx) => {
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
    });

    // Draw final segment to end of day
    ctx.beginPath();
    ctx.strokeStyle = statusColors[lastStatus];
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(width, lastY);
    ctx.stroke();
  };

  const downloadPDF = (dailyLog, index) => {
    const canvas = canvasRefs.current[index];
    const doc = new jsPDF();
    doc.setFontSize(12);

    // Header
    doc.text('DRIVER\'S DAILY LOG', 105, 10, { align: 'center' });
    doc.setFontSize(8);
    doc.text(`Date: ${dailyLog.date}`, 10, 20);
    doc.text(`Driver: ${user?.name || 'N/A'}`, 10, 25);
    doc.text(`Carrier: ${user?.carrier || 'N/A'}`, 10, 30);
    doc.text(`From: ${trip.current_location.name}`, 50, 20);
    doc.text(`To: ${trip.dropoff_location.name}`, 50, 25);
    doc.text(`Total Miles: ${(dailyLog.total_driving_hours * 55).toFixed(1)}`, 90, 20);

    // Add canvas image (grid)
    const imgData = canvas.toDataURL('image/png');
    doc.addImage(imgData, 'PNG', 10, 40, 190, 30); // 190mm wide, 30mm tall

    // Summary
    doc.text('Summary', 10, 80);
    doc.autoTable({
      startY: 85,
      head: [['Status', 'Hours']],
      body: [
        ['Off Duty', dailyLog.total_off_duty_hours.toFixed(2)],
        ['Sleeper Berth', dailyLog.total_sleeper_berth_hours.toFixed(2)],
        ['Driving', dailyLog.total_driving_hours.toFixed(2)],
        ['On Duty Not Driving', dailyLog.total_on_duty_hours.toFixed(2)],
      ],
    });

    // Cycle Totals
    const cycleTotals = calculateCycleTotals();
    doc.text('70-Hour/8-Day Cycle', 10, doc.lastAutoTable.finalY + 10);
    doc.autoTable({
      startY: doc.lastAutoTable.finalY + 15,
      head: [['Category', 'Hours']],
      body: [
        ['Driving', cycleTotals.driving],
        ['On Duty', cycleTotals.onDuty],
      ],
    });

    doc.save(`DailyLog_${dailyLog.date}.pdf`);
  };

  return (
    <div className="space-y-6">
      {dailyLogs?.map((dailyLog, index) => (
        <div key={index} className="p-6 bg-white rounded-lg shadow-md">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-gray-800">Daily Log - {dailyLog.date}</h2>
            <button
              onClick={() => downloadPDF(dailyLog, index)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              Download PDF
            </button>
          </div>

          {/* Header */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-600"><strong>Driver:</strong> {user?.name || 'N/A'}</p>
              <p className="text-sm text-gray-600"><strong>Carrier:</strong> {user?.carrier || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600"><strong>From:</strong> {trip.current_location.name}</p>
              <p className="text-sm text-gray-600"><strong>To:</strong> {trip.dropoff_location.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600"><strong>Total Miles:</strong> {(dailyLog.total_driving_hours * 55).toFixed(1)}</p>
            </div>
          </div>

          {/* Log Grid */}
          <div className="mb-4">
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

          {/* Summary */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-600"><strong>Off Duty:</strong> {dailyLog.total_off_duty_hours.toFixed(2)} hrs</p>
            </div>
            <div>
              <p className="text-sm text-gray-600"><strong>Sleeper Berth:</strong> {dailyLog.total_sleeper_berth_hours.toFixed(2)} hrs</p>
            </div>
            <div>
              <p className="text-sm text-gray-600"><strong>Driving:</strong> {dailyLog.total_driving_hours.toFixed(2)} hrs</p>
            </div>
            <div>
              <p className="text-sm text-gray-600"><strong>On Duty Not Driving:</strong> {dailyLog.total_on_duty_hours.toFixed(2)} hrs</p>
            </div>
          </div>

          {/* Cycle Totals */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">70-Hour/8-Day Cycle</h3>
            <div className="grid grid-cols-2 gap-4">
              <p className="text-sm text-gray-600"><strong>Driving:</strong> {calculateCycleTotals().driving} hrs</p>
              <p className="text-sm text-gray-600"><strong>On Duty:</strong> {calculateCycleTotals().onDuty} hrs</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DailyLogSheet;