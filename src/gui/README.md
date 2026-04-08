# SolarSim GUI - React Frontend

React + React Flow frontend for browser-based configuration UI.

## Run

1. Install Node.js 20+.
2. Open terminal in `src/gui/`.
3. Install deps:
   - `npm install`
4. Start dev server:
   - `npm run dev`

## Backend API

The frontend requires the Flask API server running on port 5000:
```bash
python src/app.py
```

## Features

- Full-screen React Flow canvas for asset configuration.
- Sidebar-driven configuration.
- Add and configure assets (`pv`, `el`, `grd`).
- Connect assets into pipes.
- Select/edit node and edge properties.
- Save/load configuration files to `configs/` directory.
- Delete selected node/pipe with button or `Delete`/`Backspace`.
- YAML export/import compatible with list-style `assets` and `pipes`.

## Notes

- Browser file API is used for load/save in this frontend-only version.
- Integrating with Python simulation runtime can be done next via FastAPI endpoints.
