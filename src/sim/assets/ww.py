from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class ww(Asset):
    """Domestic hot water preparation.

    Consumes heat (and optionally electricity for a booster pump) to
    produce domestic hot water.  Heat demand is modelled as a flat daily
    profile scaled to a configured annual demand.
    """

    ASSET_TYPE = "ww"
    DISPLAY_NAME = "Warm Water"
    COLOR = "#90e0ef"
    PRESETS = {
        "Default": {
            "annual_demand_kwh": 2000.0,
            "t_target": 60.0,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply")],
        "electric": [("electricity_in", "Pump Power")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_demand_out", "Heat Demand (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.annual_demand_kwh = self.get_float_param("annual_demand_kwh", 2000.0)
        # Hourly demand (uniform distribution)
        self.hourly_demand_kw = self.annual_demand_kwh / 8760.0

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                self.set_output("heat_demand_out", self.hourly_demand_kw)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
