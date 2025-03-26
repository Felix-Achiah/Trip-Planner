import { jwtDecode } from 'jwt-decode';

const getAccessToken = () => {
    // Check if window is defined (to determine if the code is running in the browser)
  if (typeof window !== 'undefined') {
    // Access localStorage only if window is defined (browser environment)
    const userTokens= localStorage.getItem('tokens');
    return userTokens ? JSON.parse(userTokens)?.tokens?.access_token : '';
  }
}

const getRefreshToken = () => {
  // Check if window is defined (to determine if the code is running in the browser)
if (typeof window !== 'undefined') {
  // Access localStorage only if window is defined (browser environment)
  const userTokens = localStorage.getItem('tokens');
  return userTokens ? JSON.parse(userTokens)?.tokens?.refresn_token : '';
}
}

const getUser = () => {
  // Ensure getAccessToken is called to fetch the token
  const access_token = getAccessToken();
  if (typeof window !== 'undefined' && access_token) {
    try {
      const userDetails = jwtDecode(access_token);
      return userDetails;
    } catch (error) {
      console.error('Failed to decode token', error);
      return null;
    }
  }
  return null;
};

export { getAccessToken, getRefreshToken, getUser }