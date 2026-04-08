from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class el(Asset):
    """Simple electric load with static demand."""

    ASSET_TYPE = "el"
    DISPLAY_NAME = "Electric Load"
    COLOR = "#a0e7b3"
    PRESETS = {
        "Household": {
            "type": "static",
            "load_kw": 1,
        },
        "Commercial": {
            "type": "static",
            "load_kw": 4,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "P_in")],
    }
    OUTPUT_PORTS: Dict[str, Any] = {}

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.load_kw = self.get_float_param("load_kw", 0.0)
        self.load_type = str(self.get_param("type", "static"))

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                supplied_kw = self.sum_input("electricity_in")
                self.set_output("load_kw", self.load_kw, timestamp=timestamp)
                self.set_output("supplied_kw", supplied_kw, timestamp=timestamp)
                self.set_output("unmet_kw", max(self.load_kw - supplied_kw, 0.0), timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
