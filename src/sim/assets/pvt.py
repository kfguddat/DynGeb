from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pvt(Asset):
	"""Photovoltaic-Thermal (PVT) collector: produces both electricity and heat."""

	ASSET_TYPE = "pvt"
	DISPLAY_NAME = "PVT"
	COLOR = "#f9c74f"
	PRESETS = {
		"Default": {
			"capacity_kwp": 5.0,
			"pv_efficiency": 0.15,
			"thermal_efficiency": 0.40,
			"azimuth_deg": 180,
			"tilt_deg": 35,
		},
	}
	INPUT_PORTS = {
		"data": [("irradiance_in", "Irradiance")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "P_el")],
		"thermal": [("heat_out", "Q_th")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.capacity_kwp = self.get_float_param("capacity_kwp", 5.0)
		self.pv_efficiency = self.get_float_param("pv_efficiency", 0.15)
		self.thermal_efficiency = self.get_float_param("thermal_efficiency", 0.40)

	def _get_irradiance_kw(self) -> Optional[float]:
		raw = self.get_input("irradiance_in")
		if raw is None:
			return None
		try:
			return float(raw)
		except (TypeError, ValueError):
			return None

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				irradiance = self._get_irradiance_kw()
				factor = irradiance if irradiance is not None else 1.0
				el_kw = max(self.capacity_kwp * self.pv_efficiency * factor, 0.0)
				heat_kw = max(self.capacity_kwp * self.thermal_efficiency * factor, 0.0)
				self.set_output("electricity_out", el_kw)
				self.set_output("heat_out", heat_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
