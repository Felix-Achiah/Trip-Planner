import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';

import { login } from '../services/api';
import ClipLoader from 'react-spinners/ClipLoader';
import { toast } from 'react-toastify';

const SignInPage = () => {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', remember: false });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const togglePassword = () => setPasswordVisible(!passwordVisible);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await login({ email: form.email, password: form.password });
      const { access_token, refresh_token, user_id} = response.data;
      localStorage.setItem('tokens', JSON.stringify({
        access_token,
        refresh_token,
        user_id
      }));
      toast.success('Signed in successfully!', {
        position: 'top-right',
        autoClose: 3000,
      });
      navigate('/');
    } catch (err) {
      const errorMsg = err.response?.data || 'Invalid email or password';
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
      <div className="w-full max-w-md p-6 bg-white rounded-2xl shadow-xl">
        <div className='flex items-center justify-center'>
          <svg xmlns="http://www.w3.org/2000/svg" className={`h-8 w-8 mr-2 text-indigo-300`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h2 className="text-3xl font-bold text-center text-gray-800">Trip Planner</h2>
        </div>
        <p className="mt-2 text-sm text-center text-gray-500">Sign in to your account</p>

        <form className="mt-6" onSubmit={handleSubmit}>
          {/* Email Input */}
          <div>
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

          {/* Password Input */}
          <div className="mt-4 relative">
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

          {/* Remember Me & Forgot Password */}
          <div className="mt-4 flex items-center justify-between">
            <label className="flex items-center text-sm">
              <input
                type="checkbox"
                className="mr-2"
                checked={form.remember}
                onChange={(e) => setForm({ ...form, remember: e.target.checked })}
                disabled={loading}
              />
              Remember me
            </label>
            {/* <Link to="/forgot-password" className="text-sm text-blue-600 hover:underline">
              Forgot password?
            </Link> */}
          </div>

          {/* Sign In Button with Circular Progress */}
          <button
            type="submit"
            className="mt-6 w-full p-3 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 flex items-center justify-center"
            disabled={loading}
          >
            {loading ? (
              <ClipLoader size={20} color="#ffffff" />
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Sign Up Link */}
        <p className="mt-4 text-center text-sm">
          Don’t have an account?{' '}
          <Link to="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
};

export default SignInPage;