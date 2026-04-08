from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class dh(Asset):
    """District heating connection asset."""

    ASSET_TYPE = "dh"
    DISPLAY_NAME = "District Heating"
    COLOR = "#e63946"
    PRESETS = {
        "Default": {
            "price_per_kwh": 0.08,
            "import_kw": 0.0,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Return Heat (kW)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Supply Heat (kW)")],
        "monetary": [("cost_out", "Cost (EUR)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.price_per_kwh = self.get_float_param("price_per_kwh", 0.08)
        self.import_kw = self.get_float_param("import_kw", 0.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                supplied_kw = self.import_kw
                cost = supplied_kw * self.price_per_kwh
                self.set_output("heat_out", supplied_kw, timestamp=timestamp)
                self.set_output("cost_out", cost, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
