from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cnd(Asset):
	"""Air conditioning unit: consumes electricity to produce cooling (negative heat)."""

	ASSET_TYPE = "cnd"
	DISPLAY_NAME = "Air Conditioning"
	COLOR = "#90e0ef"
	PRESETS = {
		"Default": {
			"capacity_kw": 3.0,
			"eer": 2.5,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "P_in")],
	}
	OUTPUT_PORTS = {
		"thermal": [("cooling_out", "Q_cool")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kw = self.get_float_param("capacity_kw", 3.0)
		self.eer = self.get_float_param("eer", 2.5)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				el_kw = min(self.sum_input("electricity_in"), self.capacity_kw)
				cooling_kw = max(el_kw * self.eer, 0.0)
				self.set_output("cooling_out", cooling_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
