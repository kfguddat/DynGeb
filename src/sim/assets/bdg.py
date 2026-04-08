from typing import Dict, Any, Optional
from datetime import datetime
from src.sim.asset import Asset


class bdg(Asset):
    """Building thermal model using a simplified RC (resistance-capacitance) approach.

    The hourly heat balance is:
        Q_loss = (T_inside - T_outside) / R_envelope   [kW]
        T_inside(t+1) = T_inside(t) + (dt / C_mass) * (Q_heat_in - Q_loss)

    Where:
        R_envelope  thermal resistance of the building envelope (K/kW)
        C_mass      thermal mass / capacitance (kWh/K)
        T_setpoint  desired indoor temperature (°C)
    """

    ASSET_TYPE = "bdg"
    DISPLAY_NAME = "Building"
    COLOR = "#f4a261"
    PRESETS = {
        "Default": {
            "r_envelope": 5.0,
            "c_mass": 20.0,
            "t_setpoint": 20.0,
            "t_initial": 20.0,
            "floor_area_m2": 100.0,
        },
        "Passive House": {
            "r_envelope": 15.0,
            "c_mass": 40.0,
            "t_setpoint": 21.0,
            "t_initial": 21.0,
            "floor_area_m2": 120.0,
        },
    }
    INPUT_PORTS = {
        "thermal": [("heat_in", "Heat Supply")],
        "data": [("temperature_in", "Outside Temperature")],
    }
    OUTPUT_PORTS = {
        "thermal": [("heat_demand_out", "Heat Demand (kW)")],
        "data": [("t_inside_out", "Indoor Temperature (°C)")],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.r_envelope: float = self.get_float_param("r_envelope", 5.0)
        self.c_mass: float = self.get_float_param("c_mass", 20.0)
        self.t_setpoint: float = self.get_float_param("t_setpoint", 20.0)
        self.t_inside: float = self.get_float_param("t_initial", 20.0)

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                t_outside_raw = self.inputs.get("temperature_in")
                t_outside = float(t_outside_raw) if t_outside_raw is not None else 10.0

                # Heat loss through envelope
                q_loss_kw = (self.t_inside - t_outside) / max(self.r_envelope, 1e-6)
                # Desired heat to maintain setpoint (demand)
                q_demand_kw = max(q_loss_kw, 0.0)

                # Actual heat supplied
                q_supplied_kw = self.sum_input("heat_in")

                # Update indoor temperature (1-hour timestep)
                delta_t = (q_supplied_kw - q_loss_kw) / max(self.c_mass, 1e-6)
                self.t_inside = self.t_inside + delta_t

                self.set_output("heat_demand_out", q_demand_kw)
                self.set_output("t_inside_out", self.t_inside)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
