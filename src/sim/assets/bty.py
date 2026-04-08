from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bty(Asset):
    """Battery storage asset with charge/discharge logic."""

    ASSET_TYPE = "bty"
    DISPLAY_NAME = "Battery"
    COLOR = "#90be6d"
    PRESETS = {
        "Default": {
            "capacity_kwh": 10,
            "max_charge_kw": 3.5,
            "max_discharge_kw": 3.5,
            "efficiency": 0.95,
            "soc_initial": 0.5,
            "soc_min": 0.05,
            "soc_max": 0.95,
        },
        "Large": {
            "capacity_kwh": 30,
            "max_charge_kw": 10,
            "max_discharge_kw": 10,
            "efficiency": 0.95,
            "soc_initial": 0.5,
            "soc_min": 0.05,
            "soc_max": 0.95,
        },
    }
    INPUT_PORTS = {
        "electric": [("electricity_in", "Charge (kW)")],
    }
    OUTPUT_PORTS = {
        "electric": [("electricity_out", "Discharge (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.capacity_kwh = self.get_float_param("capacity_kwh", 10.0)
        self.max_charge_kw = self.get_float_param("max_charge_kw", 3.5)
        self.max_discharge_kw = self.get_float_param("max_discharge_kw", 3.5)
        self.efficiency = self.get_float_param("efficiency", 0.95)
        soc_initial = self.get_float_param("soc_initial", 0.5)
        self.soc_min = self.get_float_param("soc_min", 0.05)
        self.soc_max = self.get_float_param("soc_max", 0.95)
        self.soc: float = max(self.soc_min, min(self.soc_max, soc_initial))

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                charge_in_kw = min(self.sum_input("electricity_in"), self.max_charge_kw)
                charge_in_kw = max(charge_in_kw, 0.0)

                energy_stored = self.capacity_kwh * self.soc
                max_chargeable = (self.soc_max - self.soc) * self.capacity_kwh
                actual_charge = min(charge_in_kw, max_chargeable)
                energy_stored += actual_charge * self.efficiency

                max_dischargeable = (self.soc - self.soc_min) * self.capacity_kwh
                discharge_kw = min(self.max_discharge_kw, max_dischargeable)
                discharge_kw = max(discharge_kw, 0.0)
                energy_stored -= discharge_kw

                if self.capacity_kwh > 0:
                    self.soc = max(self.soc_min, min(self.soc_max, energy_stored / self.capacity_kwh))

                self.set_output("electricity_out", discharge_kw, timestamp=timestamp)
                self.set_output("soc", self.soc, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
