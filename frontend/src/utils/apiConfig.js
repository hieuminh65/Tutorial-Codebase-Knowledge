// Get the appropriate API base URL based on the current environment
export const getApiBaseUrl = () => {
  const baseUrl = import.meta.env.VITE_BASE_URL;
  console.log("BASE_URL", baseUrl);
  return baseUrl || "http://localhost:5001/api";
};

// Export a configured API URL instance
export const API_BASE_URL = getApiBaseUrl();
