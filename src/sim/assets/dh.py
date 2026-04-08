from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class dh(Asset):
	"""District heating connection."""

	ASSET_TYPE = "dh"
	DISPLAY_NAME = "District Heating"
	COLOR = "#fd79a8"
	PRESETS = {
		"Default": {
			"price_kw": 0.08,
			"max_kw": 50.0,
		},
	}
	INPUT_PORTS = {
		"monetary": [("payment_in", "Payment")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_out", "Heat Output")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.price_kw = self.get_float_param("price_kw", 0.08)
		self.max_kw = self.get_float_param("max_kw", 50.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				payment = self.sum_input("payment_in")
				if self.price_kw > 0:
					heat_out = min(payment / self.price_kw, self.max_kw)
				else:
					heat_out = self.max_kw
				self.set_output("heat_out", max(heat_out, 0.0))

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
