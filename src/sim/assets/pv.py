from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset

class pv(Asset):
	"""Simple PV system with optional irradiance data-port input."""
	ASSET_TYPE = "pv"
	DISPLAY_NAME = "PV"
	COLOR = "#f6d365"
	PRESETS = {
		"Default": {
			"capacity_kwp": 10,
			"efficiency": 0.18,
			"azimuth_deg": 180,
			"tilt_deg": 35,
		},
		"Rooftop": {
			"capacity_kwp": 6,
			"efficiency": 0.19,
			"azimuth_deg": 180,
			"tilt_deg": 30,
		},
	}
	INPUT_PORTS = {
		"data": [("irradiance_in", "Irradiance")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "P_out")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)

		self.capacity_kwp = self.get_float_param("capacity_kwp", 0.0)
		self.efficiency = self.get_float_param("efficiency", 1.0)
		self.azimuth = self.get_param("azimuth_deg", 180)
		self.tilt = self.get_param("tilt_deg", 35)


		return None

	def _get_irradiance_kw(self) -> Optional[float]:
		"""Return normalised irradiance (kW/kWp) from the data input port, or None."""
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
				irradiance_kw = self._get_irradiance_kw()

				if irradiance_kw is None:
					output_kw = self.capacity_kwp * self.efficiency
				else:
					output_kw = self.capacity_kwp * self.efficiency * irradiance_kw

				output_kw = max(output_kw, 0.0)
				self.set_output("electricity_out", output_kw)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
