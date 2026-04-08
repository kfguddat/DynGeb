from typing import Dict, Any, Optional
from datetime import datetime
import csv
from pathlib import Path
from src.sim.asset import Asset


class env(Asset):
    """Environment asset that provides external weather and price data.

    Reads a CSV file with columns for timestamp, temperature, irradiance,
    and optionally electricity price.  At each timestep the relevant row is
    looked up and broadcast to all connected data-port subscribers via the
    standard output mechanism.
    """

    ASSET_TYPE = "env"
    DISPLAY_NAME = "Environment"
    COLOR = "#a8dadc"
    PRESETS = {
        "Default": {
            "weather_file": "",
            "temperature_col": "temperature",
            "irradiance_col": "irradiance",
            "price_col": "price",
        }
    }
    INPUT_PORTS: Dict[str, Any] = {}
    OUTPUT_PORTS = {
        "data": [
            ("temperature_out", "Outdoor Temperature (C)"),
            ("irradiance_out", "Solar Irradiance (W/m2)"),
            ("price_out", "Electricity Price (EUR/kWh)"),
        ],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, params=params)
        self.weather_file: str = str(self.get_param("weather_file", ""))
        self.temperature_col: str = str(self.get_param("temperature_col", "temperature"))
        self.irradiance_col: str = str(self.get_param("irradiance_col", "irradiance"))
        self.price_col: str = str(self.get_param("price_col", "price"))
        self._data: Dict[datetime, Dict[str, float]] = {}
        self._loaded = False

    def _load_data(self) -> None:
        """Load weather/price CSV into an in-memory dict keyed by datetime."""
        if self._loaded:
            return
        self._loaded = True
        if not self.weather_file:
            return

        path = Path(self.weather_file)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            path = project_root / self.weather_file

        if not path.exists():
            print(f"[env] Weather file not found: {path}")
            return

        try:
            with open(path, newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ts_raw = row.get("timestamp") or row.get("Timestamp") or row.get("datetime")
                    if ts_raw is None:
                        continue
                    try:
                        ts = datetime.fromisoformat(str(ts_raw).strip())
                    except ValueError:
                        continue
                    entry: Dict[str, float] = {}
                    for col in (self.temperature_col, self.irradiance_col, self.price_col):
                        val = row.get(col)
                        if val is not None:
                            try:
                                entry[col] = float(val)
                            except (ValueError, TypeError):
                                pass
                    self._data[ts] = entry
        except OSError as exc:
            print(f"[env] Could not read weather file: {exc}")

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                self._load_data()
                row = self._data.get(timestamp, {})
                temp = row.get(self.temperature_col, 10.0)
                irr = row.get(self.irradiance_col, 0.0)
                price = row.get(self.price_col, 0.25)
                self.set_output("temperature_out", temp, timestamp=timestamp)
                self.set_output("irradiance_out", irr, timestamp=timestamp)
                self.set_output("price_out", price, timestamp=timestamp)

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
