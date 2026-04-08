from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cr(Asset):
	"""Credit/loan with monthly annuity payments."""

	ASSET_TYPE = "cr"
	DISPLAY_NAME = "Credit"
	COLOR = "#fdcb6e"
	PRESETS = {
		"Default": {
			"principal": 50000.0,
			"interest_rate_annual": 0.05,
			"duration_years": 20,
		},
	}
	INPUT_PORTS = {}
	OUTPUT_PORTS = {
		"monetary": [("payment_out", "Monthly Payment")],
	}

	def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
		super().__init__(name=name, params=params)
		self.principal = self.get_float_param("principal", 50000.0)
		self.interest_rate_annual = self.get_float_param("interest_rate_annual", 0.05)
		self.duration_years = self.get_float_param("duration_years", 20.0)
		self._monthly_payment = self._compute_annuity()

	def _compute_annuity(self) -> float:
		r = self.interest_rate_annual / 12.0
		n = self.duration_years * 12.0
		if r == 0.0 or n == 0.0:
			return self.principal / n if n > 0 else 0.0
		return self.principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

	def calc(self, *args: Any, **kwargs: Any) -> Any:
		if args and isinstance(args[0], datetime):
			timestamp = args[0]

			def compute() -> None:
				self.set_output("payment_out", self._monthly_payment)

			self._run_timestamp_calc(timestamp, compute)
			return None

		if len(args) >= 2:
			return self._calc_for_port(args[0], args[1], value=args[2] if len(args) >= 3 else None)

		raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
