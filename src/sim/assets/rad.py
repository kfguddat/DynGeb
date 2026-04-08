from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class rad(Asset):
    """Radiator / heat emitter.

    Distributes heat supplied via the thermal input port to the room.
    Models a simple fixed-flow radiator.
    """

    ASSET_TYPE = "rad"
    DISPLAY_NAME = "Radiator"
    COLOR = "#f4a261"
    PRESETS = {
        "Default": {
            "max_heat_kw": 5.0,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Heat Emitted")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.max_heat_kw = self.get_float_param("max_heat_kw", 5.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                heat_in_kw = min(self.sum_input("heat_in"), self.max_heat_kw)
                self.set_output("heat_out", heat_in_kw)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
