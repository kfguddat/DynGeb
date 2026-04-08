from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pvt(Asset):
    """PV-Thermal (PVT) collector that generates both electricity and heat."""

    ASSET_TYPE = "pvt"
    DISPLAY_NAME = "PV-Thermal"
    COLOR = "#f6ae2d"
    PRESETS = {
        "Default": {
            "capacity_kwp": 6.0,
            "pv_efficiency": 0.15,
            "thermal_efficiency": 0.40,
        },
    }
    INPUT_PORTS = {
        "data": [
            ("irradiance_in", "Irradiance (W/m2)"),
            ("temperature_in", "Outdoor Temperature (C)"),
        ],
    }
    OUTPUT_PORTS = {
        "electric": [("electricity_out", "P_out (kW)")],
        "thermal": [("heat_out", "Q_out (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kwp = self.get_float_param("capacity_kwp", 6.0)
        self.pv_efficiency = self.get_float_param("pv_efficiency", 0.15)
        self.thermal_efficiency = self.get_float_param("thermal_efficiency", 0.40)

    def _get_irradiance_fraction(self) -> Optional[float]:
        raw = self.get_input("irradiance_in")
        if raw is None:
            return None
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None
        if val > 2.0:
            val = val / 1000.0
        return max(val, 0.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                irr = self._get_irradiance_fraction()
                if irr is None:
                    irr = 0.5

                elec_out = self.capacity_kwp * self.pv_efficiency * irr
                heat_out = self.capacity_kwp * self.thermal_efficiency * irr
                self.set_output("electricity_out", max(elec_out, 0.0), timestamp=timestamp)
                self.set_output("heat_out", max(heat_out, 0.0), timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
