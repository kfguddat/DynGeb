# SolarSim

A Python-based solar simulation and configuration tool with a modern React frontend.

## Project Structure

```
solarsim/
├── configs/              Configuration files (YAML)
├── data/                 Input data files
├── sims/                 Simulation results
└── src/
    ├── gui/              React frontend (src/gui/)
    │   ├── src/          React application code
    │   ├── public/       Static assets
    │   └── package.json
    ├── sim/              Simulation engine
    │   └── assets/       Asset type implementations
    ├── app.py            Flask API server entry point
    ├── server.py         Flask API server
    └── simulation.py      Simulation orchestration
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 20+

### Backend (Flask API)

1. Install Python dependencies:
   ```bash
   pip install -r requirements-api.txt
   ```

2. Run the API server:
   ```bash
   python src/app.py
   ```
   The API will be available at `http://localhost:5000`

### Frontend (React)

1. Navigate to the frontend directory:
   ```bash
   cd src/gui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

### Running Together

In development, you need to run both servers:
- Terminal 1: `python src/app.py` (Backend)
- Terminal 2: `cd src/gui && npm run dev` (Frontend)

The frontend proxies API calls to the backend via the Vite dev server configuration.

## Features

- **React Flow Canvas**: Interactive node-based configuration interface
- **Asset Management**: Add and configure various asset types (PV, Load, Grid)
- **Pipe Connections**: Define energy/resource flows between assets
- **File Management**: Save/load configurations as YAML files
- **Sidebar Controls**: Edit asset properties and manage files

## Configuration Files

Configuration files are stored in `configs/` directory as YAML files. You can:
- Create new configurations
- Load existing configurations
- Save current configuration with a new name
- Clone configurations

## Development

The frontend is built with:
- React 18
- React Flow for graph visualization
- TypeScript
- Vite for bundling

The backend uses:
- Flask for API routes
- PyYAML for configuration serialization
