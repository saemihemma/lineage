# LINEAGE Web Frontend

React + TypeScript frontend for LINEAGE game.

## Setup

```bash
# Install dependencies
npm install

# Sync data files (briefing text, etc.) from project root
npm run sync-data
# Or manually: ./scripts/sync_data_to_frontend.sh

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

## Updating Text Content

When you update text files in `data/` directory:

```bash
# Run sync script to copy to frontend
npm run sync-data

# Or manually:
./scripts/sync_data_to_frontend.sh    # Mac/Linux
scripts\sync_data_to_frontend.bat     # Windows
```

Changes will be visible immediately on browser refresh (no rebuild needed).

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
