from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class htr(Asset):
	"""Electric heater converting electricity to heat."""

	ASSET_TYPE = "htr"
	DISPLAY_NAME = "Electric Heater"
	COLOR = "#ffb347"
	PRESETS = {
		"Default": {
			"max_kw": 3.0,
			"efficiency": 0.95,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "Power Input")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_out", "Heat Output")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.max_kw = self.get_float_param("max_kw", 3.0)
		self.efficiency = self.get_float_param("efficiency", 0.95)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				electricity_kw = self.sum_input("electricity_in")
				heat_out = min(electricity_kw, self.max_kw) * self.efficiency
				self.set_output("heat_out", max(heat_out, 0.0))

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
