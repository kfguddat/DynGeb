from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from datetime import datetime

from src.sim.value import Value, TimeSeries

if TYPE_CHECKING:
    from src.sim.asset import Asset


class Port:
    """Represents a connection port on an asset."""

    def __init__(
        self,
        asset: 'Asset',
        name: str,
        medium: str,
        description: str = "",
        in_port: bool = True,
    ):
        self.asset = asset
        self.name = name
        self.medium = medium
        self.description = description
        self.in_port = in_port
        self.flow: TimeSeries = TimeSeries(
            Value(unit=medium, description=description)
        )

    def __repr__(self) -> str:
        direction = "in" if self.in_port else "out"
        return f"Port({self.asset.name}.{self.name}, {direction}, {self.medium})"


class Pipe:
    """
    Connects asset output ports (sources) to asset input ports (sinks).

    ``in_ports`` are priority-ordered groups of asset output ports that supply
    energy/data into this pipe.  ``out_ports`` are priority-ordered groups of
    asset input ports that consume from this pipe.
    """

    def __init__(
        self,
        in_ports: list[list[Port]],
        out_ports: list[list[Port]],
        medium: str = "electric",
    ):
        self.in_ports = in_ports
        self.out_ports = out_ports
        self.medium = medium

        # Per-step tracking to prevent over-provisioning from the same source.
        self._supply_capacity: dict[int, float] = {}
        self._supply_provided: dict[int, float] = {}
        self._step_timestamp: Optional[datetime] = None

    def reset(self, timestamp: datetime) -> None:
        """Reset per-step supply tracking."""
        self._supply_capacity.clear()
        self._supply_provided.clear()
        self._step_timestamp = timestamp

    def iter_out_ports(self):
        """Yield ``(priority_index, port)`` for every sink port."""
        for priority, group in enumerate(self.out_ports):
            for port in group:
                yield priority, port

    def _query_source(
        self,
        source_port: Port,
        timestamp: datetime,
        demand: Value,
    ) -> float:
        """
        Trigger calculation on a source port's asset and return the available
        output capacity for this step.  Results are cached per step so that
        repeated calls to the same source do not re-trigger expensive
        calculations.
        """
        port_id = id(source_port)
        if port_id in self._supply_capacity:
            return self._supply_capacity[port_id]

        response = source_port.asset.calc(source_port, timestamp, demand)
        if isinstance(response, Value):
            available = max(float(response.get() or 0.0), 0.0)
        else:
            available = max(float(response or 0.0), 0.0)

        self._supply_capacity[port_id] = available
        return available

    def calc(
        self,
        timestamp: datetime,
        requesting_out_port: Port,
        demand: Value,
    ) -> Value:
        """
        Fulfil a supply request from a consumer port.

        Iterates through source priority groups, claiming up to the remaining
        demand from each source while respecting per-source capacity limits
        shared across all consumers in this step.

        Args:
            timestamp: Current simulation time.
            requesting_out_port: The consumer (asset input) port that is
                requesting supply.
            demand: How much supply is needed.

        Returns:
            A Value with the total amount provided.
        """
        requested = max(float(demand.get() or 0.0), 0.0)
        if requested <= 0.0:
            return Value(value=0.0, unit=self.medium)

        remaining = requested
        total_provided = 0.0

        for group in self.in_ports:
            for source_port in group:
                if remaining <= 0.0:
                    break

                port_id = id(source_port)
                capacity = self._query_source(source_port, timestamp, demand)
                already_claimed = self._supply_provided.get(port_id, 0.0)
                available = max(capacity - already_claimed, 0.0)
                provided = min(available, remaining)

                if provided > 0.0:
                    self._supply_provided[port_id] = already_claimed + provided
                    remaining -= provided
                    total_provided += provided

            if remaining <= 0.0:
                break

        return Value(
            value=total_provided,
            unit=self.medium,
            description=f"Supply for {requesting_out_port.asset.name}.{requesting_out_port.name}",
        )
