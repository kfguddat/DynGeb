from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bdg(Asset):
    """Simple RC-model building with thermal demand calculation.

    The thermal balance uses a first-order RC approximation:
        Q_loss = (T_indoor - T_outdoor) / R_envelope  [kW]
        T_indoor(t+1) = T_indoor(t) + dt/C_mass * (Q_supplied - Q_loss)
    """

    ASSET_TYPE = "bdg"
    DISPLAY_NAME = "Building"
    COLOR = "#f4a261"
    PRESETS = {
        "Default": {
            "r_envelope": 5.0,
            "c_mass": 50.0,
            "t_setpoint": 21.0,
            "t_initial": 21.0,
            "floor_area_m2": 100.0,
            "base_load_kw": 1.5,
        },
        "Well-Insulated": {
            "r_envelope": 10.0,
            "c_mass": 80.0,
            "t_setpoint": 21.0,
            "t_initial": 21.0,
            "floor_area_m2": 120.0,
            "base_load_kw": 1.0,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply (kW)")],
        "data": [("temperature_in", "Outdoor Temperature (C)")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_demand_out", "Heat Demand (kW)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.r_envelope = self.get_float_param("r_envelope", 5.0)
        self.c_mass = self.get_float_param("c_mass", 50.0)
        self.t_setpoint = self.get_float_param("t_setpoint", 21.0)
        self.t_initial = self.get_float_param("t_initial", 21.0)
        self.floor_area_m2 = self.get_float_param("floor_area_m2", 100.0)
        self.base_load_kw = self.get_float_param("base_load_kw", 1.5)
        self.t_indoor: float = self.t_initial

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                t_outdoor = self.get_input("temperature_in")
                if t_outdoor is None:
                    t_outdoor = 10.0
                else:
                    try:
                        t_outdoor = float(t_outdoor)
                    except (TypeError, ValueError):
                        t_outdoor = 10.0

                # Q_loss proportional to envelope area: U-value * area * delta_T / 1000
                # r_envelope is interpreted as (K/kW) thermal resistance per m².
                # Effective resistance = r_envelope / floor_area_m2 scales to building size.
                effective_r = max(self.r_envelope / max(self.floor_area_m2, 1.0), 0.001)
                q_loss = max((self.t_indoor - t_outdoor) / effective_r, 0.0)
                heat_demand = q_loss + self.base_load_kw
                heat_supplied = self.sum_input("heat_in")

                dt_hours = 1.0
                delta_t = (dt_hours / max(self.c_mass, 0.001)) * (heat_supplied - q_loss)
                self.t_indoor = self.t_indoor + delta_t

                self.set_output("heat_demand_out", heat_demand, timestamp=timestamp)
                self.set_output("t_indoor", self.t_indoor, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
