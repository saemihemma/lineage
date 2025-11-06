# LINEAGE Web Frontend

React + TypeScript frontend for LINEAGE game.

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

## Data Files

Game data files (JSON configuration, messages, etc.) are loaded directly from the backend API or served via the backend's static file serving. No manual syncing is required for web deployment.

## Project Structure

```
src/
├── api/           # API client for backend communication
├── components/    # Reusable UI components
├── screens/       # Main screen components (Briefing, Loading, Simulation)
├── hooks/         # Custom React hooks
├── types/         # TypeScript type definitions
└── styles/        # Global styles and theme
```

## Development

The frontend runs on `http://localhost:5173` by default (Vite dev server).

Make sure the backend API is running on `http://localhost:8000` (or update `VITE_API_URL`).
