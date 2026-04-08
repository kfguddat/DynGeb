from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cr(Asset):
	"""Credit/loan asset: tracks outstanding debt and monthly payments."""

	ASSET_TYPE = "cr"
	DISPLAY_NAME = "Credit"
	COLOR = "#d4a5a5"
	PRESETS = {
		"Default": {
			"principal": 10000.0,
			"interest_rate": 0.05,
			"annuity": 1200.0,
		},
	}
	INPUT_PORTS: Dict[str, Any] = {}
	OUTPUT_PORTS = {
		"monetary": [("payment_out", "Monthly Payment"), ("balance_out", "Balance")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.principal = self.get_float_param("principal", 10000.0)
		self.interest_rate = self.get_float_param("interest_rate", 0.05)
		self.annuity = self.get_float_param("annuity", 1200.0)
		self.balance: float = self.principal

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				monthly_payment = self.annuity / 12.0
				self.set_output("payment_out", monthly_payment)
				self.set_output("balance_out", self.balance)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			port = args[0]
			timestamp = args[1]
			value = args[2] if len(args) >= 3 else None
			return self._calc_for_port(port, timestamp, value=value)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
