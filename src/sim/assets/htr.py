from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class htr(Asset):
    """Electric resistance heater.

    Converts electricity to heat with a fixed efficiency (typically close to 1.0).
    """

    ASSET_TYPE = "htr"
    DISPLAY_NAME = "Heater"
    COLOR = "#e76f51"
    PRESETS = {
        "Default": {
            "max_power_kw": 5.0,
            "efficiency": 0.99,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "Power In")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Heat Out")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.max_power_kw = self.get_float_param("max_power_kw", 5.0)
        self.efficiency = self.get_float_param("efficiency", 0.99)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                power_in_kw = min(self.sum_input("electricity_in"), self.max_power_kw)
                heat_out_kw = power_in_kw * self.efficiency
                self.set_output("heat_out", heat_out_kw)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
