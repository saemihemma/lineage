/**
 * Frontend API client for LINEAGE game
 * Uses async methods from the backend API client
 */
import { getOrCreateSessionId } from '../utils/localStorage';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface LeaderboardEntry {
  id: string;
  self_name: string;
  soul_level: number;
  soul_xp: number;
  clones_uploaded: number;
  total_expeditions: number;
  created_at: string;
  updated_at: string;
}

export interface LeaderboardSubmission {
  self_name: string;
  soul_level: number;
  soul_xp: number;
  clones_uploaded: number;
  total_expeditions: number;
}

class APIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL.replace(/\/$/, ''); // Remove trailing slash
  }

  private async makeRequest<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T | null> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const sessionId = getOrCreateSessionId();

      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId, // Send persistent session ID for rate limiting
          ...options?.headers,
        },
        credentials: 'include', // Important for cookies/sessions
      });

      if (!response.ok) {
        console.error(`API request failed: ${response.status} ${response.statusText}`);
        return null;
      }

      // Handle empty responses
      const text = await response.text();
      if (!text) {
        return null as T;
      }

      return JSON.parse(text) as T;
    } catch (error) {
      console.error('API request error:', error);
      return null;
    }
  }

  async isOnline(): Promise<boolean> {
    const response = await this.makeRequest<{ status: string }>('/api/health');
    return response?.status === 'healthy';
  }

  async fetchLeaderboard(limit: number = 100, offset: number = 0): Promise<LeaderboardEntry[]> {
    const response = await this.makeRequest<LeaderboardEntry[]>(
      `/api/leaderboard?limit=${limit}&offset=${offset}`
    );
    return response || [];
  }

  async submitToLeaderboard(submission: LeaderboardSubmission): Promise<boolean> {
    const response = await this.makeRequest<{ status: string }>(
      '/api/leaderboard/submit',
      {
        method: 'POST',
        body: JSON.stringify(submission),
      }
    );
    return response !== null;
  }

  async uploadTelemetry(events: any[]): Promise<boolean> {
    const response = await this.makeRequest<{ status: string }>(
      '/api/telemetry',
      {
        method: 'POST',
        body: JSON.stringify(events),
      }
    );
    return response !== null;
  }
}

// Export singleton instance
export const apiClient = new APIClient();

