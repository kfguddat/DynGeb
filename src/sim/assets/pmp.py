from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pmp(Asset):
    """Heat pump.

    Extracts heat from a low-temperature source (ambient air or ground)
    and delivers it at a higher temperature using electrical power.
    The Coefficient of Performance (COP) scales linearly with the
    source temperature above a minimum threshold.
    """

    ASSET_TYPE = "pmp"
    DISPLAY_NAME = "Heat Pump"
    COLOR = "#2a9d8f"
    PRESETS = {
        "Default": {
            "max_power_kw": 5.0,
            "cop_nominal": 3.5,
        },
        "Air Source": {
            "max_power_kw": 8.0,
            "cop_nominal": 3.0,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "Power In")],
        "data": [("temperature_in", "Source Temperature (°C)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Heat Out")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.max_power_kw = self.get_float_param("max_power_kw", 5.0)
        self.cop_nominal = self.get_float_param("cop_nominal", 3.5)

    def _cop(self) -> float:
        """COP adjusted for source temperature (-10 °C baseline at 3.5 nominal)."""
        raw = self.inputs.get("temperature_in")
        if raw is None:
            return self.cop_nominal
        t_source = float(raw)
        # Simple linear adjustment: +0.05 COP per °C above -10 °C
        cop = self.cop_nominal + 0.05 * (t_source - (-10.0))
        return max(cop, 1.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                power_kw = min(self.sum_input("electricity_in"), self.max_power_kw)
                heat_out_kw = power_kw * self._cop()
                self.set_output("heat_out", heat_out_kw)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
