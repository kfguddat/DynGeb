#thermal model for building
#in: thermal 
#out: thermal
from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bdg(Asset):
	"""Simple building model with heat and electricity demand."""

	ASSET_TYPE = "bdg"
	DISPLAY_NAME = "Building"
	COLOR = "#dfe6e9"
	PRESETS = {
		"Default": {
			"heat_demand_kw": 5.0,
			"electricity_demand_kw": 2.0,
			"price_electricity": 0.25,
		},
	}
	INPUT_PORTS = {
		"thermal": [("heat_in", "Heat Input")],
		"electric": [("electricity_in", "Electricity")],
	}
	OUTPUT_PORTS = {
		"monetary": [("energy_cost", "Energy Cost")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.heat_demand_kw = self.get_float_param("heat_demand_kw", 5.0)
		self.electricity_demand_kw = self.get_float_param("electricity_demand_kw", 2.0)
		self.price_electricity = self.get_float_param("price_electricity", 0.25)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				electricity_kw = self.sum_input("electricity_in")
				energy_cost = electricity_kw * self.price_electricity
				self.set_output("energy_cost", energy_cost)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
