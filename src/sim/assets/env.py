from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class env(Asset):
	"""Environment asset providing weather data (temperature, irradiance) to other assets."""

	ASSET_TYPE = "env"
	DISPLAY_NAME = "Environment"
	COLOR = "#aed6f1"
	PRESETS = {
		"Default": {
			"temperature_c": 10.0,
			"irradiance_kwpm2": 0.5,
		},
	}
	INPUT_PORTS: Dict[str, Any] = {}
	OUTPUT_PORTS = {
		"data": [
			("temperature_out", "Ambient Temp (°C)"),
			("irradiance_out", "Irradiance (kW/m²)"),
		],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.temperature_c = self.get_float_param("temperature_c", 10.0)
		self.irradiance_kwpm2 = self.get_float_param("irradiance_kwpm2", 0.5)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				self.set_output("temperature_out", self.temperature_c)
				self.set_output("irradiance_out", self.irradiance_kwpm2)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
