from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class htr(Asset):
    """Electric heater that converts electricity to heat."""

    ASSET_TYPE = "htr"
    DISPLAY_NAME = "Heater"
    COLOR = "#e76f51"
    PRESETS = {
        "Default": {
            "capacity_kw": 5.0,
            "efficiency": 0.98,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "P_in (kW)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Q_out (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kw = self.get_float_param("capacity_kw", 5.0)
        self.efficiency = self.get_float_param("efficiency", 0.98)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                electric_in = min(self.sum_input("electricity_in"), self.capacity_kw)
                electric_in = max(electric_in, 0.0)
                heat_out = electric_in * self.efficiency
                self.set_output("heat_out", heat_out, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
