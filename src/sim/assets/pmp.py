from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pmp(Asset):
	"""Heat pump: converts electricity to heat using COP > 1."""

	ASSET_TYPE = "pmp"
	DISPLAY_NAME = "Heat Pump"
	COLOR = "#457b9d"
	PRESETS = {
		"Default": {
			"capacity_kw": 5.0,
			"cop": 3.0,
		},
		"High COP": {
			"capacity_kw": 5.0,
			"cop": 4.5,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "P_in")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_out", "Q_out")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kw = self.get_float_param("capacity_kw", 5.0)
		self.cop = self.get_float_param("cop", 3.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				el_kw = min(self.sum_input("electricity_in"), self.capacity_kw)
				heat_kw = max(el_kw * self.cop, 0.0)
				self.set_output("heat_out", heat_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
