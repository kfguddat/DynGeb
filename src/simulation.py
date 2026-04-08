from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import importlib
from src.sim.asset import Asset
from src.sim.pipe import Pipe, Port
from src.sim.value import Value


class Simulation:
    """Orchestrates the entire energy system simulation."""
    
    def __init__(self, config_path: str):
        """
        Initialize Simulation by loading config from YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.config_path = config_path
        
        # Simulation parameters
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.timestep_hours: int = 1
        
        # Core data structures
        self.assets: Dict[str, Asset] = {}
        self.pipes: list[Pipe] = []
        
        # Results storage
        self.results: Dict[str, Dict[datetime, Any]] = {}
        
        # Parse simulation config
        self._parse_simulation_config()

    @staticmethod
    def _numeric(value: Any) -> float:
        if isinstance(value, Value):
            raw = value.get()
            return 0.0 if raw is None else float(raw)
        if value is None:
            return 0.0
        return float(value)

    @staticmethod
    def _normalize_medium(medium: str) -> str:
        normalized = (medium or "").strip().lower()
        if normalized in {"electric", "thermal", "monetary", "data"}:
            return normalized
        return "electric"
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load and parse YAML configuration file.
        
        Args:
            config_path: Path to YAML file
            
        Returns:
            Dictionary containing parsed configuration
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _parse_simulation_config(self) -> None:
        """
        Parse simulation-level settings from config.
        Sets start_time, end_time, timestep_hours.
        """
        sim_config = self.config.get('simulation', {})
        
        # Parse dates
        start_str = sim_config.get('start')
        end_str = sim_config.get('end')
        
        self.start_time = datetime.fromisoformat(start_str) if start_str else None
        self.end_time = datetime.fromisoformat(end_str) if end_str else None
        
        # Parse timestep
        self.timestep_hours = sim_config.get('timestep_hours', 1)
    
    def _build_assets(self) -> None:
        """
        Create asset instances from config.
        Instantiates each asset from assets section and stores in self.assets dict.
        """
        assets_config = self.config.get('assets', {})
        if not isinstance(assets_config, list):
            print("Warning: 'assets' must be a list of objects with id and asset_type")
            return

        for item in assets_config:
            if not isinstance(item, dict):
                continue
            asset_id = str(item.get('id') or '')
            asset_type = str(item.get('asset_type') or '')
            if not asset_id or not asset_type:
                continue

            params = {
                k: v
                for k, v in item.items()
                if k not in ['id', 'asset_type', 'name', 'preset', 'color', 'pos', 'x', 'y']
            }
            module_name = self._get_module_name(asset_type)
            class_name = module_name

            try:
                module = importlib.import_module(f'src.sim.assets.{module_name}')
                asset_class = getattr(module, class_name)
                asset = asset_class(name=asset_id, params=params)
                asset.register_input_resolver(self._resolve_asset_input)
                self.assets[asset_id] = asset
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load asset {asset_id} ({class_name}): {e}")
    
    def _get_module_name(self, asset_type: str) -> str:
        """Asset module names are identical to asset_type names."""
        return asset_type
    
    def _build_pipes(self) -> None:
        """
        Create pipe instances from config.
        """
        pipes_config = self.config.get('pipes', [])

        self.pipes = []
        for pipe_data in pipes_config:
            in_refs = self._to_priority_groups(pipe_data.get('in'))
            out_refs = self._to_priority_groups(pipe_data.get('out'))

            if not in_refs or not out_refs:
                continue

            medium = self._normalize_medium(str(pipe_data.get('medium') or self._infer_medium(str(in_refs[0][0]))))
            in_ports = self._build_port_groups(in_refs, medium=medium, in_port=False)
            out_ports = self._build_port_groups(out_refs, medium=medium, in_port=True)

            if not in_ports or not out_ports:
                continue

            pipe = Pipe(in_ports=in_ports, out_ports=out_ports, medium=medium)
            self.pipes.append(pipe)

    @staticmethod
    def _to_priority_groups(raw: Any) -> list[list[str]]:
        if raw is None:
            return []
        if isinstance(raw, str):
            return [[raw]]
        if not isinstance(raw, list):
            return []
        if raw and all(isinstance(item, str) for item in raw):
            return [[str(item) for item in raw]]

        groups: list[list[str]] = []
        for item in raw:
            if isinstance(item, str):
                groups.append([item])
            elif isinstance(item, list):
                group = [str(ref) for ref in item if isinstance(ref, str)]
                if group:
                    groups.append(group)
        return groups

    def _build_port_groups(self, groups: list[list[str]], medium: str, in_port: bool) -> list[list[Port]]:
        parsed: list[list[Port]] = []
        for group in groups:
            parsed_group: list[Port] = []
            for ref in group:
                if "." not in ref:
                    continue
                asset_id, port_name = ref.split(".", 1)
                asset = self.assets.get(asset_id)
                if asset is None:
                    continue

                runtime_port = None
                if in_port:
                    runtime_port = getattr(asset, "input_ports", {}).get(port_name)
                else:
                    runtime_port = getattr(asset, "output_ports", {}).get(port_name)

                if runtime_port is None:
                    runtime_port = Port(
                        asset=asset,
                        name=port_name,
                        medium=medium,
                        description=ref,
                        in_port=in_port,
                    )
                    if in_port:
                        asset.input_ports[port_name] = runtime_port
                    else:
                        asset.output_ports[port_name] = runtime_port

                parsed_group.append(runtime_port)
            if parsed_group:
                parsed.append(parsed_group)
        return parsed
    
    def _infer_medium(self, port_str: str) -> str:
        """Infer medium type from port name."""
        port_lower = port_str.lower()
        if 'data' in port_lower or 'temperature' in port_lower or 'temp' in port_lower or 'irradiance' in port_lower:
            return 'data'
        if 'electricity' in port_lower or 'electric' in port_lower or 'power' in port_lower:
            return 'electric'
        if 'heat' in port_lower or 'thermal' in port_lower:
            return 'thermal'
        if 'money' in port_lower or 'price' in port_lower or 'revenue' in port_lower or 'cost' in port_lower or 'eur' in port_lower:
            return 'monetary'
        return 'electric'
    
    def _get_medium_unit(self, medium: str) -> str:
        """Get default unit for medium."""
        units = {
            'electric': 'kW',
            'thermal': 'kW',
            'monetary': 'EUR',
            'data': '',
        }
        return units.get(self._normalize_medium(medium), '')
    
    def _initialize_state(self) -> None:
        """
        Runtime port flows are initialized directly by each asset.
        """
        return
    
    def run(self) -> None:
        """
        Execute the complete simulation.
        Main orchestration function that runs the hourly loop.
        
        Flow:
            1. Load YAML config (already done in __init__)
            2. Build assets and pipes
              3. Initialize runtime port flows
            4. For each hour:
                    - Evaluate data-source assets
               - Compute asset production/consumption
                    - Propagate calc calls through pipes
               - Store results
            5. Export results
        """
        self._build_assets()
        self._build_pipes()
        self._initialize_state()
        
        # Run hourly simulation loop
        if self.start_time is None or self.end_time is None:
            print("Error: start_time and end_time not set")
            return
        
        current_time = self.start_time
        while current_time <= self.end_time:
            self._step(current_time)
            current_time += timedelta(hours=self.timestep_hours)
    
    def _step(self, timestamp: datetime) -> None:
        """
        Execute one simulation timestep (one hour).
        
        Args:
            timestamp: Current simulation time
            
        Flow:
            1. Evaluate data-source assets
            2. Calculate outputs for all assets based on inputs
            3. Propagate flows through pipes
            4. Store results
        """
        # Reset hourly inputs and per-step pipe caches.
        for asset in self.assets.values():
            asset.inputs = {}
        for pipe in self.pipes:
            pipe.reset(timestamp)

        # Step 1: Evaluate optional data-source asset.
        if 'env' in self.assets:
            env_asset = self.assets['env']
            env_asset.calc(timestamp)

        # Step 2: Trigger recursive calc propagation for all assets.
        for asset_id, asset in self.assets.items():
            if asset_id == 'env':
                continue
            asset.calc(timestamp)

        # A second pass settles assets whose inputs were fulfilled later in the first pass.
        for asset_id, asset in self.assets.items():
            if asset_id == 'env':
                continue
            asset.calc(timestamp)

        # Step 3: Store results.
        self._store_results(timestamp)

    def _estimate_requested_input(self, asset: Asset, port_name: str) -> float:
        demand_key = ""
        if port_name.endswith("_in"):
            demand_key = f"{port_name[:-3]}_demand"
        elif port_name.endswith("_input"):
            demand_key = f"{port_name[:-6]}_demand"
        else:
            demand_key = f"{port_name}_demand"

        if demand_key in asset.outputs and asset.outputs[demand_key] is not None:
            return max(self._numeric(asset.outputs[demand_key]), 0.0)

        if hasattr(asset, "load_kw"):
            return max(float(getattr(asset, "load_kw")), 0.0)

        existing = max(self._numeric(asset.get_input(port_name)), 0.0)
        if existing > 0.0:
            return existing

        # If no explicit demand exists, treat the sink as willing to accept available supply.
        return 1e18

    def _resolve_asset_input(
        self,
        asset: Asset,
        port_name: str,
        requested: Value,
        timestamp: datetime,
    ) -> Value:
        requested_amount = max(self._numeric(requested), 0.0)
        if requested_amount <= 0.0:
            requested_amount = self._estimate_requested_input(asset, port_name)

        if requested_amount <= 0.0:
            return Value(value=0.0, unit=requested.unit, description=f"No demand for {asset.name}.{port_name}")

        unit = requested.unit or self._get_medium_unit(self._infer_medium(port_name))
        remaining = requested_amount
        provided_total = 0.0

        # Priorities are enforced inside each pipe by iterating out ports in order.
        for pipe in self.pipes:
            for _, out_port in pipe.iter_out_ports():
                if out_port.asset is not asset or out_port.name != port_name:
                    continue

                response = pipe.calc(
                    timestamp,
                    out_port,
                    Value(value=remaining, unit=unit, description=f"Demand for {asset.name}.{port_name}"),
                )
                got = max(self._numeric(response), 0.0)
                provided_total += got
                remaining = max(remaining - got, 0.0)

                if remaining <= 0.0:
                    break
            if remaining <= 0.0:
                break

        return Value(value=provided_total, unit=unit, description=f"Resolved input for {asset.name}.{port_name}")
    
    def _store_results(self, timestamp: datetime) -> None:
        """
        Store simulation results for current timestep.
        
        Args:
            timestamp: Current simulation time
        """
        for asset_id, asset in self.assets.items():
            if asset_id not in self.results:
                self.results[asset_id] = {}
            
            # Store outputs and inputs
            result_data = {
                'outputs': dict(asset.outputs),
                'inputs': dict(asset.inputs)
            }
            self.results[asset_id][timestamp] = result_data
    
    def export_csv(self, output_dir: str) -> None:
        """
        Export all port time-series data from simulation results as CSV files.
        Creates one CSV per asset with input/output port flow columns.
        
        Args:
            output_dir: Directory to save CSV files
        """
        import csv
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for asset_id, asset in self.assets.items():
            csv_file = output_path / f"{asset_id}.csv"

            port_series: Dict[str, Any] = {}
            for port_name, port in getattr(asset, 'input_ports', {}).items():
                if getattr(port, 'flow', None) is not None:
                    port_series[f"in.{port_name}"] = port.flow
            for port_name, port in getattr(asset, 'output_ports', {}).items():
                if getattr(port, 'flow', None) is not None:
                    port_series[f"out.{port_name}"] = port.flow

            if not port_series:
                continue

            # Collect all timestamps
            all_timestamps = set()
            for ts in port_series.values():
                all_timestamps.update(ts.get_all().keys())
            
            all_timestamps = sorted(list(all_timestamps))
            
            # Write CSV
            with open(csv_file, 'w', newline='') as f:
                fieldnames = ['timestamp'] + list(port_series.keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for ts in all_timestamps:
                    row = {'timestamp': ts.isoformat()}
                    for series_name, timeseries in port_series.items():
                        row[series_name] = timeseries.get(ts)
                    writer.writerow(row)
    
    def export_config(self, output_path: str) -> None:
        """
        Export current configuration to YAML file.
        
        Args:
            output_path: Path to save the config YAML
        """
        with open(output_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def get_results(self) -> Dict[str, Dict[datetime, Any]]:
        """
        Get simulation results.
        
        Returns:
            Dictionary of asset results with timestamps and values
        """
        return self.results
