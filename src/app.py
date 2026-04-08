import sys
import subprocess
import threading
from pathlib import Path
import time

# Ensure `src` package imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from src.server import app as flask_app

GUI_DIR = PROJECT_ROOT / 'src' / 'gui'


def start_frontend():
	"""Start Vite dev server in src/gui"""
	try:
		print("Starting frontend dev server (Vite)...")
		subprocess.run(
			['npm.cmd' if sys.platform == 'win32' else 'npm', 'run', 'dev'],
			cwd=str(GUI_DIR),
			check=False
		)
	except FileNotFoundError as e:
		print(f"Error starting frontend: npm not found ({e}). Please install Node.js and ensure npm is on PATH.")
	except Exception as e:
		print(f"Error starting frontend: {e}")


if __name__ == "__main__":
	# Start frontend in a background thread
	frontend_thread = threading.Thread(target=start_frontend, daemon=True)
	frontend_thread.start()
	
	# Give frontend a moment to start
	time.sleep(3)
	
	print("Starting backend API server...")
	print("Frontend will be available at http://localhost:5173")
	print("Backend API available at http://localhost:5000")
	
	# Start Flask server (blocks)
	flask_app.run(debug=False, port=5000)


