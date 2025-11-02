/**
 * Events feed API client - for live state sync
 */
import type { GameEvent } from '../types/events';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class EventsAPI {
  private baseUrl: string;
  private lastETag: string | null = null;
  private lastTimestamp: number = 0;

  constructor() {
    this.baseUrl = API_BASE_URL.replace(/\/$/, '');
  }

  /**
   * Fetch events since a timestamp, using ETag for efficient polling
   */
  async getEventsFeed(after?: number): Promise<GameEvent[]> {
    const params = new URLSearchParams();
    if (after) {
      params.append('after', after.toString());
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add If-None-Match header if we have an ETag
    if (this.lastETag) {
      headers['If-None-Match'] = this.lastETag;
    }

    const response = await fetch(
      `${this.baseUrl}/api/game/events/feed?${params.toString()}`,
      {
        method: 'GET',
        headers,
        credentials: 'include',
      }
    );

    // 304 Not Modified - no new events
    if (response.status === 304) {
      return [];
    }

    // 404 means endpoint doesn't exist yet - graceful degradation
    if (response.status === 404) {
      console.warn('Events feed endpoint not available yet - backend may not be updated');
      return [];
    }

    if (!response.ok) {
      throw new Error(`Events feed failed: ${response.status}`);
    }

    // Store ETag for next request
    const etag = response.headers.get('ETag');
    if (etag) {
      this.lastETag = etag;
    }

    const events: GameEvent[] = await response.json();
    
    // Update last timestamp if we got events
    if (events.length > 0) {
      this.lastTimestamp = Math.max(...events.map(e => e.timestamp));
    }

    return events;
  }

  /**
   * Get the last timestamp we've seen (for resuming after reconnection)
   */
  getLastTimestamp(): number {
    return this.lastTimestamp;
  }

  /**
   * Reset ETag and timestamp (e.g., after long idle period)
   */
  reset(): void {
    this.lastETag = null;
    this.lastTimestamp = 0;
  }
}

export const eventsAPI = new EventsAPI();

