"""
Signal controller service for managing individual traffic signals.

This module handles the control and state management of individual traffic signals,
including transitions, timing, and safety constraints.
"""

import time
from typing import Dict, Any, Optional
from models.traffic import TrafficSignal
from config import Config


class SignalController:
    """
    Controls individual traffic signals with proper state management and transitions.
    
    This class ensures safe signal transitions, proper timing, and maintains
    realistic traffic light behavior with yellow transitions.
    """
    
    def __init__(self):
        """Initialize the signal controller."""
        self.min_green_time = Config.MIN_GREEN_TIME
        self.max_green_time = Config.MAX_GREEN_TIME
        self.yellow_time = Config.YELLOW_TIME
        self.min_red_time = Config.MIN_RED_TIME
        
        # Signal states for each intersection
        self.signal_states = {}  # intersection_id -> current state info
        
        # Transition tracking
        self.transition_states = {}  # intersection_id -> transition info
    
    def update_signal(self, intersection_id: str, target_signal: str, 
                     duration: int, reason: str) -> Dict[str, Any]:
        """
        Update the signal state for an intersection with proper transitions.
        
        Args:
            intersection_id: Unique identifier for the intersection
            target_signal: Target signal state ('Red', 'Yellow', 'Green')
            duration: Duration for the signal in seconds
            reason: Reason for the signal change
            
        Returns:
            Dictionary containing the actual signal state and timing
        """
        current_time = time.time()
        
        # Initialize intersection state if not exists
        if intersection_id not in self.signal_states:
            self.signal_states[intersection_id] = {
                'current_signal': 'Red',
                'duration': 30,
                'last_change': current_time,
                'reason': 'Initialization'
            }
        
        current_state = self.signal_states[intersection_id]
        current_signal = current_state['current_signal']
        
        # Handle direct signal changes (no transition needed)
        if target_signal == current_signal:
            # Update duration for same signal
            self.signal_states[intersection_id].update({
                'duration': duration,
                'last_change': current_time,
                'reason': reason
            })
            
            return {
                'intersection_id': intersection_id,
                'signal': target_signal,
                'duration': duration,
                'reason': reason,
                'transition': False
            }
        
        # Handle transitions between different signals
        return self._handle_signal_transition(intersection_id, current_signal, 
                                            target_signal, duration, reason, current_time)
    
    def _handle_signal_transition(self, intersection_id: str, current_signal: str, 
                                target_signal: str, duration: int, reason: str, 
                                current_time: float) -> Dict[str, Any]:
        """Handle signal transitions with proper yellow phase."""
        
        # Check if we're currently in a transition
        if intersection_id in self.transition_states:
            transition_info = self.transition_states[intersection_id]
            
            # Check if transition is complete
            if current_time - transition_info['start_time'] >= self.yellow_time:
                # Complete the transition
                self._complete_transition(intersection_id, target_signal, duration, reason, current_time)
                
                return {
                    'intersection_id': intersection_id,
                    'signal': target_signal,
                    'duration': duration,
                    'reason': reason,
                    'transition': False
                }
            else:
                # Still in yellow transition
                remaining_yellow = self.yellow_time - (current_time - transition_info['start_time'])
                
                return {
                    'intersection_id': intersection_id,
                    'signal': 'Yellow',
                    'duration': int(remaining_yellow),
                    'reason': f"Transition to {target_signal}",
                    'transition': True
                }
        
        # Start new transition
        self._start_transition(intersection_id, current_signal, target_signal, 
                             duration, reason, current_time)
        
        return {
            'intersection_id': intersection_id,
            'signal': 'Yellow',
            'duration': self.yellow_time,
            'reason': f"Transition to {target_signal}",
            'transition': True
        }
    
    def _start_transition(self, intersection_id: str, current_signal: str, 
                         target_signal: str, duration: int, reason: str, current_time: float):
        """Start a signal transition."""
        self.transition_states[intersection_id] = {
            'from_signal': current_signal,
            'to_signal': target_signal,
            'target_duration': duration,
            'target_reason': reason,
            'start_time': current_time
        }
        
        # Update current state to yellow
        self.signal_states[intersection_id].update({
            'current_signal': 'Yellow',
            'duration': self.yellow_time,
            'last_change': current_time,
            'reason': f"Transition to {target_signal}"
        })
    
    def _complete_transition(self, intersection_id: str, target_signal: str, 
                           duration: int, reason: str, current_time: float):
        """Complete a signal transition."""
        # Update to final signal state
        self.signal_states[intersection_id].update({
            'current_signal': target_signal,
            'duration': duration,
            'last_change': current_time,
            'reason': reason
        })
        
        # Remove transition state
        if intersection_id in self.transition_states:
            del self.transition_states[intersection_id]
    
    def get_signal_state(self, intersection_id: str) -> Optional[Dict[str, Any]]:
        """Get the current signal state for an intersection."""
        if intersection_id not in self.signal_states:
            return None
        
        state = self.signal_states[intersection_id]
        current_time = time.time()
        elapsed = current_time - state['last_change']
        remaining = max(0, state['duration'] - elapsed)
        
        return {
            'intersection_id': intersection_id,
            'signal': state['current_signal'],
            'duration': state['duration'],
            'remaining': remaining,
            'reason': state['reason'],
            'last_change': state['last_change'],
            'in_transition': intersection_id in self.transition_states
        }
    
    def get_all_signal_states(self) -> Dict[str, Dict[str, Any]]:
        """Get signal states for all intersections."""
        all_states = {}
        current_time = time.time()
        
        for intersection_id in self.signal_states:
            all_states[intersection_id] = self.get_signal_state(intersection_id)
        
        return all_states
    
    def should_change_signal(self, intersection_id: str) -> bool:
        """Check if a signal should change based on timing."""
        if intersection_id not in self.signal_states:
            return False
        
        state = self.signal_states[intersection_id]
        current_time = time.time()
        elapsed = current_time - state['last_change']
        
        return elapsed >= state['duration']
    
    def force_signal(self, intersection_id: str, signal: str, duration: int, reason: str):
        """Force a signal change without transitions (for emergencies)."""
        current_time = time.time()
        
        # Clear any existing transitions
        if intersection_id in self.transition_states:
            del self.transition_states[intersection_id]
        
        # Set signal directly
        self.signal_states[intersection_id] = {
            'current_signal': signal,
            'duration': duration,
            'last_change': current_time,
            'reason': reason
        }
        
        print(f"Emergency signal change: {intersection_id} -> {signal} ({duration}s) - {reason}")
    
    def emergency_override(self, intersection_id: str, emergency_type: str = "Emergency Vehicle"):
        """Handle emergency vehicle override."""
        if emergency_type == "Emergency Vehicle":
            self.force_signal(intersection_id, "Green", 90, "Emergency Vehicle Priority")
        elif emergency_type == "Incident":
            self.force_signal(intersection_id, "Red", 120, "Traffic Incident - Intersection Blocked")
        else:
            self.force_signal(intersection_id, "Red", 60, f"Emergency Override: {emergency_type}")
    
    def reset_signal(self, intersection_id: str):
        """Reset a signal to safe default state."""
        self.force_signal(intersection_id, "Red", 30, "System Reset")
        
        # Clear any transitions
        if intersection_id in self.transition_states:
            del self.transition_states[intersection_id]
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get statistics about signal operations."""
        current_time = time.time()
        
        stats = {
            'total_intersections': len(self.signal_states),
            'active_transitions': len(self.transition_states),
            'signal_distribution': {'Red': 0, 'Yellow': 0, 'Green': 0},
            'intersection_details': {}
        }
        
        for intersection_id, state in self.signal_states.items():
            signal = state['current_signal']
            stats['signal_distribution'][signal] += 1
            
            stats['intersection_details'][intersection_id] = {
                'current_signal': signal,
                'duration': state['duration'],
                'remaining': max(0, state['duration'] - (current_time - state['last_change'])),
                'in_transition': intersection_id in self.transition_states,
                'reason': state['reason']
            }
        
        return stats
    
    def cleanup_expired_transitions(self):
        """Clean up expired transitions."""
        current_time = time.time()
        expired_transitions = []
        
        for intersection_id, transition_info in self.transition_states.items():
            if current_time - transition_info['start_time'] >= self.yellow_time * 2:  # Allow some buffer
                expired_transitions.append(intersection_id)
        
        for intersection_id in expired_transitions:
            print(f"Cleaning up expired transition for {intersection_id}")
            del self.transition_states[intersection_id]
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup_expired_transitions()
