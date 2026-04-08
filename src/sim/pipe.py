from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from src.sim.value import Value, TimeSeries

if TYPE_CHECKING:
    from src.sim.asset import Asset


class Port:
    """Represents a single connection point on an asset."""

    def __init__(
        self,
        asset: "Asset",
        name: str,
        medium: str,
        description: str = "",
        in_port: bool = True,
    ) -> None:
        self.asset = asset
        self.name = name
        self.medium = medium
        self.description = description
        self.in_port = in_port
        self.flow: TimeSeries = TimeSeries(
            Value(unit="", description=description or name)
        )

    def __repr__(self) -> str:
        direction = "in" if self.in_port else "out"
        return f"Port({self.asset.name}.{self.name}, {direction}, {self.medium})"


class Pipe:
    """Connects asset output ports (supply) to asset input ports (demand).

    ``in_ports`` are the **supply** side – outputs from source assets feeding
    into the pipe.  ``out_ports`` are the **demand** side – inputs on sink
    assets consuming from the pipe.  Both are ordered lists of priority groups
    so that higher-priority sources/sinks are tried first.
    """

    def __init__(
        self,
        in_ports: list[list[Port]],
        out_ports: list[list[Port]],
        medium: str = "electric",
    ) -> None:
        self.in_ports = in_ports
        self.out_ports = out_ports
        self.medium = medium
        self._step_provided: dict[Any, float] = {}

    def reset(self, timestamp: Any) -> None:
        """Clear per-step cached flow values."""
        self._step_provided.pop(timestamp, None)

    def iter_out_ports(self):
        """Yield ``(priority_index, port)`` for every demand-side port."""
        for priority, group in enumerate(self.out_ports):
            for port in group:
                yield priority, port

    def calc(
        self,
        timestamp: Any,
        out_port: Port,
        requested: Value,
    ) -> Value:
        """Resolve how much supply can be delivered to *out_port*.

        Iterates through supply-side (``in_ports``) priority groups, asks each
        source asset for its available output, and accumulates the total up to
        the requested amount.

        Args:
            timestamp: Current simulation timestep.
            out_port: The demand-side port requesting supply.
            requested: A :class:`Value` carrying the requested amount.

        Returns:
            A :class:`Value` with the total amount that could be provided.
        """
        req_amount = float(requested.get() or 0.0)
        if req_amount <= 0.0:
            return Value(value=0.0, unit=requested.unit)

        remaining = req_amount
        provided_total = 0.0

        for group in self.in_ports:
            if remaining <= 0.0:
                break
            for source_port in group:
                if remaining <= 0.0:
                    break
                ask = Value(
                    value=remaining,
                    unit=requested.unit,
                    description=f"Supply request for {out_port.asset.name}.{out_port.name}",
                )
                response = source_port.asset.calc(source_port, timestamp, ask)
                got: float
                if isinstance(response, Value):
                    raw = response.get()
                    got = float(raw) if raw is not None else 0.0
                elif response is not None:
                    got = float(response)
                else:
                    got = 0.0
                got = max(got, 0.0)
                provided_total += got
                remaining = max(remaining - got, 0.0)

        return Value(
            value=provided_total,
            unit=requested.unit,
            description=f"Provided to {out_port.asset.name}.{out_port.name}",
        )

    def __repr__(self) -> str:
        n_in = sum(len(g) for g in self.in_ports)
        n_out = sum(len(g) for g in self.out_ports)
        return f"Pipe(medium={self.medium}, in={n_in}, out={n_out})"
