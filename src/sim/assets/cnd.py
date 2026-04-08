from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cnd(Asset):
    """Air-conditioning / cooling asset."""

    ASSET_TYPE = "cnd"
    DISPLAY_NAME = "Air Conditioning"
    COLOR = "#48cae4"
    PRESETS = {
        "Default": {
            "capacity_kw": 5.0,
            "eer": 3.0,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "P_in (kW)")],
        "data": [("temperature_in", "Outdoor Temperature (C)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("cooling_out", "Cooling (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kw = self.get_float_param("capacity_kw", 5.0)
        self.eer = self.get_float_param("eer", 3.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                electric_in = min(self.sum_input("electricity_in"), self.capacity_kw)
                electric_in = max(electric_in, 0.0)
                cooling_out = electric_in * self.eer
                self.set_output("cooling_out", cooling_out, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
