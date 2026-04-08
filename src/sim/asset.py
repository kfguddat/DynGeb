from __future__ import annotations

from typing import Dict, Any, Optional, Iterable, Callable
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path
import importlib
import inspect
from src.sim.value import Value, TimeSeries

PortEntry = str | tuple[str, str]
PortConfigValue = int | list[PortEntry]


class Asset(ABC):
    """Base class for all energy system assets."""

    ASSET_TYPE = "asset"
    DISPLAY_NAME = "Asset"
    COLOR = "#cccccc"
    PRESETS: Dict[str, Dict[str, Any]] = {"Default": {}}
    INPUT_PORTS: Dict[str, PortConfigValue] = {}
    OUTPUT_PORTS: Dict[str, PortConfigValue] = {}
    
    def __init__(self, name: str, asset_type: Optional[str] = None, params: Dict[str, Any] = None):
        """
        Initialize an Asset.
        
        Args:
            name: Unique identifier for this asset instance
            asset_type: Type of asset (e.g., "pv", "battery", "building")
            params: Dictionary of parameters from config
        """
        self.name = name
        self.asset_type = asset_type or self.ASSET_TYPE

        raw_params = params or {}
        self.params = {
            (str(key).lower() if isinstance(key, str) else key): value
            for key, value in raw_params.items()
        }
        
        # Dictionaries to store runtime I/O values.
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.input_ports: Dict[str, Any] = {}
        self.output_ports: Dict[str, Any] = {}
        self._input_resolver: Optional[Callable[["Asset", str, Value, datetime], Value]] = None
        self._calc_in_progress: set[datetime] = set()
        self._active_timestamp: Optional[datetime] = None

        self._initialize_runtime_ports()
    
    def set_input(self, name: str, value: Any, timestamp: Optional[datetime] = None) -> None:
        """Set an input value for this hour."""
        self.inputs[name] = value
        ts = timestamp if timestamp is not None else self._active_timestamp
        if ts is None:
            return
        port = self.input_ports.get(name)
        if port is not None and getattr(port, "flow", None) is not None:
            port.flow.add(ts, value)
    
    def get_input(self, name: str) -> Any:
        """Get an input value."""
        return self.inputs.get(name)
    
    def set_output(self, name: str, value: Any, timestamp: Optional[datetime] = None) -> None:
        """Set an output value for this hour."""
        self.outputs[name] = value
        ts = timestamp if timestamp is not None else self._active_timestamp
        if ts is None:
            return
        port = self.output_ports.get(name)
        if port is not None and getattr(port, "flow", None) is not None:
            port.flow.add(ts, value)

    def get_output(self, name: str) -> Any:
        """Get an output value."""
        return self.outputs.get(name)

    def _initialize_runtime_ports(self) -> None:
        # Late import avoids circular import during module initialization.
        from src.sim.pipe import Port

        def build_ports(mapping: Dict[str, PortConfigValue], is_input: bool) -> Dict[str, Any]:
            runtime_ports: Dict[str, Any] = {}
            for medium, value in mapping.items():
                if isinstance(value, int):
                    if value <= 0:
                        continue
                    for idx in range(value):
                        port_name = f"{medium}_{'in' if is_input else 'out'}_{idx + 1}"
                        runtime_ports[port_name] = Port(
                            asset=self,
                            name=port_name,
                            medium=str(medium),
                            description=port_name,
                            in_port=is_input,
                        )
                    continue

                for idx, item in enumerate(value):
                    if isinstance(item, tuple):
                        raw_name, label = item
                        port_name = str(raw_name) if raw_name else f"{medium}_{'in' if is_input else 'out'}_{idx + 1}"
                        description = str(label)
                    else:
                        raw_name = str(item)
                        port_name = raw_name if raw_name else f"{medium}_{'in' if is_input else 'out'}_{idx + 1}"
                        description = self._humanize_port_label(port_name)

                    runtime_ports[port_name] = Port(
                        asset=self,
                        name=port_name,
                        medium=str(medium),
                        description=description,
                        in_port=is_input,
                    )
            return runtime_ports

        self.input_ports = build_ports(self.INPUT_PORTS, is_input=True)
        self.output_ports = build_ports(self.OUTPUT_PORTS, is_input=False)

    @staticmethod
    def _humanize_port_label(port_id: str) -> str:
        return port_id.replace("_", " ").title()

    @classmethod
    def _expand_ports(cls, direction: str, mapping: Dict[str, PortConfigValue]) -> list[Dict[str, str]]:
        ports: list[Dict[str, str]] = []
        for medium, value in mapping.items():
            if isinstance(value, int):
                if value <= 0:
                    continue
                for index in range(value):
                    port_id = f"{medium}_{direction}_{index + 1}"
                    description = cls._humanize_port_label(port_id)
                    ports.append({
                        "id": port_id,
                        "medium": medium,
                        "label": description,
                        "description": description,
                    })
                continue

            for index, item in enumerate(value):
                if isinstance(item, tuple):
                    port_id, label = item
                else:
                    port_id = item
                    label = cls._humanize_port_label(port_id)

                if not port_id:
                    port_id = f"{medium}_{direction}_{index + 1}"
                description = str(label)
                ports.append({
                    "id": str(port_id),
                    "medium": medium,
                    "label": description,
                    "description": description,
                })
        return ports

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        return {
            "displayName": cls.DISPLAY_NAME,
            "color": cls.COLOR,
            "presets": cls.PRESETS,
            "ports": {
                "in": cls._expand_ports("in", cls.INPUT_PORTS),
                "out": cls._expand_ports("out", cls.OUTPUT_PORTS),
            },
        }

    def get_param(self, key: str, default: Any = None) -> Any:
        key_l = str(key).lower()
        if key_l in self.params:
            return self.params[key_l]
        return default

    def get_float_param(self, key: str, default: float = 0.0) -> float:
        return float(self.get_param(key, default))

    @staticmethod
    def coerce_numeric(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (list, tuple)):
            return float(sum(v for v in value if v is not None))
        if isinstance(value, dict):
            return float(sum(v for v in value.values() if v is not None))
        return float(value)

    def sum_input(self, name: str) -> float:
        return self.coerce_numeric(self.get_input(name))

    @staticmethod
    def _to_value(value: Any, unit: str = "", description: str = "") -> Value:
        if isinstance(value, Value):
            return value
        return Value(value=value, unit=unit, description=description)

    @staticmethod
    def _bool_from_flag(flag: Any) -> bool:
        if hasattr(flag, "value"):
            return bool(getattr(flag, "value"))
        return bool(flag)

    @staticmethod
    def _port_name_from_port(port: Any) -> str:
        if hasattr(port, "name") and getattr(port, "name"):
            return str(getattr(port, "name"))
        raise ValueError("Port object must define a name")

    def _flatten_port_map(self, mapping: Dict[str, PortConfigValue], direction: str) -> list[str]:
        names: list[str] = []
        for medium, value in mapping.items():
            if isinstance(value, int):
                if value <= 0:
                    continue
                names.extend([f"{medium}_{direction}_{idx + 1}" for idx in range(value)])
                continue
            for idx, item in enumerate(value):
                if isinstance(item, tuple):
                    port_id = str(item[0])
                else:
                    port_id = str(item)
                if not port_id:
                    port_id = f"{medium}_{direction}_{idx + 1}"
                names.append(port_id)
        return names

    def input_port_names(self) -> list[str]:
        return self._flatten_port_map(self.INPUT_PORTS, "in")

    def output_port_names(self) -> list[str]:
        return self._flatten_port_map(self.OUTPUT_PORTS, "out")

    def register_input_resolver(
        self,
        resolver: Callable[["Asset", str, Value, datetime], Value],
    ) -> None:
        self._input_resolver = resolver

    def _request_missing_inputs(self, timestamp: datetime) -> None:
        if self._input_resolver is None:
            return

        for port_name in self.input_port_names():
            if port_name in self.inputs:
                continue

            port = self.input_ports.get(port_name)
            if port is not None and str(getattr(port, "medium", "")).lower() == "data":
                # Data ports are optional pull-values; leave unset unless explicitly provided.
                continue

            requested = Value(value=0.0, description=f"Requested supply for {self.name}.{port_name}")
            received = self._input_resolver(self, port_name, requested, timestamp)
            received_value = self.coerce_numeric(received.get() if isinstance(received, Value) else received)
            self.inputs[port_name] = received_value

    def _run_timestamp_calc(
        self,
        timestamp: datetime,
        compute: Callable[[], None],
    ) -> None:
        if timestamp in self._calc_in_progress:
            return
        self._calc_in_progress.add(timestamp)
        previous_timestamp = self._active_timestamp
        self._active_timestamp = timestamp
        try:
            self._request_missing_inputs(timestamp)
            compute()
        finally:
            self._active_timestamp = previous_timestamp
            self._calc_in_progress.discard(timestamp)

    def _calc_for_port(
        self,
        port: Any,
        timestamp: datetime,
        value: Optional[Value] = None,
    ) -> Value:
        port_name = self._port_name_from_port(port)
        is_input = self._bool_from_flag(getattr(port, "in_port", False))
        requested = self._to_value(value if value is not None else Value(value=0.0))

        if is_input:
            current = self.coerce_numeric(self.get_input(port_name))
            incoming = self.coerce_numeric(requested.get())
            self.set_input(port_name, current + incoming, timestamp=timestamp)
            return Value(value=incoming, unit=requested.unit, description=f"Accepted input for {self.name}.{port_name}")

        self.calc(timestamp)
        output_value = self.coerce_numeric(self.get_output(port_name))
        out_port = self.output_ports.get(port_name)
        if out_port is not None and getattr(out_port, "flow", None) is not None and out_port.flow.get(timestamp) is None:
            out_port.flow.add(timestamp, output_value)
        return Value(value=output_value, unit=requested.unit, description=f"Provided output for {self.name}.{port_name}")

    @abstractmethod
    def calc(self, *args: Any, **kwargs: Any) -> Any:
        """Calculate timestamp outputs or resolve a port-level calc request."""
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"Asset({self.name}, type={self.asset_type})"


def discover_asset_classes(module_names: Optional[Iterable[str]] = None) -> Dict[str, type[Asset]]:
    assets_dir = Path(__file__).resolve().parent / "assets"
    candidates = list(module_names) if module_names else [
        path.stem for path in assets_dir.glob("*.py") if path.stem != "__init__"
    ]

    classes: Dict[str, type[Asset]] = {}
    for module_name in candidates:
        try:
            module = importlib.import_module(f"src.sim.assets.{module_name}")
        except Exception:
            continue

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls is Asset or not issubclass(cls, Asset):
                continue
            asset_type = getattr(cls, "ASSET_TYPE", None)
            if not asset_type:
                continue
            classes[asset_type] = cls

    return classes


def build_asset_catalog(module_names: Optional[Iterable[str]] = None) -> Dict[str, Dict[str, Any]]:
    classes = discover_asset_classes(module_names)
    return {asset_type: cls.ui_config() for asset_type, cls in sorted(classes.items())}
