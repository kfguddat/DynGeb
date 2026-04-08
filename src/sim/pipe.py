from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from datetime import datetime

from src.sim.value import TimeSeries, Value

if TYPE_CHECKING:
    from src.sim.asset import Asset


class Port:
    """Represents a single connection point on an asset."""

    def __init__(
        self,
        asset: "Asset",
        name: str,
        medium: str,
        description: str,
        in_port: bool,
    ) -> None:
        self.asset = asset
        self.name = name
        self.medium = medium
        self.description = description
        self.in_port = in_port
        self.flow: TimeSeries = TimeSeries(
            data=Value(unit=medium, description=description)
        )

    def __repr__(self) -> str:
        direction = "in" if self.in_port else "out"
        return f"Port({self.asset.name}.{self.name} [{direction}] {self.medium})"


class Pipe:
    """
    Connects asset output ports to asset input ports.

    in_ports:  list[list[Port]] - source ports (asset outputs), each inner list
               is a priority group; sources in the same group are tried in order
               until demand is met before moving to the next group.
    out_ports: list[list[Port]] - destination ports (asset inputs), same
               priority-group structure.
    medium:    the energy/data medium flowing through this pipe.
    """

    def __init__(
        self,
        in_ports: list[list[Port]],
        out_ports: list[list[Port]],
        medium: str,
    ) -> None:
        self.in_ports = in_ports
        self.out_ports = out_ports
        self.medium = medium
        self._settled: set[datetime] = set()

    def reset(self, timestamp: datetime) -> None:
        """Clear per-timestep settlement state."""
        self._settled.discard(timestamp)

    def iter_out_ports(self):
        """Yield (group_index, Port) for every destination port."""
        for group_idx, group in enumerate(self.out_ports):
            for port in group:
                yield group_idx, port

    def calc(
        self,
        timestamp: datetime,
        out_port: Port,
        requested_value: Optional[Value] = None,
    ) -> Value:
        """
        Attempt to fulfil the demand expressed by *requested_value* at *out_port*
        by drawing supply from the source ports in priority order.

        Returns a Value containing the total amount actually provided.
        """
        if isinstance(requested_value, Value):
            requested_amount = max(float(requested_value.get() or 0.0), 0.0)
            unit = requested_value.unit
        else:
            requested_amount = max(float(requested_value or 0.0), 0.0)
            unit = ""

        remaining = requested_amount
        total_provided = 0.0

        for group in self.in_ports:
            for source_port in group:
                if remaining <= 0.0:
                    break
                try:
                    response = source_port.asset.calc(
                        source_port,
                        timestamp,
                        Value(value=remaining, unit=unit),
                    )
                except (TypeError, ValueError, AttributeError):
                    continue

                if isinstance(response, Value):
                    got = max(float(response.get() or 0.0), 0.0)
                else:
                    got = max(float(response or 0.0), 0.0)

                total_provided += got
                remaining = max(remaining - got, 0.0)

            if remaining <= 0.0:
                break

        return Value(
            value=total_provided,
            unit=unit,
            description=f"Pipe supplied {total_provided} {unit} to {out_port.name}",
        )

    def __repr__(self) -> str:
        return f"Pipe(medium={self.medium}, in={len(self.in_ports)} groups, out={len(self.out_ports)} groups)"
