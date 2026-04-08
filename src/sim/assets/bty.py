from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bty(Asset):
    """Battery energy storage with charge/discharge logic."""

    ASSET_TYPE = "bty"
    DISPLAY_NAME = "Battery"
    COLOR = "#a8dadc"
    PRESETS = {
        "Default": {
            "capacity_kwh": 10.0,
            "max_charge_kw": 5.0,
            "max_discharge_kw": 5.0,
            "efficiency": 0.95,
            "initial_soc": 0.5,
        },
        "Small Home": {
            "capacity_kwh": 5.0,
            "max_charge_kw": 2.5,
            "max_discharge_kw": 2.5,
            "efficiency": 0.95,
            "initial_soc": 0.5,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "Charge")],
    }
    OUTPUT_PORTS = {
        "electric": [("electricity_out", "Discharge")],
        "monetary": [("soc_out", "State of Charge")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.capacity_kwh = self.get_float_param("capacity_kwh", 10.0)
        self.max_charge_kw = self.get_float_param("max_charge_kw", 5.0)
        self.max_discharge_kw = self.get_float_param("max_discharge_kw", 5.0)
        self.efficiency = self.get_float_param("efficiency", 0.95)
        self.soc: float = self.get_float_param("initial_soc", 0.5)  # 0..1

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                charge_kw = min(self.sum_input("electricity_in"), self.max_charge_kw)
                charge_kwh = charge_kw * self.efficiency

                available_kwh = self.soc * self.capacity_kwh
                discharge_kwh = min(available_kwh, self.max_discharge_kw)
                discharge_kw = discharge_kwh / max(self.efficiency, 1e-6)

                # Update state of charge (1-hour timestep assumed)
                energy_delta = charge_kwh - discharge_kwh
                new_energy = max(0.0, min(self.capacity_kwh, available_kwh + energy_delta))
                self.soc = new_energy / max(self.capacity_kwh, 1e-6)

                self.set_output("electricity_out", discharge_kw)
                self.set_output("soc_out", self.soc)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
