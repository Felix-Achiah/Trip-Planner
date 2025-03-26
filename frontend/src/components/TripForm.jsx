import React, { useState } from 'react';
import { toast } from 'react-toastify';
import ClipLoader from 'react-spinners/ClipLoader';
import { geocodeAddress, createTrip } from '../services/api';

const TripForm = ({ onTripCreated }) => {
  const [formData, setFormData] = useState({
    title: '', // Changed from 'New Trip' to empty string for dynamic input
    currentLocation: '',
    pickupLocation: '',
    dropoffLocation: '',
    currentCycleHours: 0,
    startTime: new Date().toISOString().slice(0, 16),
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Geocode all locations
      const [current, pickup, dropoff] = await Promise.all([
        geocodeAddress(formData.currentLocation),
        geocodeAddress(formData.pickupLocation),
        geocodeAddress(formData.dropoffLocation),
      ]);

      // Fetch user ID from localStorage
      const tokens = localStorage.getItem('tokens');
      const userId = JSON.parse(tokens)?.user_id;
      if (!userId) {
        throw new Error('User ID not found in localStorage. Please log in again.');
      }

      const tripData = {
        title: formData.title || 'New Trip', // Fallback to 'New Trip' if title is empty
        current_location: {
          name: formData.currentLocation,
          latitude: current.data.latitude,
          longitude: current.data.longitude,
          address: current.data.address,
        },
        pickup_location: {
          name: formData.pickupLocation,
          latitude: pickup.data.latitude,
          longitude: pickup.data.longitude,
          address: pickup.data.address,
        },
        dropoff_location: {
          name: formData.dropoffLocation,
          latitude: dropoff.data.latitude,
          longitude: dropoff.data.longitude,
          address: dropoff.data.address,
        },
        current_cycle_hours: parseFloat(formData.currentCycleHours),
        start_time: formData.startTime,
        user: userId,
      };

      const response = await createTrip(tripData);
      onTripCreated(response.data.id);
      toast.success('Trip created successfully!', {
        position: 'top-right',
        autoClose: 3000,
      });
    } catch (error) {
      console.error('Error creating trip:', error);
      toast.error('Failed to create trip', {
        position: 'top-right',
        autoClose: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md my-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center md:text-left">Create Trip</h2>
      <form onSubmit={handleSubmit} className="space-y-6 md:grid md:grid-cols-2 md:gap-6 md:space-y-0">
        {/* Trip Title */}
        <div className="space-y-2">
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Trip Title
          </label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
            placeholder="Enter trip title"
          />
        </div>

        {/* Current Location */}
        <div className="space-y-2">
          <label htmlFor="currentLocation" className="block text-sm font-medium text-gray-700">
            Current Location
          </label>
          <input
            type="text"
            id="currentLocation"
            name="currentLocation"
            value={formData.currentLocation}
            onChange={handleChange}
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
            placeholder="Enter current location"
          />
        </div>

        {/* Pickup Location */}
        <div className="space-y-2">
          <label htmlFor="pickupLocation" className="block text-sm font-medium text-gray-700">
            Pickup Location
          </label>
          <input
            type="text"
            id="pickupLocation"
            name="pickupLocation"
            value={formData.pickupLocation}
            onChange={handleChange}
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
            placeholder="Enter pickup location"
          />
        </div>

        {/* Dropoff Location */}
        <div className="space-y-2">
          <label htmlFor="dropoffLocation" className="block text-sm font-medium text-gray-700">
            Dropoff Location
          </label>
          <input
            type="text"
            id="dropoffLocation"
            name="dropoffLocation"
            value={formData.dropoffLocation}
            onChange={handleChange}
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
            placeholder="Enter dropoff location"
          />
        </div>

        {/* Current Cycle Hours */}
        <div className="space-y-2">
          <label htmlFor="currentCycleHours" className="block text-sm font-medium text-gray-700">
            Current Cycle Hours
          </label>
          <input
            type="number"
            id="currentCycleHours"
            name="currentCycleHours"
            value={formData.currentCycleHours}
            onChange={handleChange}
            min="0"
            max="70"
            step="0.1"
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
            placeholder="Enter cycle hours"
          />
        </div>

        {/* Start Time */}
        <div className="space-y-2">
          <label htmlFor="startTime" className="block text-sm font-medium text-gray-700">
            Start Time
          </label>
          <input
            type="datetime-local"
            id="startTime"
            name="startTime"
            value={formData.startTime}
            onChange={handleChange}
            required
            disabled={loading}
            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none disabled:bg-gray-100"
          />
        </div>

        {/* Submit Button */}
        <div className="md:col-span-2 flex justify-center md:justify-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full md:w-auto px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? (
              <ClipLoader size={20} color="#ffffff" />
            ) : (
              'Create Trip'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default TripForm;