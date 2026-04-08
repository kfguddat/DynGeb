from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import csv
from src.sim.asset import Asset


class env(Asset):
    """Environment asset that reads weather data (TRY format) and exposes
    irradiance and outside temperature as output ports for other assets."""

    ASSET_TYPE = "env"
    DISPLAY_NAME = "Environment"
    COLOR = "#b7e4c7"
    PRESETS = {
        "Default": {
            "weather_file": "",
            "t_outside": 10.0,
            "irradiance": 200.0,
        },
    }
    INPUT_PORTS: Dict[str, Any] = {}
    OUTPUT_PORTS = {
        "data": [
            ("irradiance_out", "Irradiance (W/m²)"),
            ("temperature_out", "Outside Temperature (°C)"),
        ],
    }

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, params=params)
        self.weather_file: str = str(self.get_param("weather_file", ""))
        # Static fallback values used when no weather file is loaded
        self.t_outside_default: float = self.get_float_param("t_outside", 10.0)
        self.irradiance_default: float = self.get_float_param("irradiance", 200.0)
        # Loaded weather series: {datetime: {"irradiance": float, "temperature": float}}
        self._weather: Dict[datetime, Dict[str, float]] = {}
        if self.weather_file:
            self._load_weather(self.weather_file)

    # ------------------------------------------------------------------
    # Weather loading helpers
    # ------------------------------------------------------------------

    def _load_weather(self, path: str) -> None:
        """Load a weather file.

        Supports simple CSV files with columns:
            timestamp, irradiance, temperature
        or DWD TRY .dat files (space-separated, columns described in header).
        """
        file_path = Path(path)
        if not file_path.exists():
            return
        suffix = file_path.suffix.lower()
        try:
            if suffix in {".csv", ".txt"}:
                self._load_csv_weather(file_path)
            elif suffix == ".dat":
                self._load_try_weather(file_path)
        except Exception:
            pass

    def _load_csv_weather(self, file_path: Path) -> None:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(str(row.get("timestamp", "")))
                    irr = float(row.get("irradiance", 0) or 0)
                    temp = float(row.get("temperature", 0) or 0)
                    self._weather[ts] = {"irradiance": irr, "temperature": temp}
                except (ValueError, KeyError):
                    continue

    def _load_try_weather(self, file_path: Path) -> None:
        """Parse a DWD TRY .dat file (whitespace-separated hourly data).

        Typical TRY columns (1-indexed):
            1: MM  (month), 2: DD (day), 3: HH (hour 1-24)
            13: N  (global horizontal irradiance, W/m²)
            15: t  (air temperature, °C)
        Column indices may vary; we fall back to zero-based positional parsing.
        """
        import re
        with open(file_path, encoding="latin-1") as f:
            lines = f.readlines()

        header_line_idx: Optional[int] = None
        col_irr: Optional[int] = None
        col_temp: Optional[int] = None
        col_mm: Optional[int] = None
        col_dd: Optional[int] = None
        col_hh: Optional[int] = None

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"^\s*MM\s+DD\s+HH", stripped, re.IGNORECASE):
                header_line_idx = idx
                headers = stripped.split()
                for i, h in enumerate(headers):
                    hl = h.strip().lower()
                    if hl == "mm":
                        col_mm = i
                    elif hl == "dd":
                        col_dd = i
                    elif hl in {"hh", "h"}:
                        col_hh = i
                    elif hl in {"b", "g", "g_h", "glo", "glob", "n"}:
                        if col_irr is None:
                            col_irr = i
                    elif hl in {"t", "ta", "temp", "t_l"}:
                        if col_temp is None:
                            col_temp = i
                break

        # Defaults based on common TRY column positions (0-based after MM DD HH):
        # MM=0, DD=1, HH=2, ..., irradiance around col 12-13, temp around 14
        if col_mm is None:
            col_mm = 0
        if col_dd is None:
            col_dd = 1
        if col_hh is None:
            col_hh = 2
        if col_irr is None:
            col_irr = 13
        if col_temp is None:
            col_temp = 14

        year = 2015
        start_line = (header_line_idx + 1) if header_line_idx is not None else 0

        for line in lines[start_line:]:
            parts = line.split()
            if not parts:
                continue
            try:
                mm = int(parts[col_mm])
                dd = int(parts[col_dd])
                hh = int(parts[col_hh])
                if hh == 24:
                    hh = 0
                    dd += 1
                irr = float(parts[col_irr])
                temp = float(parts[col_temp])
                ts = datetime(year, mm, dd, hh, 0, 0)
                self._weather[ts] = {"irradiance": irr, "temperature": temp}
            except (IndexError, ValueError):
                continue

    # ------------------------------------------------------------------
    # Asset interface
    # ------------------------------------------------------------------

    def _get_weather(self, timestamp: datetime) -> Dict[str, float]:
        if timestamp in self._weather:
            return self._weather[timestamp]
        return {
            "irradiance": self.irradiance_default,
            "temperature": self.t_outside_default,
        }

    def calc(self, *args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], datetime):
            timestamp = args[0]

            def compute() -> None:
                w = self._get_weather(timestamp)
                self.set_output("irradiance_out", w["irradiance"])
                self.set_output("temperature_out", w["temperature"])

            self._run_timestamp_calc(timestamp, compute)
            return None

        if len(args) >= 2:
            port = args[0]
            timestamp = args[1]
            value = args[2] if len(args) >= 3 else None
            return self._calc_for_port(port, timestamp, value=value)

        raise TypeError("calc() expects either (timestamp) or (port, timestamp, value)")
