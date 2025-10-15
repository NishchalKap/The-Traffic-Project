"""
Traffic intersection and signal models for the Smart Traffic Controller.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import time


@dataclass
class TrafficSignal:
    """Represents a traffic signal state."""
    
    color: str  # 'Red', 'Yellow', 'Green'
    duration: int  # Duration in seconds
    reason: str  # Reason for the signal change
    timestamp: float  # When the signal was set
    
    def __post_init__(self):
        if self.color not in ['Red', 'Yellow', 'Green']:
            raise ValueError(f"Invalid signal color: {self.color}")
        if self.duration < 0:
            raise ValueError(f"Invalid signal duration: {self.duration}")


class TrafficIntersection:
    """Represents a traffic intersection with all its properties and state."""
    
    def __init__(self, intersection_id: str, name: str, position: Tuple[float, float]):
        self.intersection_id = intersection_id
        self.name = name
        self.position = position  # (latitude, longitude)
        
        # Current state
        self.current_signal = "Red"
        self.signal_duration = 30
        self.last_signal_change = time.time()
        
        # Traffic data
        self.current_vehicle_count = 0
        self.traffic_density = "Low"  # Low, Medium, High
        self.accumulated_wait_time = 0
        self.average_wait_time = 0
        
        # Emergency and incident data
        self.emergency_detected = False
        self.incident_present = False
        self.incident_severity = None
        
        # Historical data for optimization
        self.vehicle_count_history = []
        self.signal_change_history = []
        self.wait_time_history = []
        
        # Configuration
        self.min_green_time = 15
        self.max_green_time = 90
        self.yellow_time = 3
        self.min_red_time = 5
        
    def update_vehicle_count(self, count: int):
        """Update the current vehicle count and density."""
        self.current_vehicle_count = max(0, count)
        self.vehicle_count_history.append({
            'count': count,
            'timestamp': time.time()
        })
        
        # Keep only last 60 entries (2 minutes at 2-second intervals)
        if len(self.vehicle_count_history) > 60:
            self.vehicle_count_history = self.vehicle_count_history[-60:]
        
        # Update traffic density
        if count >= 30:
            self.traffic_density = "High"
        elif count >= 15:
            self.traffic_density = "Medium"
        else:
            self.traffic_density = "Low"
    
    def update_signal(self, signal: str, duration: int, reason: str):
        """Update the traffic signal state."""
        old_signal = self.current_signal
        self.current_signal = signal
        self.signal_duration = duration
        self.last_signal_change = time.time()
        
        # Record signal change
        self.signal_change_history.append({
            'from': old_signal,
            'to': signal,
            'duration': duration,
            'reason': reason,
            'timestamp': time.time()
        })
        
        # Keep only last 100 entries
        if len(self.signal_change_history) > 100:
            self.signal_change_history = self.signal_change_history[-100:]
    
    def update_wait_time(self, additional_wait: float):
        """Update accumulated wait time."""
        self.accumulated_wait_time += additional_wait
        self.wait_time_history.append({
            'wait_time': additional_wait,
            'timestamp': time.time()
        })
        
        # Keep only last 100 entries
        if len(self.wait_time_history) > 100:
            self.wait_time_history = self.wait_time_history[-100:]
        
        # Update average wait time
        if self.wait_time_history:
            self.average_wait_time = sum(w['wait_time'] for w in self.wait_time_history) / len(self.wait_time_history)
    
    def get_signal_time_remaining(self) -> float:
        """Get the remaining time for the current signal."""
        elapsed = time.time() - self.last_signal_change
        remaining = self.signal_duration - elapsed
        return max(0, remaining)
    
    def should_change_signal(self) -> bool:
        """Check if the signal should change based on timing."""
        return self.get_signal_time_remaining() <= 0
    
    def get_current_state(self) -> dict:
        """Get the current state of the intersection."""
        return {
            'intersection_id': self.intersection_id,
            'name': self.name,
            'position': self.position,
            'current_signal': self.current_signal,
            'signal_duration': self.signal_duration,
            'time_remaining': self.get_signal_time_remaining(),
            'vehicle_count': self.current_vehicle_count,
            'traffic_density': self.traffic_density,
            'emergency_detected': self.emergency_detected,
            'incident_present': self.incident_present,
            'accumulated_wait_time': self.accumulated_wait_time,
            'average_wait_time': self.average_wait_time,
            'last_update': time.time()
        }
    
    def get_priority_score(self) -> float:
        """Calculate priority score for optimization (higher = more urgent)."""
        base_score = 0
        
        # Emergency vehicles get highest priority
        if self.emergency_detected:
            base_score += 100
        
        # Incidents increase priority
        if self.incident_present:
            base_score += 50
        
        # High traffic density increases priority
        if self.traffic_density == "High":
            base_score += 30
        elif self.traffic_density == "Medium":
            base_score += 15
        
        # Accumulated wait time increases priority
        base_score += min(self.accumulated_wait_time * 0.1, 25)
        
        # Current signal state affects priority
        if self.current_signal == "Red" and self.current_vehicle_count > 0:
            base_score += 20
        
        return base_score
    
    def __repr__(self):
        return f"<TrafficIntersection {self.name}: {self.current_signal} ({self.current_vehicle_count} vehicles)>"
