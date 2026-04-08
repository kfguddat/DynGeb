from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class rad(Asset):
    """Radiator / heat emitter asset that converts thermal supply to room heat."""

    ASSET_TYPE = "rad"
    DISPLAY_NAME = "Radiator"
    COLOR = "#d62828"
    PRESETS = {
        "Default": {
            "capacity_kw": 3.0,
            "efficiency": 0.95,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply (kW)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Emitted Heat (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kw = self.get_float_param("capacity_kw", 3.0)
        self.efficiency = self.get_float_param("efficiency", 0.95)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                heat_in = min(self.sum_input("heat_in"), self.capacity_kw)
                heat_in = max(heat_in, 0.0)
                heat_out = heat_in * self.efficiency
                self.set_output("heat_out", heat_out, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
