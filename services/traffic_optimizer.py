"""
Traffic optimization service for multi-intersection coordination.

This module implements the core optimization algorithm that minimizes total wait time
across all intersections while maintaining fairness and realistic traffic cycles.
"""

import time
from typing import List, Dict, Any
from config import Config


class TrafficOptimizer:
    """
    Optimizes traffic signal timing across multiple intersections.
    
    The optimization algorithm considers:
    - Vehicle counts at each intersection
    - Accumulated wait times
    - Emergency vehicle priority
    - Traffic incidents
    - Fairness across intersections
    - Realistic traffic cycle constraints
    """
    
    def __init__(self):
        """Initialize the traffic optimizer."""
        self.min_green_time = Config.MIN_GREEN_TIME
        self.max_green_time = Config.MAX_GREEN_TIME
        self.yellow_time = Config.YELLOW_TIME
        self.min_red_time = Config.MIN_RED_TIME
        
        # Optimization parameters
        self.wait_time_weight = 0.4  # Weight for accumulated wait time
        self.vehicle_count_weight = 0.3  # Weight for current vehicle count
        self.emergency_weight = 0.3  # Weight for emergency priority
        
        # Fairness parameters
        self.max_consecutive_green = 3  # Maximum consecutive green cycles for one intersection
        self.fairness_window = 300  # 5 minutes fairness window
        
        # Historical data for fairness tracking
        self.intersection_cycles = {}  # Track green cycles per intersection
        self.last_optimization = {}  # Track last optimization results
    
    def optimize_traffic_signals(self, traffic_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize traffic signals for all intersections.
        
        Args:
            traffic_data: List of dictionaries containing traffic data for each intersection
            
        Returns:
            List of optimized signal configurations for each intersection
        """
        if not traffic_data:
            return []
        
        current_time = time.time()
        
        # Calculate priority scores for each intersection
        priority_scores = self._calculate_priority_scores(traffic_data, current_time)
        
        # Apply fairness constraints
        adjusted_scores = self._apply_fairness_constraints(priority_scores, current_time)
        
        # Determine signal states and durations
        optimized_signals = self._determine_signal_states(traffic_data, adjusted_scores, current_time)
        
        # Update historical tracking
        self._update_historical_data(optimized_signals, current_time)
        
        return optimized_signals
    
    def _calculate_priority_scores(self, traffic_data: List[Dict[str, Any]], current_time: float) -> Dict[str, float]:
        """Calculate priority scores for each intersection."""
        priority_scores = {}
        
        for data in traffic_data:
            intersection_id = data['intersection_id']
            
            # Base score starts at 0
            score = 0
            
            # Emergency vehicles get highest priority
            if data.get('emergency', False):
                score += 100 * self.emergency_weight
            
            # Vehicle count contributes to priority
            vehicle_count = data.get('vehicle_count', 0)
            vehicle_score = min(vehicle_count / 10.0, 10.0)  # Normalize to 0-10
            score += vehicle_score * self.vehicle_count_weight
            
            # Accumulated wait time contributes to priority
            wait_time = data.get('wait_time', 0)
            wait_score = min(wait_time / 30.0, 10.0)  # Normalize to 0-10
            score += wait_score * self.wait_time_weight
            
            # Traffic density bonus
            density = data.get('density', 'Low')
            if density == 'High':
                score += 5
            elif density == 'Medium':
                score += 2
            
            priority_scores[intersection_id] = score
        
        return priority_scores
    
    def _apply_fairness_constraints(self, priority_scores: Dict[str, float], current_time: float) -> Dict[str, float]:
        """Apply fairness constraints to prevent intersection starvation."""
        adjusted_scores = priority_scores.copy()
        
        for intersection_id, score in priority_scores.items():
            # Check if intersection has had too many consecutive green cycles
            if intersection_id in self.intersection_cycles:
                recent_greens = self._count_recent_green_cycles(intersection_id, current_time)
                
                if recent_greens >= self.max_consecutive_green:
                    # Reduce priority to allow other intersections
                    adjusted_scores[intersection_id] = score * 0.3
                    
                elif recent_greens >= self.max_consecutive_green - 1:
                    # Slightly reduce priority
                    adjusted_scores[intersection_id] = score * 0.7
        
        return adjusted_scores
    
    def _count_recent_green_cycles(self, intersection_id: str, current_time: float) -> int:
        """Count recent green cycles for fairness tracking."""
        if intersection_id not in self.intersection_cycles:
            return 0
        
        recent_greens = 0
        cutoff_time = current_time - self.fairness_window
        
        for cycle_time in reversed(self.intersection_cycles[intersection_id]):
            if cycle_time < cutoff_time:
                break
            recent_greens += 1
        
        return recent_greens
    
    def _determine_signal_states(self, traffic_data: List[Dict[str, Any]], 
                                priority_scores: Dict[str, float], 
                                current_time: float) -> List[Dict[str, Any]]:
        """Determine optimal signal states and durations."""
        optimized_signals = []
        
        # Find the intersection with highest priority
        if not priority_scores:
            return optimized_signals
        
        max_priority_intersection = max(priority_scores.items(), key=lambda x: x[1])
        
        for data in traffic_data:
            intersection_id = data['intersection_id']
            priority_score = priority_scores.get(intersection_id, 0)
            
            # Determine signal state
            if intersection_id == max_priority_intersection[0]:
                signal_state = "Green"
                duration = self._calculate_green_duration(data)
                reason = f"Priority intersection (score: {priority_score:.1f})"
            else:
                signal_state = "Red"
                duration = self._calculate_red_duration(data)
                reason = f"Lower priority (score: {priority_score:.1f})"
            
            # Handle emergency override
            if data.get('emergency', False):
                signal_state = "Green"
                duration = 90  # Long green for emergency vehicles
                reason = "Emergency vehicle priority"
            
            # Handle incident override
            if data.get('incident_present', False):
                signal_state = "Red"
                duration = 120  # Long red for incidents
                reason = "Traffic incident - intersection blocked"
            
            optimized_signals.append({
                'intersection_id': intersection_id,
                'signal': signal_state,
                'duration': duration,
                'reason': reason,
                'priority_score': priority_score,
                'timestamp': current_time
            })
        
        return optimized_signals
    
    def _calculate_green_duration(self, data: Dict[str, Any]) -> int:
        """Calculate optimal green light duration."""
        vehicle_count = data.get('vehicle_count', 0)
        density = data.get('density', 'Low')
        
        # Base duration
        if density == 'High':
            base_duration = 60
        elif density == 'Medium':
            base_duration = 40
        else:
            base_duration = 25
        
        # Adjust based on vehicle count
        if vehicle_count > 50:
            base_duration += 20
        elif vehicle_count > 30:
            base_duration += 10
        
        # Apply constraints
        duration = max(self.min_green_time, min(base_duration, self.max_green_time))
        
        return duration
    
    def _calculate_red_duration(self, data: Dict[str, Any]) -> int:
        """Calculate optimal red light duration."""
        vehicle_count = data.get('vehicle_count', 0)
        
        # Shorter red if no vehicles waiting
        if vehicle_count == 0:
            duration = self.min_red_time
        else:
            # Longer red if vehicles are waiting (to balance the system)
            duration = min(self.min_red_time + vehicle_count * 2, 45)
        
        return duration
    
    def _update_historical_data(self, optimized_signals: List[Dict[str, Any]], current_time: float):
        """Update historical data for fairness tracking."""
        for signal_data in optimized_signals:
            intersection_id = signal_data['intersection_id']
            
            if signal_data['signal'] == 'Green':
                # Track green cycles
                if intersection_id not in self.intersection_cycles:
                    self.intersection_cycles[intersection_id] = []
                
                self.intersection_cycles[intersection_id].append(current_time)
                
                # Keep only recent cycles
                cutoff_time = current_time - self.fairness_window
                self.intersection_cycles[intersection_id] = [
                    cycle_time for cycle_time in self.intersection_cycles[intersection_id]
                    if cycle_time >= cutoff_time
                ]
        
        # Store last optimization results
        self.last_optimization = {
            signal['intersection_id']: signal for signal in optimized_signals
        }
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics and fairness metrics."""
        stats = {
            'total_intersections': len(self.intersection_cycles),
            'fairness_window': self.fairness_window,
            'max_consecutive_green': self.max_consecutive_green,
            'intersection_cycles': {},
            'last_optimization': self.last_optimization
        }
        
        for intersection_id, cycles in self.intersection_cycles.items():
            stats['intersection_cycles'][intersection_id] = {
                'total_green_cycles': len(cycles),
                'recent_green_cycles': len([c for c in cycles if time.time() - c < self.fairness_window]),
                'last_green_cycle': max(cycles) if cycles else None
            }
        
        return stats
    
    def reset_fairness_tracking(self):
        """Reset fairness tracking data."""
        self.intersection_cycles.clear()
        self.last_optimization.clear()
        print("🔄 Fairness tracking reset")
    
    def adjust_parameters(self, wait_weight: float = None, vehicle_weight: float = None, 
                         emergency_weight: float = None, max_consecutive: int = None):
        """Adjust optimization parameters."""
        if wait_weight is not None:
            self.wait_time_weight = wait_weight
        if vehicle_weight is not None:
            self.vehicle_count_weight = vehicle_weight
        if emergency_weight is not None:
            self.emergency_weight = emergency_weight
        if max_consecutive is not None:
            self.max_consecutive_green = max_consecutive
        
        print(f"⚙️  Optimization parameters updated:")
        print(f"   Wait time weight: {self.wait_time_weight}")
        print(f"   Vehicle count weight: {self.vehicle_count_weight}")
        print(f"   Emergency weight: {self.emergency_weight}")
        print(f"   Max consecutive green: {self.max_consecutive_green}")
