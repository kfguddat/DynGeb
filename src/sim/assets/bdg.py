from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bdg(Asset):
	"""Building thermal model: consumes heat to maintain indoor temperature."""

	ASSET_TYPE = "bdg"
	DISPLAY_NAME = "Building"
	COLOR = "#c9ada7"
	PRESETS = {
		"Default": {
			"heat_demand_kw": 5.0,
			"floor_area_m2": 100.0,
		},
	}
	INPUT_PORTS = {
		"thermal": [("heat_in", "Heat Supply")],
		"electric": [("electricity_in", "Electricity")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_demand", "Heat Demand")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.heat_demand_kw = self.get_float_param("heat_demand_kw", 5.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				self.set_output("heat_demand", self.heat_demand_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
