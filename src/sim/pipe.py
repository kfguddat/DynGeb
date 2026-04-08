from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from src.sim.value import Value, TimeSeries

if TYPE_CHECKING:
	from src.sim.asset import Asset


class Port:
	"""Represents a connection point on an asset."""

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
		self.flow = TimeSeries(data=Value(description=description))

	def __repr__(self) -> str:
		direction = "in" if self.in_port else "out"
		return f"Port({self.asset.name}.{self.name}, {self.medium}, {direction})"


class Pipe:
	"""Connects supply-side output ports to demand-side input ports."""

	def __init__(
		self,
		in_ports: list[list[Port]],
		out_ports: list[list[Port]],
		medium: str = "electric",
	) -> None:
		# in_ports = supply side (asset OUTPUT ports), priority groups
		# out_ports = demand side (asset INPUT ports), priority groups
		self.in_ports = in_ports
		self.out_ports = out_ports
		self.medium = medium
		# Tracks how much each supply port has already delivered this timestep
		self._supply_used: dict[int, float] = {}

	def reset(self, timestamp: Any) -> None:
		"""Reset per-step supply tracking."""
		self._supply_used = {}

	def iter_out_ports(self):
		"""Yield (priority_idx, port) for all demand-side ports."""
		for priority_idx, group in enumerate(self.out_ports):
			for port in group:
				yield priority_idx, port

	def calc(self, timestamp: Any, out_port: Port, demand: Value) -> Value:
		"""
		Attempt to fulfil demand at out_port from in_ports (supply side).

		Args:
			timestamp: current simulation timestamp
			out_port: the demand-side port requesting supply
			demand: how much is requested

		Returns:
			Value with the amount actually provided
		"""
		unit = demand.unit if isinstance(demand, Value) else ""
		raw = demand.get() if isinstance(demand, Value) else demand
		try:
			remaining = float(raw) if raw is not None else 0.0
		except (TypeError, ValueError):
			remaining = 0.0

		if remaining <= 0.0:
			return Value(value=0.0, unit=unit, description="No demand")

		provided_total = 0.0

		for supply_group in self.in_ports:
			for in_port in supply_group:
				if remaining <= 0.0:
					break

				already_used = self._supply_used.get(id(in_port), 0.0)

				# Ask the supply asset how much it can provide
				try:
					response = in_port.asset._calc_for_port(
						in_port,
						timestamp,
						Value(value=remaining, unit=unit, description=f"Supply request"),
					)
					available = float(response.get()) if isinstance(response, Value) else float(response)
				except Exception:
					available = 0.0

				# Only credit new supply beyond what was already allocated
				new_supply = max(available - already_used, 0.0)
				actually_provided = min(new_supply, remaining)

				if actually_provided > 0.0:
					self._supply_used[id(in_port)] = already_used + actually_provided
					provided_total += actually_provided
					remaining -= actually_provided

			if remaining <= 0.0:
				break

		return Value(value=provided_total, unit=unit, description=f"Provided via pipe")
