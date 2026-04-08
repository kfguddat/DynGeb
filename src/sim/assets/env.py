from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class env(Asset):
	"""Environment asset that reads TRY weather data."""

	ASSET_TYPE = "env"
	DISPLAY_NAME = "Environment"
	COLOR = "#b8e4f9"
	PRESETS = {
		"Default": {
			"data_file": "",
			"irradiance_default": 500.0,
			"temperature_default": 10.0,
		}
	}
	INPUT_PORTS = {}
	OUTPUT_PORTS = {
		"data": [
			("irradiance", "Global Irradiance"),
			("temperature", "Air Temperature"),
		],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self._weather_data: list = []
		self._irradiance_default = self.get_float_param("irradiance_default", 500.0)
		self._temperature_default = self.get_float_param("temperature_default", 10.0)
		data_file = self.get_param("data_file", "")
		if data_file:
			self._load_try_data(data_file)

	def _load_try_data(self, file_path: str) -> None:
		"""Load DWD TRY weather data file (fixed-width text format)."""
		try:
			with open(file_path, "r", encoding="latin-1") as fh:
				for line in fh:
					stripped = line.strip()
					if not stripped or stripped.startswith("*") or stripped.startswith("RW"):
						continue
					parts = stripped.split()
					if len(parts) < 14:
						continue
					try:
						row = {
							"mm": int(parts[2]),
							"dd": int(parts[3]),
							"hh": int(parts[4]),
							"t": float(parts[5]),
							"B": float(parts[12]),
							"D": float(parts[13]),
						}
						self._weather_data.append(row)
					except (ValueError, IndexError):
						continue
		except OSError:
			pass

	def _get_data_for_timestamp(self, timestamp: datetime) -> Dict[str, float]:
		"""Return weather dict for a given timestamp, falling back to defaults."""
		mm = timestamp.month
		dd = timestamp.day
		hh = timestamp.hour + 1  # TRY uses hours 1-24

		for row in self._weather_data:
			if row["mm"] == mm and row["dd"] == dd and row["hh"] == hh:
				return row
		return {"t": self._temperature_default, "B": 0.0, "D": 0.0}

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				data = self._get_data_for_timestamp(timestamp)
				irradiance = max(data.get("B", 0.0) + data.get("D", 0.0), 0.0)
				temperature = data.get("t", self._temperature_default)
				self.set_output("irradiance", irradiance)
				self.set_output("temperature", temperature)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
