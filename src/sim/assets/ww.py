from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class ww(Asset):
	"""Domestic hot water demand (thermal sink)."""

	ASSET_TYPE = "ww"
	DISPLAY_NAME = "Warm Water"
	COLOR = "#81ecec"
	PRESETS = {
		"Default": {
			"demand_kw": 1.0,
		},
	}
	INPUT_PORTS = {
		"thermal": [("heat_in", "Heat Input")],
	}
	OUTPUT_PORTS = {}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.demand_kw = self.get_float_param("demand_kw", 1.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				pass  # demand signalled via demand_kw; heat_in set by resolver

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
