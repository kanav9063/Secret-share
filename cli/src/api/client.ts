import fetch from 'node-fetch';
import { loadAuth } from '../config.js';

// Base URL for our backend API
const API_BASE = 'http://localhost:8001';

/**
 * Make an authenticated request to our backend.
 * Automatically includes the JWT token from saved auth.
 */
export async function authenticatedFetch(path: string, options: any = {}) {
  // 1. Get saved auth token
  const auth = loadAuth();
  if (!auth.token) {
    throw new Error('Not authenticated. Please login first.');
  }

  // 2. Build full URL
  const url = `${API_BASE}${path}`;

  // 3. Add auth header to request
  const headers = {
    'Authorization': `Bearer ${auth.token}`,
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // 4. Make the request
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // 5. Handle response
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication failed. Please login again.');
    }
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  // 6. Parse JSON response
  return response.json();
}