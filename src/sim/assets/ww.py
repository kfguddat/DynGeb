from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class ww(Asset):
    """Warm water / domestic hot water demand asset."""

    ASSET_TYPE = "ww"
    DISPLAY_NAME = "Warm Water"
    COLOR = "#f77f00"
    PRESETS = {
        "Default": {
            "daily_demand_kwh": 5.0,
            "tank_capacity_kwh": 10.0,
            "tank_loss_rate": 0.01,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply (kW)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_demand_out", "Heat Demand (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.daily_demand_kwh = self.get_float_param("daily_demand_kwh", 5.0)
        self.tank_capacity_kwh = self.get_float_param("tank_capacity_kwh", 10.0)
        self.tank_loss_rate = self.get_float_param("tank_loss_rate", 0.01)
        self.stored_kwh: float = self.tank_capacity_kwh * 0.5

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                hourly_demand = self.daily_demand_kwh / 24.0
                tank_loss = self.stored_kwh * self.tank_loss_rate
                heat_in = self.sum_input("heat_in")

                self.stored_kwh = max(
                    0.0,
                    min(
                        self.tank_capacity_kwh,
                        self.stored_kwh + heat_in - hourly_demand - tank_loss,
                    ),
                )
                self.set_output("heat_demand_out", hourly_demand, timestamp=timestamp)
                self.set_output("stored_kwh", self.stored_kwh, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
