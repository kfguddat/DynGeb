from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cr(Asset):
    """Credit / loan asset that tracks debt repayment and monthly cash flow."""

    ASSET_TYPE = "cr"
    DISPLAY_NAME = "Credit"
    COLOR = "#9b5de5"
    PRESETS = {
        "Default": {
            "principal": 20000.0,
            "annual_interest_rate": 0.04,
            "annual_payment": 2500.0,
        },
    }
    INPUT_PORTS: Dict[str, Any] = {}
    OUTPUT_PORTS = {
        "monetary": [
            ("monthly_payment_out", "Monthly Payment (EUR)"),
            ("remaining_debt_out", "Remaining Debt (EUR)"),
        ],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.remaining_debt = self.get_float_param("principal", 20000.0)
        self.annual_interest_rate = self.get_float_param("annual_interest_rate", 0.04)
        self.annual_payment = self.get_float_param("annual_payment", 2500.0)
        self._last_month: Optional[int] = None

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                monthly_payment = 0.0
                if self._last_month != timestamp.month:
                    self._last_month = timestamp.month
                    monthly_interest = self.remaining_debt * (self.annual_interest_rate / 12)
                    monthly_annuity = self.annual_payment / 12
                    principal_payment = max(monthly_annuity - monthly_interest, 0.0)
                    self.remaining_debt = max(self.remaining_debt - principal_payment, 0.0)
                    monthly_payment = monthly_annuity

                self.set_output("monthly_payment_out", monthly_payment, timestamp=timestamp)
                self.set_output("remaining_debt_out", self.remaining_debt, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
