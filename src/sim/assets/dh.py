from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class dh(Asset):
	"""District heating connection: imports heat from the district heating network."""

	ASSET_TYPE = "dh"
	DISPLAY_NAME = "District Heating"
	COLOR = "#e07a5f"
	PRESETS = {
		"Default": {
			"price_import": 0.08,
			"import_kw": 0.0,
		},
	}
	INPUT_PORTS = {
		"monetary": [("payment_in", "Payment")],
	}
	OUTPUT_PORTS = {
		"thermal": [("heat_out", "Q_out")],
		"monetary": [("cost_out", "Cost")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.price_import = self.get_float_param("price_import", 0.08)
		self.import_kw = self.get_float_param("import_kw", 0.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				heat_kw = max(self.import_kw, 0.0)
				cost = heat_kw * self.price_import
				self.set_output("heat_out", heat_kw)
				self.set_output("cost_out", cost)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
