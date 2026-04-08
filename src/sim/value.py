from typing import Any, Dict, Optional
from datetime import datetime


class Value:
    """Represents a single value with metadata."""
    
    def __init__(
        self,
        value: Any = None,
        unit: str = "",
        description: str = "",
        default: Any = None,
        subscribers: Dict[str, Any] = None,
    ):
        """
        Initialize a Value object.
        
        Args:
            value: The actual value
            unit: Unit of measurement (e.g., "kW", "°C", "€")
            description: Human-readable description
            default: Default value if none provided
            subscribers: dict of 
        """
        self.value = value if value is not None else default
        self.unit = unit
        self.description = description
        self.default = default

    def get(self) -> Any:
        """Get the actual value."""
        return self.value
    
    def set(self, value: Any) -> None:
        """Set the actual value."""
        self.value = value
    
    def __repr__(self) -> str:
        return f"Value({self.value} {self.unit})"
    
    def __str__(self) -> str:
        return f"{self.value} {self.unit}" if self.unit else str(self.value)


class TimeSeries:
    """Represents a time-series of values with associated timestamps."""
    
    def __init__(self, data: Value):
        """
        Initialize a TimeSeries object.
        
        Args:
            data: A Value object defining the metadata for this time-series
        """
        self.data = data
        self.values: Dict[datetime, Any] = {}
    
    def add(self, timestamp: datetime, value: Any) -> None:
        """
        Add a value at a specific timestamp.
        
        Args:
            timestamp: datetime object
            value: The value to store
        """
        self.values[timestamp] = value
    
    def get(self, timestamp: datetime) -> Any:
        """
        Get value at a specific timestamp.
        
        Args:
            timestamp: datetime object
            
        Returns:
            The value at that timestamp, or None if not found
        """
        return self.values.get(timestamp)
    
    def get_all(self) -> Dict[datetime, Any]:
        """Get all timestamp-value pairs."""
        return self.values.copy()
    
    def __len__(self) -> int:
        return len(self.values)
    
    def __repr__(self) -> str:
        return f"TimeSeries({self.data}, {len(self.values)} entries)"


# Alias: Series is the preferred name going forward (TimeSeries retained for
# backwards compatibility with existing code).
Series = TimeSeries