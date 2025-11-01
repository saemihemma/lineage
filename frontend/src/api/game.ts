/**
 * Game API client - handles game state and actions
 */
import type { GameState } from '../types/game';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class GameAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL.replace(/\/$/, '');
  }

  private async makeRequest<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      credentials: 'include', // Important for cookies
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `API request failed: ${response.status}`);
    }

    return response.json();
  }

  async getState(): Promise<GameState> {
    return this.makeRequest<GameState>('/api/game/state');
  }

  async saveState(state: GameState): Promise<void> {
    await this.makeRequest('/api/game/state', {
      method: 'POST',
      body: JSON.stringify(state),
    });
  }

  async gatherResource(resource: string): Promise<{ state: GameState; message: string; amount: number }> {
    return this.makeRequest(`/api/game/gather-resource?resource=${encodeURIComponent(resource)}`, {
      method: 'POST',
    });
  }

  async buildWomb(): Promise<{ state: GameState; message: string }> {
    return this.makeRequest('/api/game/build-womb', {
      method: 'POST',
    });
  }

  async growClone(kind: string): Promise<{ 
    state: GameState; 
    clone: any; 
    soul_split: number; 
    message: string 
  }> {
    return this.makeRequest(`/api/game/grow-clone?kind=${encodeURIComponent(kind)}`, {
      method: 'POST',
    });
  }

  async applyClone(cloneId: string): Promise<{ state: GameState; message: string }> {
    return this.makeRequest(`/api/game/apply-clone?clone_id=${encodeURIComponent(cloneId)}`, {
      method: 'POST',
    });
  }

  async runExpedition(kind: string): Promise<{ state: GameState; message: string }> {
    return this.makeRequest(`/api/game/run-expedition?kind=${encodeURIComponent(kind)}`, {
      method: 'POST',
    });
  }

  async uploadClone(cloneId: string): Promise<{ state: GameState; message: string }> {
    return this.makeRequest(`/api/game/upload-clone?clone_id=${encodeURIComponent(cloneId)}`, {
      method: 'POST',
    });
  }
}

export const gameAPI = new GameAPI();

