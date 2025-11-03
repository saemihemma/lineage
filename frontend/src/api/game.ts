/**
 * Game API client - handles game state and actions
 */
import type { GameState } from '../types/game';
import { loadStateFromLocalStorage, getOrCreateSessionId } from '../utils/localStorage';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class GameAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL.replace(/\/$/, '');
  }

  /**
   * Get current state from localStorage (for sending with actions)
   */
  private getCurrentState(): GameState | null {
    return loadStateFromLocalStorage();
  }

  private async makeRequest<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const sessionId = getOrCreateSessionId();

      // Log request details for debugging
      console.log(`🌐 API Request: ${options?.method || 'GET'} ${endpoint}`, {
        url,
        baseUrl: this.baseUrl,
        sessionId: sessionId,
        hasCredentials: true,
      });

      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId, // Send persistent session ID for rate limiting
          ...options?.headers,
        },
        credentials: 'include', // Important for cookies
      });

      // Check if session cookie is present in response
      const setCookieHeader = response.headers.get('Set-Cookie');
      if (setCookieHeader) {
        console.log(`🍪 Cookie set in response: ${setCookieHeader.substring(0, 50)}...`);
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        const errorMsg = error.detail || `API request failed: ${response.status}`;
        console.error(`❌ API Error: ${options?.method || 'GET'} ${endpoint}`, {
          status: response.status,
          statusText: response.statusText,
          error: errorMsg,
        });
        throw new Error(errorMsg);
      }

      const data = await response.json();
      console.log(`✅ API Response: ${options?.method || 'GET'} ${endpoint}`, {
        status: response.status,
        hasState: 'state' in data,
        hasWombs: 'state' in data && Array.isArray(data.state?.wombs),
        wombCount: 'state' in data && Array.isArray(data.state?.wombs) ? data.state.wombs.length : 0,
      });
      
      return data;
    } catch (err) {
      // Enhanced error handling for network issues
      if (err instanceof TypeError && err.message.includes('fetch')) {
        // Network error - fetch failed (CORS, DNS, connection refused, etc.)
        console.error(`🌐 Network Error: ${options?.method || 'GET'} ${endpoint}`, {
          url,
          baseUrl: this.baseUrl,
          error: err.message,
          suggestion: 'Check if API is running and CORS is configured correctly',
        });
        const networkError = new Error(`Network error: ${err.message}. API URL: ${this.baseUrl}`);
        (networkError as any).name = 'NetworkError';
        throw networkError;
      }
      
      // Re-throw other errors (including Error from response handling)
      throw err;
    }
  }

  // State management moved to localStorage - these methods are no longer used
  async getState(): Promise<GameState> {
    console.warn('getState() called but state is now managed via localStorage');
    throw new Error('State management moved to localStorage. Use loadStateFromLocalStorage() instead.');
  }

  async saveState(_state: GameState): Promise<GameState | void> {
    console.warn('saveState() called but state is now managed via localStorage');
    throw new Error('State management moved to localStorage. Use saveStateToLocalStorage() instead.');
  }

  async gatherResource(resource: string): Promise<{ state: GameState; message: string; amount: number }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/gather-resource?resource=${encodeURIComponent(resource)}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async buildWomb(): Promise<{ state: GameState; message: string }> {
    const currentState = this.getCurrentState();
    return this.makeRequest('/api/game/build-womb', {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async growClone(kind: string): Promise<{ 
    state: GameState; 
    clone: any; 
    soul_split: number; 
    message: string 
  }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/grow-clone?kind=${encodeURIComponent(kind)}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async applyClone(cloneId: string): Promise<{ state: GameState; message: string }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/apply-clone?clone_id=${encodeURIComponent(cloneId)}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async runExpedition(kind: string): Promise<{ state: GameState; message: string }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/run-expedition?kind=${encodeURIComponent(kind)}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async uploadClone(cloneId: string): Promise<{ state: GameState; message: string }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/upload-clone?clone_id=${encodeURIComponent(cloneId)}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async repairWomb(wombId: number): Promise<{ 
    state: GameState; 
    message: string; 
    cost: Record<string, number>;
    repair_time: number;
    task_id: string;
  }> {
    const currentState = this.getCurrentState();
    return this.makeRequest(`/api/game/repair-womb?womb_id=${wombId}`, {
      method: 'POST',
      body: JSON.stringify(currentState || {}),
    });
  }

  async getTaskStatus(): Promise<{
    active: boolean;
    task: {
      id: string;
      type: string;
      progress: number;
      elapsed: number;
      remaining: number;
      duration: number;
      label: string;
    } | null;
    completed?: boolean;
  }> {
    return this.makeRequest('/api/game/tasks/status');
  }
}

export const gameAPI = new GameAPI();

