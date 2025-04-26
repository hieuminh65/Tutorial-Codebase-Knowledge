// Get the appropriate API base URL based on the current environment
export const getApiBaseUrl = () => {
  // Simply use the local development URL
  return "http://localhost:5001/api";
};

// Export a configured API URL instance
export const API_BASE_URL = getApiBaseUrl();
