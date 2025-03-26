import React, { useState, useEffect } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';

import { getUser } from '../utils/fetchUser';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [username, setUsername] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  

  useEffect(() => {
    if(user) {
      setUsername(`${user?.first_name} ${user?.last_name}`)
    }

    // Add scroll event listener
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // Close mobile menu when route changes
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const toggleMenu = () => setIsOpen(!isOpen);

  const handleLogout = () => {
    localStorage.removeItem('tokens');
    localStorage.removeItem('user_id');
    toast.info('Logged out successfully!', { 
      position: 'top-right',
      icon: '👋'
    });
    navigate('/login');
  };

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${
      scrolled ? 'bg-white shadow-md text-gray-800' : 'bg-gradient-to-r from-indigo-800 to-indigo-900 text-white'
    }`}>
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-8 w-8 mr-2 ${scrolled ? 'text-indigo-600' : 'text-indigo-300'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              <span className={`font-bold text-xl ${scrolled ? 'text-indigo-700' : 'text-white'}`}>
                TripPlanner
              </span>
            </Link>
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:block">
            <div className="flex items-center space-x-4">
              <NavLink 
                to="/" 
                className={({ isActive }) => 
                  `px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    isActive 
                      ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white') 
                      : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
                  }`
                }
              >
                Dashboard
              </NavLink>
              
              <NavLink 
                to="/trips" 
                className={({ isActive }) => 
                  `px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    isActive 
                      ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white') 
                      : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
                  }`
                }
              >
                My Trips
              </NavLink>
              
              <NavLink 
                to="/daily-logs" 
                className={({ isActive }) => 
                  `px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    isActive 
                      ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white') 
                      : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
                  }`
                }
              >
                Daily Logs
              </NavLink>
            </div>
          </div>

          {/* User Menu */}
          <div className="hidden md:block">
            <div className="flex items-center">
              <div className="relative group">
                <button 
                  className={`flex items-center text-sm font-medium rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                    scrolled 
                      ? 'focus:ring-indigo-500 text-gray-700' 
                      : 'focus:ring-white text-white'
                  }`}
                >
                  <span className="sr-only">Open user menu</span>
                  <div className={`h-8 w-8 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center ${
                    scrolled ? 'text-white' : 'text-white'
                  }`}>
                    {username.charAt(0).toUpperCase()}
                  </div>
                  <span className="ml-2">{username}</span>
                  <svg className="ml-1 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
                <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-300">
                  {/* <Link to="/profile" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Your Profile
                  </Link>
                  <Link to="/settings" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Settings
                  </Link> */}
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={toggleMenu}
              className={`inline-flex items-center justify-center p-2 rounded-md ${
                scrolled 
                  ? 'text-gray-700 hover:text-gray-900 hover:bg-gray-100' 
                  : 'text-indigo-100 hover:text-white hover:bg-indigo-700'
              } focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white`}
              aria-expanded="false"
            >
              <span className="sr-only">Open main menu</span>
              {!isOpen ? (
                <svg className="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              ) : (
                <svg className="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className={`${isOpen ? 'block' : 'hidden'} md:hidden`}>
        <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-base font-medium ${
                isActive
                  ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white')
                  : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
              }`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/trips"
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-base font-medium ${
                isActive
                  ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white')
                  : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
              }`
            }
          >
            My Trips
          </NavLink>
          <NavLink
            to="/daily-logs"
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-base font-medium ${
                isActive
                  ? (scrolled ? 'bg-indigo-100 text-indigo-700' : 'bg-indigo-700 text-white')
                  : (scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white')
              }`
            }
          >
            Daily Logs
          </NavLink>
        </div>
        <div className="pt-4 pb-3 border-t border-indigo-800">
          <div className="flex items-center px-5">
            <div className="flex-shrink-0">
              <div className="h-10 w-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center text-white">
                {username.charAt(0).toUpperCase()}
              </div>
            </div>
            <div className="ml-3">
              <div className={`text-base font-medium ${scrolled ? 'text-gray-800' : 'text-white'}`}>{username}</div>
              <div className={`text-sm font-medium ${scrolled ? 'text-gray-500' : 'text-indigo-300'}`}>Truck Driver</div>
            </div>
          </div>
          <div className="mt-3 px-2 space-y-1">
            {/* <Link 
              to="/profile"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white'
              }`}
            >
              Your Profile
            </Link>
            <Link 
              to="/settings"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white'
              }`}
            >
              Settings
            </Link> */}
            <button
              onClick={handleLogout}
              className={`block w-full text-left px-3 py-2 rounded-md text-base font-medium ${
                scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-indigo-100 hover:bg-indigo-700 hover:text-white'
              }`}
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;