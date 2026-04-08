from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cr(Asset):
    """Loan / credit asset.

    Tracks an outstanding debt balance and computes monthly interest and
    repayment (annuity method).  The annuity is debited from the monetary
    output every hour proportionally (annuity / 8760).
    """

    ASSET_TYPE = "cr"
    DISPLAY_NAME = "Credit"
    COLOR = "#c77dff"
    PRESETS = {
        "Default": {
            "principal": 20000.0,
            "annual_rate": 0.03,
            "annuity": 2000.0,
        },
    }
    INPUT_PORTS = {
        "monetary": [("payment_in", "Repayment")],
    }
    OUTPUT_PORTS = {
        "monetary": [
            ("interest_out", "Interest (hourly)"),
            ("repayment_out", "Repayment (hourly)"),
            ("balance_out", "Remaining Balance"),
        ],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.balance = self.get_float_param("principal", 20000.0)
        self.annual_rate = self.get_float_param("annual_rate", 0.03)
        self.annuity = self.get_float_param("annuity", 2000.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                if self.balance <= 0.0:
                    self.set_output("interest_out", 0.0)
                    self.set_output("repayment_out", 0.0)
                    self.set_output("balance_out", 0.0)
                    return

                # Hourly fractions of annual payments
                hourly_interest = self.balance * self.annual_rate / 8760.0
                hourly_annuity = self.annuity / 8760.0
                hourly_repayment = max(hourly_annuity - hourly_interest, 0.0)

                self.balance = max(self.balance - hourly_repayment, 0.0)

                self.set_output("interest_out", hourly_interest)
                self.set_output("repayment_out", hourly_repayment)
                self.set_output("balance_out", self.balance)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
