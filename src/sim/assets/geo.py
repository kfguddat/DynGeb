from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class geo(Asset):
	"""Geothermal heat source: provides heat at a fixed output."""

	ASSET_TYPE = "geo"
	DISPLAY_NAME = "Geothermal"
	COLOR = "#6b705c"
	PRESETS = {
		"Default": {
			"capacity_kw": 5.0,
			"cop": 4.0,
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
		self.cop = self.get_float_param("cop", 4.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				el_kw = min(self.sum_input("electricity_in"), self.capacity_kw / self.cop)
				# capacity_kw / cop = max electrical input for the rated heat output
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
