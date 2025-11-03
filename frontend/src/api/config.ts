/**
 * Config API client - handles game configuration
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface TraitDefinition {
  name: string;
  desc: string;
}

export interface GameplayConfig {
  traits?: Record<string, TraitDefinition>;
  [key: string]: any;
}

let cachedConfig: GameplayConfig | null = null;
let configFetchPromise: Promise<GameplayConfig> | null = null;

export async function fetchGameplayConfig(): Promise<GameplayConfig> {
  // Return cached config if available
  if (cachedConfig) {
    return cachedConfig;
  }

  // If fetch is already in progress, return that promise
  if (configFetchPromise) {
    return configFetchPromise;
  }

  // Start new fetch
  configFetchPromise = (async () => {
    try {
      const baseUrl = API_BASE_URL.replace(/\/$/, '');
      const response = await fetch(`${baseUrl}/api/config/gameplay`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch gameplay config: ${response.status}`);
      }

      const config = await response.json();
      cachedConfig = config;
      return config;
    } catch (err) {
      console.error('Failed to fetch gameplay config:', err);
      // Return empty config on error
      return {} as GameplayConfig;
    } finally {
      configFetchPromise = null;
    }
  })();

  return configFetchPromise;
}

