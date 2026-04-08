from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pvt(Asset):
    """Photovoltaic-Thermal (PVT) collector.

    Produces both electricity and useful heat from solar irradiance.
    Electrical output mirrors a standard PV panel; thermal output is
    proportional to irradiance and collector area.
    """

    ASSET_TYPE = "pvt"
    DISPLAY_NAME = "PV-Thermal"
    COLOR = "#e9c46a"
    PRESETS = {
        "Default": {
            "capacity_kwp": 5.0,
            "efficiency_electric": 0.12,
            "efficiency_thermal": 0.45,
            "azimuth_deg": 180,
            "tilt_deg": 35,
        },
    }
    INPUT_PORTS = {
        "data": [
            ("irradiance_in", "Irradiance (W/m²)"),
            ("temperature_in", "Outside Temperature (°C)"),
        ],
    }
    OUTPUT_PORTS = {
        "electric": [("electricity_out", "P_electric (kW)")],
        "thermal": [("heat_out", "Q_thermal (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.capacity_kwp = self.get_float_param("capacity_kwp", 5.0)
        self.efficiency_electric = self.get_float_param("efficiency_electric", 0.12)
        self.efficiency_thermal = self.get_float_param("efficiency_thermal", 0.45)

    def _irradiance_factor(self) -> float:
        raw = self.inputs.get("irradiance_in")
        if raw is None:
            return 1.0
        return max(float(raw), 0.0) / 1000.0

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                factor = self._irradiance_factor()
                p_electric = max(self.capacity_kwp * self.efficiency_electric * factor, 0.0)
                # Thermal output uses the remaining irradiance after electrical conversion
                p_thermal = max(self.capacity_kwp * self.efficiency_thermal * factor, 0.0)
                self.set_output("electricity_out", p_electric)
                self.set_output("heat_out", p_thermal)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
