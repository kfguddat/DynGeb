from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bty(Asset):
	"""Battery energy storage."""

	ASSET_TYPE = "bty"
	DISPLAY_NAME = "Battery"
	COLOR = "#c3e88d"
	PRESETS = {
		"Default": {
			"capacity_kwh": 10.0,
			"max_charge_kw": 5.0,
			"max_discharge_kw": 5.0,
			"efficiency": 0.95,
			"initial_soc": 0.5,
		},
		"Large": {
			"capacity_kwh": 50.0,
			"max_charge_kw": 25.0,
			"max_discharge_kw": 25.0,
			"efficiency": 0.95,
			"initial_soc": 0.5,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "Charge Input")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "Discharge Output")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kwh = self.get_float_param("capacity_kwh", 10.0)
		self.max_charge_kw = self.get_float_param("max_charge_kw", 5.0)
		self.max_discharge_kw = self.get_float_param("max_discharge_kw", 5.0)
		self.efficiency = self.get_float_param("efficiency", 0.95)
		self.soc = self.get_float_param("initial_soc", 0.5)
		self._last_calc_ts: Optional[datetime] = None

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				if self._last_calc_ts == timestamp:
					return
				self._last_calc_ts = timestamp

				charge_kw = self.sum_input("electricity_in")
				max_charge = min(self.max_charge_kw, (1.0 - self.soc) * self.capacity_kwh)
				actual_charge = min(charge_kw, max(max_charge, 0.0))

				max_discharge = min(self.max_discharge_kw, self.soc * self.capacity_kwh)

				new_energy = self.soc * self.capacity_kwh + actual_charge * self.efficiency
				self.soc = max(0.0, min(1.0, new_energy / self.capacity_kwh))

				self.set_output("electricity_out", max(max_discharge, 0.0))

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
