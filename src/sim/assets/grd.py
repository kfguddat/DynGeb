from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset

class grd(Asset):
	"""Simple grid connection for import/export with fixed prices."""

	ASSET_TYPE = "grd"
	DISPLAY_NAME = "Grid"
	COLOR = "#8fd3f4"
	PRESETS = {
		"Default": {
			"type": "static",
			"price_import": 0.25,
			"price_export": 0.15,
			"import_kw": 0,
		},
		"High Tariff": {
			"type": "static",
			"price_import": 0.35,
			"price_export": 0.12,
			"import_kw": 0,
		},
	}
	INPUT_PORTS = {
		"electric": [("electricity_in", "Export to Grid")],
	}
	OUTPUT_PORTS = {
		"electric": [("electricity_out", "Import from Grid")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)

		self.price_import = self.get_float_param("price_import", 0.0)
		self.price_export = self.get_float_param("price_export", 0.0)
		self.import_kw = self.get_float_param("import_kw", 0.0)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				exported_kw = self.sum_input("electricity_in")
				imported_kw = self.import_kw

				import_cost = imported_kw * self.price_import
				export_revenue = exported_kw * self.price_export
				net_cost = import_cost - export_revenue

				self.set_output("electricity_out", imported_kw)
				self.set_output("import_cost", import_cost)
				self.set_output("export_revenue", export_revenue)
				self.set_output("net_cost", net_cost)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
