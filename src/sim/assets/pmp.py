from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class pmp(Asset):
    """Air-source heat pump with temperature-dependent COP."""

    ASSET_TYPE = "pmp"
    DISPLAY_NAME = "Heat Pump"
    COLOR = "#457b9d"
    PRESETS = {
        "Default": {
            "capacity_kw": 8.0,
            "cop_nominal": 3.5,
            "t_source_nominal": 7.0,
            "t_sink": 45.0,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "P_in (kW)")],
        "data": [("temperature_in", "Source Temperature (C)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_out", "Q_out (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kw = self.get_float_param("capacity_kw", 8.0)
        self.cop_nominal = self.get_float_param("cop_nominal", 3.5)
        self.t_source_nominal = self.get_float_param("t_source_nominal", 7.0)
        self.t_sink = self.get_float_param("t_sink", 45.0)

    def _cop(self, t_source: float) -> float:
        """Estimate COP for given source temperature using linear correction."""
        delta = t_source - self.t_source_nominal
        cop = self.cop_nominal + 0.05 * delta
        return max(cop, 1.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                t_source_raw = self.get_input("temperature_in")
                try:
                    t_source = float(t_source_raw) if t_source_raw is not None else self.t_source_nominal
                except (TypeError, ValueError):
                    t_source = self.t_source_nominal

                cop = self._cop(t_source)
                electric_in = min(self.sum_input("electricity_in"), self.capacity_kw)
                electric_in = max(electric_in, 0.0)
                heat_out = electric_in * cop
                self.set_output("heat_out", heat_out, timestamp=timestamp)
                self.set_output("cop", cop, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
