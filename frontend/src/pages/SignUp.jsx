import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { signup } from '../services/api';
import ClipLoader from 'react-spinners/ClipLoader';
import { toast } from 'react-toastify';

const SignUpPage = () => {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPasswordVisible, setConfirmPasswordVisible] = useState(false);
  const [form, setForm] = useState({
    email: '',
    firstName: '',
    lastName: '',
    password: '',
    confirmPassword: '',
    address: '',
    phoneNumber: '',
    zipCode: '',
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const togglePassword = () => setPasswordVisible(!passwordVisible);
  const toggleConfirmPassword = () => setConfirmPasswordVisible(!confirmPasswordVisible);

  // Password validation function
  const isStrongPassword = (password) => {
    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
    return strongPasswordRegex.test(password);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    // Check if passwords match
    if (form.password !== form.confirmPassword) {
      toast.error('Passwords do not match', {
        position: 'top-right',
        autoClose: 5000,
      });
      setLoading(false);
      return;
    }

    // Check if password is strong
    if (!isStrongPassword(form.password)) {
      toast.error(
        'Password must be at least 8 characters long and include an uppercase letter, lowercase letter, number, and special character (e.g., !@#$%^&*)',
        {
          position: 'top-right',
          autoClose: 5000,
        }
      );
      setLoading(false);
      return;
    }

    try {
      const response = await signup({
        email: form.email,
        first_name: form.firstName,
        last_name: form.lastName,
        password: form.password,
        address: form.address,
        phone_number: form.phoneNumber,
        zip_code: form.zipCode,
      });
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user_id', response.data.id);
      toast.success('Signed up successfully!', {
        position: 'top-right',
        autoClose: 3000,
      });
      navigate('/');
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.email?.[0] || 'Signup failed';
      toast.error(errorMsg, {
        position: 'top-right',
        autoClose: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full my-6 max-w-4xl p-6 bg-white rounded-2xl shadow-xl">
      <div className='flex items-center justify-center'>
          <svg xmlns="http://www.w3.org/2000/svg" className={`h-8 w-8 mr-2 text-indigo-300`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h2 className="text-3xl font-bold text-center text-gray-800">Trip Planner</h2>
        </div>
        <p className="mt-2 text-sm text-center text-gray-500">Create your account</p>

        <form className="mt-6 space-y-6 md:space-y-0 md:grid md:grid-cols-2 md:gap-6" onSubmit={handleSubmit}>
          {/* Email (Full Width) */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              placeholder="Enter your email"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
              disabled={loading}
            />
          </div>

          {/* First Name and Last Name (Side by Side on Large Screens) */}
          <div>
            <label className="block text-sm font-medium text-gray-700">First Name</label>
            <input
              type="text"
              placeholder="Enter your first name"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.firstName}
              onChange={(e) => setForm({ ...form, firstName: e.target.value })}
              required
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Last Name</label>
            <input
              type="text"
              placeholder="Enter your last name"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.lastName}
              onChange={(e) => setForm({ ...form, lastName: e.target.value })}
              required
              disabled={loading}
            />
          </div>

          {/* Password (Full Width) */}
          <div className="md:col-span-2 relative">
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type={passwordVisible ? 'text' : 'password'}
              placeholder="Enter your password"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              disabled={loading}
            />
            <button
              type="button"
              className="absolute right-3 top-10 text-gray-500"
              onClick={togglePassword}
              disabled={loading}
            >
              {passwordVisible ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>

          {/* Confirm Password (Full Width) */}
          <div className="md:col-span-2 relative">
            <label className="block text-sm font-medium text-gray-700">Confirm Password</label>
            <input
              type={confirmPasswordVisible ? 'text' : 'password'}
              placeholder="Confirm your password"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.confirmPassword}
              onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
              required
              disabled={loading}
            />
            <button
              type="button"
              className="absolute right-3 top-10 text-gray-500"
              onClick={toggleConfirmPassword}
              disabled={loading}
            >
              {confirmPasswordVisible ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>

          {/* Address and Phone Number (Side by Side on Large Screens) */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Address</label>
            <input
              type="text"
              placeholder="Enter your address"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Phone Number</label>
            <input
              type="text"
              placeholder="Enter your phone number"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.phoneNumber}
              onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })}
              disabled={loading}
            />
          </div>

          {/* Zip Code (Full Width) */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Zip Code</label>
            <input
              type="text"
              placeholder="Enter your zip code"
              className="mt-1 w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-200 focus:outline-none"
              value={form.zipCode}
              onChange={(e) => setForm({ ...form, zipCode: e.target.value })}
              disabled={loading}
            />
          </div>

          {/* Sign Up Button (Full Width) */}
          <div className="md:col-span-2">
            <button
              type="submit"
              className="w-full p-3 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 flex items-center justify-center"
              disabled={loading}
            >
              {loading ? <ClipLoader size={20} color="#ffffff" /> : 'Sign Up'}
            </button>
          </div>
        </form>

        {/* Sign In Link */}
        <p className="mt-6 text-center text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default SignUpPage;