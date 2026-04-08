from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cnd(Asset):
	"""Air conditioning / cooling unit."""

	ASSET_TYPE = "cnd"
	DISPLAY_NAME = "Air Conditioning"
	COLOR = "#74b9ff"
	PRESETS = {
		"Default": {
			"max_kw": 5.0,
			"cop": 2.5,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "Power Input")],
	}
	OUTPUT_PORTS = {
		"thermal": [("cooling_out", "Cooling Output")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.max_kw = self.get_float_param("max_kw", 5.0)
		self.cop = self.get_float_param("cop", 2.5)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				electricity_kw = self.sum_input("electricity_in")
				cooling_out = min(electricity_kw, self.max_kw) * self.cop
				self.set_output("cooling_out", max(cooling_out, 0.0))

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
