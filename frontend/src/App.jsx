import React, { useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Navbar from './components/Navbar.jsx';
import TripPlanner from './pages/TripPlanner.jsx';
import SignInPage from './pages/SignIn.jsx';
import SignUpPage from './pages/SignUp.jsx';
import TripsPage from './pages/TripsPage.jsx';
import DailyLogsPage from './pages/DailyLogsPage.jsx';

// eslint-disable-next-line no-unused-vars
const PrivateRoute = ({ element: Element }) => {
  const isAuthenticated = !!localStorage.getItem('tokens');
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  return isAuthenticated ? <Element /> : null;
};

// Component to handle routing and Navbar visibility
const AppContent = () => {
  const location = useLocation();
  const showNavbar = location.pathname !== '/login' && location.pathname !== '/signup';

  return (
    <div>
      {showNavbar && <Navbar />}
      <Routes>
        <Route path="/login" element={<SignInPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/" element={<PrivateRoute element={TripPlanner} />} />
        <Route path="/trips" element={<PrivateRoute element={TripsPage} />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />
    </div>
  );
};

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;