from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pvt(Asset):
	"""PV-Thermal hybrid panel (combined electricity and heat output)."""

	ASSET_TYPE = "pvt"
	DISPLAY_NAME = "PV-Thermal"
	COLOR = "#ffeaa7"
	PRESETS = {
		"Default": {
			"capacity_kwp": 10.0,
			"pv_efficiency": 0.15,
			"thermal_efficiency": 0.40,
		},
	}
	INPUT_PORTS = {
		"data": [("irradiance_in", "Irradiance")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "P_out")],
		"thermal": [("heat_out", "Q_out")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kwp = self.get_float_param("capacity_kwp", 10.0)
		self.pv_efficiency = self.get_float_param("pv_efficiency", 0.15)
		self.thermal_efficiency = self.get_float_param("thermal_efficiency", 0.40)

	def _get_irradiance_kw(self) -> Optional[float]:
		val = self.get_input("irradiance_in")
		if val is None:
			return None
		try:
			return float(val) / 1000.0
		except (TypeError, ValueError):
			return None

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				irradiance_kw = self._get_irradiance_kw()
				if irradiance_kw is None:
					irradiance_factor = 1.0
				else:
					irradiance_factor = irradiance_kw

				electricity_out = self.capacity_kwp * self.pv_efficiency * irradiance_factor
				heat_out = self.capacity_kwp * self.thermal_efficiency * irradiance_factor

				self.set_output("electricity_out", max(electricity_out, 0.0))
				self.set_output("heat_out", max(heat_out, 0.0))

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
