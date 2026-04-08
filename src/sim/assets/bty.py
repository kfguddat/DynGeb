from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bty(Asset):
	"""Battery storage asset: charges from surplus electricity and discharges on demand."""

	ASSET_TYPE = "bty"
	DISPLAY_NAME = "Battery"
	COLOR = "#a8d8ea"
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
			"max_charge_kw": 20.0,
			"max_discharge_kw": 20.0,
			"efficiency": 0.95,
			"initial_soc": 0.5,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "Charge")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "Discharge"), ("soc_kwh", "State of Charge (kWh)")]
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kwh = self.get_float_param("capacity_kwh", 10.0)
		self.max_charge_kw = self.get_float_param("max_charge_kw", 5.0)
		self.max_discharge_kw = self.get_float_param("max_discharge_kw", 5.0)
		self.efficiency = self.get_float_param("efficiency", 0.95)
		self.soc_kwh: float = self.get_float_param("initial_soc", 0.5) * self.capacity_kwh

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				charge_kw = min(self.sum_input("electricity_in"), self.max_charge_kw)
				charge_kw = min(charge_kw, (self.capacity_kwh - self.soc_kwh) / self.efficiency)
				charge_kw = max(charge_kw, 0.0)

				self.soc_kwh = min(self.soc_kwh + charge_kw * self.efficiency, self.capacity_kwh)
				discharge_kw = min(self.max_discharge_kw, self.soc_kwh)
				discharge_kw = max(discharge_kw, 0.0)

				self.set_output("electricity_out", discharge_kw)
				self.set_output("soc_kwh", self.soc_kwh)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
