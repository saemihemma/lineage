/**
 * Rate limits / Fuel status API client
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface EndpointLimit {
  remaining: number;
  reset_at: number;
}

export interface LimitsStatus {
  window_seconds: number;
  now: number;
  endpoints: {
    [key: string]: EndpointLimit;
    combined: EndpointLimit;
  };
}

export class LimitsAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL.replace(/\/$/, '');
  }

  /**
   * Get current rate limit status (fuel bar data)
   */
  async getStatus(): Promise<LimitsStatus | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/game/limits/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      // 404 means endpoint doesn't exist yet - graceful degradation
      if (response.status === 404) {
        console.warn('Limits status endpoint not available yet - backend may not be updated');
        return null;
      }

      if (!response.ok) {
        throw new Error(`Limits status failed: ${response.status}`);
      }

      return response.json();
    } catch (err) {
      // Don't throw - graceful degradation
      if (err instanceof Error && err.message.includes('404')) {
        return null;
      }
      console.warn('Failed to fetch limits status:', err);
      return null;
    }
  }
}

export const limitsAPI = new LimitsAPI();

