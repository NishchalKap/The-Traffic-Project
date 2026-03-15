#!/usr/bin/env python3
"""
Smart Traffic Light Controller - Main Entry Point

This is the main entry point for the Smart Traffic Light Controller system.
It orchestrates traffic light optimization across multiple intersections.
"""

import sys
import time
import threading
from typing import List, Dict
from services.traffic_optimizer import TrafficOptimizer
from services.camera_input import CameraAnalyzer
from services.signal_controller import SignalController
from models.traffic import TrafficIntersection
from config import Config


class SmartTrafficController:
    """Main controller class for the Smart Traffic Light system."""
    
    def __init__(self, num_intersections: int):
        self.num_intersections = num_intersections
        self.intersections: List[TrafficIntersection] = []
        self.optimizer = TrafficOptimizer()
        self.camera_analyzer = CameraAnalyzer()
        self.signal_controller = SignalController()
        self.running = False
        
        # Initialize intersections
        self._initialize_intersections()
    
    def _initialize_intersections(self):
        """Initialize traffic intersections with default settings."""
        for i in range(self.num_intersections):
            intersection = TrafficIntersection(
                intersection_id=f"intersection_{i+1}",
                name=f"Intersection {i+1}",
                position=(0.0, 0.0)  # TODO: Get actual GPS coordinates
            )
            self.intersections.append(intersection)
            print(f"Initialized {intersection.name} (ID: {intersection.intersection_id})")
    
    def start_system(self):
        """Start the traffic control system."""
        print(f"\nStarting Smart Traffic Controller for {self.num_intersections} intersections...")
        self.running = True
        
        # Start optimization thread
        optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        optimization_thread.start()
        
        # Start camera analysis thread for each intersection
        camera_threads = []
        for intersection in self.intersections:
            thread = threading.Thread(
                target=self._camera_analysis_loop, 
                args=(intersection,), 
                daemon=True
            )
            camera_threads.append(thread)
            thread.start()
        
        print("System started successfully!")
        print("Monitoring traffic and optimizing signals...")
        print("Press Ctrl+C to stop the system\n")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_system()
    
    def _optimization_loop(self):
        """Main optimization loop that runs every 5 seconds."""
        while self.running:
            try:
                # Collect current traffic data from all intersections
                traffic_data = []
                for intersection in self.intersections:
                    traffic_data.append({
                        'intersection_id': intersection.intersection_id,
                        'vehicle_count': intersection.current_vehicle_count,
                        'density': intersection.traffic_density,
                        'wait_time': intersection.accumulated_wait_time,
                        'emergency': intersection.emergency_detected
                    })
                
                # Run optimization algorithm
                optimized_signals = self.optimizer.optimize_traffic_signals(traffic_data)
                
                # Apply optimized signals
                for signal_data in optimized_signals:
                    intersection_id = signal_data['intersection_id']
                    signal_state = signal_data['signal']
                    duration = signal_data['duration']
                    reason = signal_data.get('reason', 'Optimization')
                    
                    # Find the intersection
                    intersection = next(
                        (i for i in self.intersections if i.intersection_id == intersection_id), 
                        None
                    )
                    
                    if intersection:
                        # Apply via SignalController to ensure safe transitions
                        applied = self.signal_controller.update_signal(
                            intersection_id=intersection.intersection_id,
                            target_signal=signal_state,
                            duration=duration,
                            reason=reason
                        )

                        # Mirror minimal state on the intersection for metrics
                        intersection.update_signal(applied['signal'], applied['duration'], applied['reason'])
                        
                        # Log the change
                        print(f"UPDATE {intersection.name}: {applied['signal']} for {applied['duration']}s ({applied['reason']})")
                
                time.sleep(Config.OPTIMIZATION_INTERVAL)  # Run optimization per config
                
            except Exception as e:
                print(f"ERROR in optimization loop: {e}")
                time.sleep(Config.OPTIMIZATION_INTERVAL)
    
    def _camera_analysis_loop(self, intersection: TrafficIntersection):
        """Camera analysis loop for a specific intersection."""
        while self.running:
            try:
                # TODO: In a real system, this would analyze actual camera feeds
                # For now, we'll use the sophisticated detection from the original code
                analysis_result = self.camera_analyzer.analyze_intersection(intersection.intersection_id)
                
                # Update intersection data
                intersection.current_vehicle_count = analysis_result['vehicle_count']
                intersection.traffic_density = analysis_result['density']
                intersection.emergency_detected = analysis_result['emergency']
                
                time.sleep(Config.CAMERA_ANALYSIS_INTERVAL)  # Analyze per config
                
            except Exception as e:
                print(f"ERROR analyzing {intersection.name}: {e}")
                time.sleep(Config.CAMERA_ANALYSIS_INTERVAL)
    
    def stop_system(self):
        """Stop the traffic control system."""
        print("\nStopping Smart Traffic Controller...")
        self.running = False
        
        # Set all intersections to safe state (Red)
        for intersection in self.intersections:
            intersection.current_signal = "Red"
            intersection.signal_duration = 30
            print(f"RED {intersection.name}: Emergency stop - Red light")
        
        print("System stopped safely")


def get_user_input() -> int:
    """Get the number of intersections from the user."""
    while True:
        try:
            num_intersections = int(input("Enter the number of intersecting roads (intersections): "))
            if num_intersections < 1:
                print("ERROR: Please enter a number greater than 0.")
                continue
            elif num_intersections > 10:
                print("WARNING: More than 10 intersections may impact performance.")
                confirm = input("Continue anyway? (y/n): ").lower()
                if confirm != 'y':
                    continue
            return num_intersections
        except ValueError:
            print("ERROR: Please enter a valid number.")


def main():
    """Main entry point."""
    print("=" * 60)
    print("SMART TRAFFIC LIGHT CONTROLLER")
    print("=" * 60)
    print("This system optimizes traffic light timing across multiple intersections")
    print("to minimize total wait time while maintaining fairness and safety.\n")
    
    # Get number of intersections from user
    num_intersections = get_user_input()
    
    # Create and start the controller
    controller = SmartTrafficController(num_intersections)
    controller.start_system()


if __name__ == "__main__":
    main()
