#!/usr/bin/env python3
"""
Smart Traffic Light Controller - Main Entry Point

This is the main entry point for the Smart Traffic Light Controller system.
It orchestrates traffic light optimization across multiple intersections.
"""

import sys
import time
import threading
import logging
from typing import List, Dict
from services.traffic_optimizer import TrafficOptimizer
from services.camera_input import CameraAnalyzer
from services.signal_controller import SignalController
from models.traffic import TrafficIntersection
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('traffic_controller.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SmartTrafficController:
    """Main controller class for the Smart Traffic Light system."""
    
    def __init__(self, num_intersections: int):
        self.num_intersections = num_intersections
        self.intersections: List[TrafficIntersection] = []
        self.optimizer = TrafficOptimizer()
        self.camera_analyzer = CameraAnalyzer()
        self.signal_controller = SignalController()
        self.running = False
        self.start_time = None
        self.optimization_count = 0
        self.error_count = 0
        
        # Initialize intersections
        self._initialize_intersections()
        logger.info(f"SmartTrafficController initialized with {num_intersections} intersections")
    
    def _initialize_intersections(self):
        """Initialize traffic intersections with default settings."""
        for i in range(self.num_intersections):
            intersection = TrafficIntersection(
                intersection_id=f"intersection_{i+1}",
                name=f"Intersection {i+1}",
                position=(0.0, 0.0)  # TODO: Get actual GPS coordinates
            )
            self.intersections.append(intersection)
            logger.info(f"Initialized {intersection.name} (ID: {intersection.intersection_id})")
            print(f"Initialized {intersection.name} (ID: {intersection.intersection_id})")
    
    def start_system(self):
        """Start the traffic control system."""
        logger.info(f"Starting Smart Traffic Controller for {self.num_intersections} intersections...")
        print(f"\nStarting Smart Traffic Controller for {self.num_intersections} intersections...")
        self.running = True
        self.start_time = time.time()
        
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
        
        logger.info("System started successfully!")
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
                self.optimization_count += 1
                
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
                        logger.info(f"Signal Change: {intersection.name}: {applied['signal']} for {applied['duration']}s ({applied['reason']})")
                        print(f"Signal Change: {intersection.name}: {applied['signal']} for {applied['duration']}s ({applied['reason']})")
                
                time.sleep(Config.OPTIMIZATION_INTERVAL)  # Run optimization per config
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in optimization loop: {e}")
                print(f"Error in optimization loop: {e}")
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
                self.error_count += 1
                logger.error(f"Error analyzing {intersection.name}: {e}")
                print(f"Error analyzing {intersection.name}: {e}")
                time.sleep(Config.CAMERA_ANALYSIS_INTERVAL)
    
    def stop_system(self):
        """Stop the traffic control system."""
        logger.info("Stopping Smart Traffic Controller...")
        print("\nStopping Smart Traffic Controller...")
        self.running = False
        
        # Set all intersections to safe state (Red)
        for intersection in self.intersections:
            intersection.current_signal = "Red"
            intersection.signal_duration = 30
            logger.info(f"{intersection.name}: Emergency stop - Red light")
            print(f"{intersection.name}: Emergency stop - Red light")
        
        # Cleanup resources
        self.camera_analyzer.cleanup()
        
        # Print system statistics
        if self.start_time:
            uptime = time.time() - self.start_time
            logger.info(f"System uptime: {uptime:.2f} seconds")
            logger.info(f"Total optimizations: {self.optimization_count}")
            logger.info(f"Total errors: {self.error_count}")
            print(f"System uptime: {uptime:.2f} seconds")
            print(f"Total optimizations: {self.optimization_count}")
            print(f"Total errors: {self.error_count}")
        
        logger.info("System stopped safely")
        print("System stopped safely")
    
    def get_system_status(self) -> Dict:
        """Get current system status and statistics."""
        return {
            'running': self.running,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'intersections': len(self.intersections),
            'optimization_count': self.optimization_count,
            'error_count': self.error_count,
            'intersection_states': [i.get_current_state() for i in self.intersections]
        }


def get_user_input() -> int:
    """Get the number of intersections from the user."""
    # For automated testing, use default value
    try:
        num_intersections = int(input("Enter the number of intersecting roads (intersections): "))
    except (EOFError, KeyboardInterrupt):
        print("Using default value: 3 intersections")
        return 3
    
    while True:
        try:
            if num_intersections < 1:
                print("Please enter a number greater than 0.")
                num_intersections = int(input("Enter the number of intersecting roads (intersections): "))
                continue
            elif num_intersections > 10:
                print("Warning: More than 10 intersections may impact performance.")
                confirm = input("Continue anyway? (y/n): ").lower()
                if confirm != 'y':
                    num_intersections = int(input("Enter the number of intersecting roads (intersections): "))
                    continue
            return num_intersections
        except ValueError:
            print("Please enter a valid number.")
            num_intersections = int(input("Enter the number of intersecting roads (intersections): "))


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
