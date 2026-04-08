from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class cnd(Asset):
    """Air conditioning / cooling unit.

    Consumes electricity and removes heat from the building.
    The Energy Efficiency Ratio (EER) relates cooling output to power input.
    """

    ASSET_TYPE = "cnd"
    DISPLAY_NAME = "Air Conditioning"
    COLOR = "#48cae4"
    PRESETS = {
        "Default": {
            "max_power_kw": 3.0,
            "eer": 3.0,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "Power In")],
        "data": [("temperature_in", "Outside Temperature (°C)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("cooling_out", "Cooling Output (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.max_power_kw = self.get_float_param("max_power_kw", 3.0)
        self.eer = self.get_float_param("eer", 3.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                power_kw = min(self.sum_input("electricity_in"), self.max_power_kw)
                cooling_kw = power_kw * self.eer
                self.set_output("cooling_out", cooling_kw)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
