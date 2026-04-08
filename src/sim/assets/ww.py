from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class ww(Asset):
	"""Warm water (domestic hot water) system: consumes heat to supply hot water."""

	ASSET_TYPE = "ww"
	DISPLAY_NAME = "Warm Water"
	COLOR = "#f1c6a7"
	PRESETS = {
		"Default": {
			"demand_kw": 1.0,
		},
	}
	INPUT_PORTS = {
		"thermal": [("heat_in", "Heat Supply")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_demand", "Heat Demand")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.demand_kw = self.get_float_param("demand_kw", 1.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				self.set_output("heat_demand", self.demand_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
