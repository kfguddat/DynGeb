from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import yaml
from src.sim.asset import build_asset_catalog

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = PROJECT_ROOT / 'configs'
CONFIGS_DIR.mkdir(exist_ok=True)


@app.route('/api/configs', methods=['GET'])
def list_configs():
    """List all available config files"""
    try:
        files = [f.stem for f in CONFIGS_DIR.glob('*.yaml')]
        return jsonify({'files': sorted(files)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/asset-catalog', methods=['GET'])
def asset_catalog():
    """Expose asset UI configuration from Python asset classes."""
    try:
        catalog = build_asset_catalog()
        return jsonify({'catalog': catalog})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/configs/<filename>', methods=['GET'])
def load_config(filename: str):
    """Load a specific config file"""
    try:
        file_path = CONFIGS_DIR / f'{filename}.yaml'
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        with open(file_path, 'r') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/configs/<filename>', methods=['POST'])
def save_config(filename: str):
    """Save a config file"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        file_path = CONFIGS_DIR / f'{filename}.yaml'
        with open(file_path, 'w') as f:
            f.write(content)
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/configs/<filename>', methods=['DELETE'])
def delete_config(filename: str):
    """Delete a config file"""
    try:
        file_path = CONFIGS_DIR / f'{filename}.yaml'
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        file_path.unlink()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
