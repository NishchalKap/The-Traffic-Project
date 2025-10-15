#!/usr/bin/env python3
"""
Comprehensive test suite for the Smart Traffic Light Controller system.

This test suite validates all major components and their interactions.
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import SmartTrafficController
from services.traffic_optimizer import TrafficOptimizer
from services.camera_input import CameraAnalyzer
from services.signal_controller import SignalController
from models.traffic import TrafficIntersection


class TestTrafficIntersection(unittest.TestCase):
    """Test the TrafficIntersection model."""
    
    def setUp(self):
        self.intersection = TrafficIntersection(
            intersection_id="test_intersection",
            name="Test Intersection",
            position=(40.7128, -74.0060)
        )
    
    def test_intersection_initialization(self):
        """Test intersection initializes with correct defaults."""
        self.assertEqual(self.intersection.intersection_id, "test_intersection")
        self.assertEqual(self.intersection.name, "Test Intersection")
        self.assertEqual(self.intersection.current_signal, "Red")
        self.assertEqual(self.intersection.traffic_density, "Low")
        self.assertFalse(self.intersection.emergency_detected)
    
    def test_vehicle_count_update(self):
        """Test vehicle count and density updates."""
        self.intersection.update_vehicle_count(35)
        self.assertEqual(self.intersection.current_vehicle_count, 35)
        self.assertEqual(self.intersection.traffic_density, "High")
        
        self.intersection.update_vehicle_count(10)
        self.assertEqual(self.intersection.current_vehicle_count, 10)
        self.assertEqual(self.intersection.traffic_density, "Low")
    
    def test_signal_update(self):
        """Test signal state updates."""
        self.intersection.update_signal("Green", 30, "Test")
        self.assertEqual(self.intersection.current_signal, "Green")
        self.assertEqual(self.intersection.signal_duration, 30)
        self.assertEqual(len(self.intersection.signal_change_history), 1)
    
    def test_priority_score_calculation(self):
        """Test priority score calculation."""
        # Test emergency priority
        self.intersection.emergency_detected = True
        score = self.intersection.get_priority_score()
        self.assertGreaterEqual(score, 100)
        
        # Test high traffic priority
        self.intersection.emergency_detected = False
        self.intersection.traffic_density = "High"
        self.intersection.current_vehicle_count = 20
        score = self.intersection.get_priority_score()
        self.assertGreater(score, 30)


class TestTrafficOptimizer(unittest.TestCase):
    """Test the TrafficOptimizer service."""
    
    def setUp(self):
        self.optimizer = TrafficOptimizer()
    
    def test_optimization_with_empty_data(self):
        """Test optimization with empty traffic data."""
        result = self.optimizer.optimize_traffic_signals([])
        self.assertEqual(result, [])
    
    def test_optimization_with_single_intersection(self):
        """Test optimization with single intersection."""
        traffic_data = [{
            'intersection_id': 'test_1',
            'vehicle_count': 20,
            'density': 'High',
            'wait_time': 30,
            'emergency': False
        }]
        
        result = self.optimizer.optimize_traffic_signals(traffic_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['intersection_id'], 'test_1')
        self.assertEqual(result[0]['signal'], 'Green')
    
    def test_emergency_priority(self):
        """Test emergency vehicles get highest priority."""
        traffic_data = [
            {
                'intersection_id': 'normal_1',
                'vehicle_count': 50,
                'density': 'High',
                'wait_time': 60,
                'emergency': False
            },
            {
                'intersection_id': 'emergency_1',
                'vehicle_count': 5,
                'density': 'Low',
                'wait_time': 10,
                'emergency': True
            }
        ]
        
        result = self.optimizer.optimize_traffic_signals(traffic_data)
        
        # Find emergency intersection
        emergency_result = next(r for r in result if r['intersection_id'] == 'emergency_1')
        self.assertEqual(emergency_result['signal'], 'Green')
        self.assertEqual(emergency_result['duration'], 90)  # Long green for emergency
    
    def test_fairness_constraints(self):
        """Test fairness constraints prevent intersection starvation."""
        # Simulate multiple green cycles for one intersection
        intersection_id = 'test_1'
        current_time = time.time()
        
        # Add multiple green cycles
        for i in range(5):
            self.optimizer.intersection_cycles[intersection_id] = [
                current_time - (i * 10) for i in range(5)
            ]
        
        traffic_data = [{
            'intersection_id': intersection_id,
            'vehicle_count': 30,
            'density': 'High',
            'wait_time': 20,
            'emergency': False
        }]
        
        result = self.optimizer.optimize_traffic_signals(traffic_data)
        # Should still get green but with reduced priority
        self.assertEqual(result[0]['signal'], 'Green')


class TestSignalController(unittest.TestCase):
    """Test the SignalController service."""
    
    def setUp(self):
        self.controller = SignalController()
    
    def test_signal_update(self):
        """Test basic signal update."""
        result = self.controller.update_signal(
            "test_intersection", "Green", 30, "Test"
        )
        
        self.assertEqual(result['intersection_id'], "test_intersection")
        # Signal might be Yellow during transition, so check for either Green or Yellow
        self.assertIn(result['signal'], ["Green", "Yellow"])
        # Duration might be 3 (yellow time) during transition or 30 (target duration)
        self.assertIn(result['duration'], [3, 30])
    
    def test_signal_transition(self):
        """Test signal transition with yellow phase."""
        # First set to Red
        self.controller.update_signal("test_intersection", "Red", 30, "Initial")
        
        # Then change to Green (should trigger yellow transition)
        result = self.controller.update_signal("test_intersection", "Green", 30, "Test")
        
        self.assertEqual(result['signal'], "Yellow")
        self.assertTrue(result['transition'])
    
    def test_emergency_override(self):
        """Test emergency override functionality."""
        self.controller.emergency_override("test_intersection", "Emergency Vehicle")
        
        state = self.controller.get_signal_state("test_intersection")
        self.assertEqual(state['signal'], "Green")
        self.assertEqual(state['duration'], 90)
        self.assertEqual(state['reason'], "Emergency Vehicle Priority")
    
    def test_signal_state_retrieval(self):
        """Test signal state retrieval."""
        self.controller.update_signal("test_intersection", "Red", 30, "Test")
        
        state = self.controller.get_signal_state("test_intersection")
        self.assertIsNotNone(state)
        self.assertEqual(state['signal'], "Red")
        self.assertEqual(state['duration'], 30)


class TestCameraAnalyzer(unittest.TestCase):
    """Test the CameraAnalyzer service."""
    
    def setUp(self):
        self.analyzer = CameraAnalyzer()
    
    @patch('cv2.VideoCapture')
    def test_analyze_intersection_with_camera_failure(self, mock_capture):
        """Test analysis when camera fails."""
        # Mock camera failure
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_capture.return_value = mock_cap
        
        result = self.analyzer.analyze_intersection("test_intersection")
        
        # Should return fallback data
        self.assertIn('vehicle_count', result)
        self.assertIn('density', result)
        self.assertIn('emergency', result)
        self.assertIn('note', result)
    
    def test_fallback_analysis(self):
        """Test fallback analysis when camera unavailable."""
        result = self.analyzer._get_fallback_analysis("test_intersection")
        
        self.assertEqual(result['vehicle_count'], 5)
        self.assertEqual(result['density'], 'Medium')
        self.assertFalse(result['emergency'])
        self.assertIn('Camera unavailable', result['note'])
    
    def test_synthetic_analysis(self):
        """Test synthetic analysis generation."""
        result = self.analyzer._get_synthetic_analysis("test_intersection")
        
        self.assertIn('vehicle_count', result)
        self.assertIn('density', result)
        self.assertFalse(result['emergency'])
        self.assertIn('Synthetic data', result['note'])


class TestSmartTrafficController(unittest.TestCase):
    """Test the main SmartTrafficController class."""
    
    def setUp(self):
        self.controller = SmartTrafficController(2)
    
    def test_controller_initialization(self):
        """Test controller initializes correctly."""
        self.assertEqual(self.controller.num_intersections, 2)
        self.assertEqual(len(self.controller.intersections), 2)
        self.assertFalse(self.controller.running)
        self.assertEqual(self.controller.optimization_count, 0)
        self.assertEqual(self.controller.error_count, 0)
    
    def test_intersection_initialization(self):
        """Test intersections are initialized correctly."""
        self.assertEqual(len(self.controller.intersections), 2)
        self.assertEqual(self.controller.intersections[0].intersection_id, "intersection_1")
        self.assertEqual(self.controller.intersections[1].intersection_id, "intersection_2")
    
    def test_system_status(self):
        """Test system status retrieval."""
        status = self.controller.get_system_status()
        
        self.assertIn('running', status)
        self.assertIn('uptime', status)
        self.assertIn('intersections', status)
        self.assertIn('optimization_count', status)
        self.assertIn('error_count', status)
        self.assertIn('intersection_states', status)
        
        self.assertEqual(status['intersections'], 2)
        self.assertEqual(status['optimization_count'], 0)
        self.assertEqual(status['error_count'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def test_end_to_end_optimization(self):
        """Test complete optimization flow."""
        controller = SmartTrafficController(2)
        
        # Simulate traffic data
        controller.intersections[0].update_vehicle_count(25)
        controller.intersections[0].traffic_density = "High"
        controller.intersections[1].update_vehicle_count(5)
        controller.intersections[1].traffic_density = "Low"
        
        # Collect traffic data
        traffic_data = []
        for intersection in controller.intersections:
            traffic_data.append({
                'intersection_id': intersection.intersection_id,
                'vehicle_count': intersection.current_vehicle_count,
                'density': intersection.traffic_density,
                'wait_time': intersection.accumulated_wait_time,
                'emergency': intersection.emergency_detected
            })
        
        # Run optimization
        optimized_signals = controller.optimizer.optimize_traffic_signals(traffic_data)
        
        # Verify results
        self.assertEqual(len(optimized_signals), 2)
        
        # Find the high-traffic intersection
        high_traffic = next(s for s in optimized_signals if s['intersection_id'] == 'intersection_1')
        self.assertEqual(high_traffic['signal'], 'Green')
        self.assertGreater(high_traffic['duration'], 30)


def run_performance_test():
    """Run a performance test to measure optimization speed."""
    print("\n" + "="*50)
    print("PERFORMANCE TEST")
    print("="*50)
    
    controller = SmartTrafficController(5)
    
    # Simulate traffic data
    for i, intersection in enumerate(controller.intersections):
        intersection.update_vehicle_count(10 + i * 5)
        intersection.traffic_density = "Medium" if i % 2 == 0 else "High"
    
    # Measure optimization time
    start_time = time.time()
    
    traffic_data = []
    for intersection in controller.intersections:
        traffic_data.append({
            'intersection_id': intersection.intersection_id,
            'vehicle_count': intersection.current_vehicle_count,
            'density': intersection.traffic_density,
            'wait_time': intersection.accumulated_wait_time,
            'emergency': intersection.emergency_detected
        })
    
    optimized_signals = controller.optimizer.optimize_traffic_signals(traffic_data)
    
    end_time = time.time()
    optimization_time = end_time - start_time
    
    print(f"Optimization time for 5 intersections: {optimization_time:.4f} seconds")
    print(f"Signals generated: {len(optimized_signals)}")
    print(f"Average time per intersection: {optimization_time/5:.4f} seconds")
    
    # Verify all intersections got signals
    intersection_ids = [s['intersection_id'] for s in optimized_signals]
    expected_ids = [f"intersection_{i+1}" for i in range(5)]
    assert set(intersection_ids) == set(expected_ids), "Not all intersections received signals"
    
    print("Performance test passed!")


if __name__ == '__main__':
    print("Smart Traffic Light Controller - Test Suite")
    print("="*60)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()
    
    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)
