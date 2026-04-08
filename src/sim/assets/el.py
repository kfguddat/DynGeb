from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset

class el(Asset):
	"""Simple electric load with static demand."""

	ASSET_TYPE = "el"
	DISPLAY_NAME = "Electric Load"
	COLOR = "#a0e7b3"
	PRESETS = {
		"Household": {
			"type": "static",
			"load_kw": 1,
		},
		"Commercial": {
			"type": "static",
			"load_kw": 4,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "P_in")],
	}
	OUTPUT_PORTS = {
		"thermal": [("thermal output", "Q_out")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)

		self.load_kw = self.get_float_param("load_kw", 0.0)
		self.load_type = str(self.get_param("type", "static"))

	def calc(port: Port, 
