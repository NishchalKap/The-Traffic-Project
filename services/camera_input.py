"""
Camera input and vehicle detection service.

This module handles camera feed analysis, vehicle detection, and emergency vehicle detection.
Based on the sophisticated detection logic from the original app/logic.py.
"""

import os
import time
import cv2
import numpy as np
from collections import deque
from typing import Dict, Any


class CameraAnalyzer:
    """
    Analyzes camera feeds to detect vehicles and emergency vehicles.
    
    This class uses background subtraction and blob filtering to detect moving objects,
    with special logic for emergency vehicle detection via flashing lights.
    """
    
    def __init__(self):
        """Initialize the camera analyzer."""
        self.cameras = {}  # Store camera instances for multiple intersections
        self.detection_history = {}  # Store detection history for each intersection
        
        # Default camera settings
        self.source = os.getenv('OPENCV_VIDEO_SOURCE', '0')
        if self.source.isdigit():
            self.source = int(self.source)
        
        # Detection parameters
        self.min_vehicle_area = 500
        self.traffic_density_high_threshold = 30
        self.traffic_density_medium_threshold = 15
        self.emergency_flasher_threshold = 200
        self.emergency_pulse_threshold = 40
    
    def _get_camera_for_intersection(self, intersection_id: str) -> cv2.VideoCapture:
        """Get or create a camera instance for the given intersection."""
        if intersection_id not in self.cameras:
            # In a real system, each intersection would have its own camera
            # For now, we'll use the same camera source for all intersections
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"Warning: Could not open camera for {intersection_id}")
                return None
            
            # Initialize background subtractor
            back_sub = cv2.createBackgroundSubtractorMOG2(
                history=300, 
                varThreshold=25, 
                detectShadows=True
            )
            
            self.cameras[intersection_id] = {
                'cap': cap,
                'back_sub': back_sub,
                'recent_counts': deque(maxlen=8),
                'red_series': deque(maxlen=15),
                'blue_series': deque(maxlen=15),
                'last_ok': time.time(),
                'consecutive_fail_reads': 0
            }
            
            # Initialize detection history
            self.detection_history[intersection_id] = deque(maxlen=10)
        
        return self.cameras[intersection_id]
    
    def _read_frame(self, intersection_id: str) -> tuple:
        """Read a frame from the camera for the given intersection."""
        camera_data = self._get_camera_for_intersection(intersection_id)
        if not camera_data:
            return False, None
        
        cap = camera_data['cap']
        ok, frame = cap.read()
        
        if not ok:
            # Try reopening once (useful for file end or camera hiccup)
            cap.release()
            cap = cv2.VideoCapture(self.source)
            camera_data['cap'] = cap
            ok, frame = cap.read()
        
        if not ok or frame is None:
            camera_data['consecutive_fail_reads'] += 1
        else:
            camera_data['consecutive_fail_reads'] = 0
            camera_data['last_ok'] = time.time()
        
        return ok, frame
    
    def analyze_intersection(self, intersection_id: str) -> Dict[str, Any]:
        """
        Analyze traffic at a specific intersection.
        
        Args:
            intersection_id: Unique identifier for the intersection
            
        Returns:
            Dictionary containing vehicle count, density, and emergency status
        """
        try:
            camera_data = self._get_camera_for_intersection(intersection_id)
            if not camera_data:
                # Return fallback data if camera unavailable
                return self._get_fallback_analysis(intersection_id)
            
            ok, frame = self._read_frame(intersection_id)
            
            if not ok or frame is None:
                # Use fallback if camera fails repeatedly
                if camera_data['consecutive_fail_reads'] >= 3:
                    return self._get_synthetic_analysis(intersection_id)
                
                # Use last known good data
                if camera_data['recent_counts']:
                    vehicle_count = camera_data['recent_counts'][-1]
                else:
                    vehicle_count = 5  # Default moderate traffic
            else:
                # Analyze the frame
                vehicle_count = self._analyze_frame(frame, camera_data)
            
            # Determine traffic density
            if vehicle_count >= self.traffic_density_high_threshold:
                density = "High"
            elif vehicle_count >= self.traffic_density_medium_threshold:
                density = "Medium"
            else:
                density = "Low"
            
            # Check for emergency vehicles
            emergency = self._detect_emergency_flashers(camera_data)
            
            # Store analysis result
            analysis_result = {
                'vehicle_count': vehicle_count,
                'density': density,
                'emergency': emergency,
                'timestamp': time.time()
            }
            
            self.detection_history[intersection_id].append(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            print(f"Error analyzing intersection {intersection_id}: {e}")
            return self._get_fallback_analysis(intersection_id)
    
    def _analyze_frame(self, frame: np.ndarray, camera_data: dict) -> int:
        """Analyze a single frame to count vehicles."""
        h, w = frame.shape[:2]
        
        # Focus on center horizontal band where the road likely is
        roi_top = int(h * 0.35)
        roi_bottom = int(h * 0.85)
        roi = frame[roi_top:roi_bottom, :]
        
        # Track red/blue intensity for emergency flasher detection
        b, g, r = cv2.split(roi)
        
        # Focus on bright pixels only to reduce noise
        bright_mask = cv2.threshold(
            cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 
            180, 255, cv2.THRESH_BINARY
        )[1]
        
        red_mean = int(cv2.mean(r, mask=bright_mask)[0])
        blue_mean = int(cv2.mean(b, mask=bright_mask)[0])
        
        camera_data['red_series'].append(red_mean)
        camera_data['blue_series'].append(blue_mean)
        
        # Apply background subtraction
        fg_mask = camera_data['back_sub'].apply(roi)
        
        # Morphology to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)
        
        # Find contours representing moving objects
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_vehicle_area:  # Ignore tiny noise
                continue
            
            x, y, cw, ch = cv2.boundingRect(cnt)
            # Filter out very tall-thin or very small boxes (likely noise)
            if cw * ch < 1200:
                continue
            
            count += 1
        
        # Smooth and scale to approximate vehicles in view
        camera_data['recent_counts'].append(count)
        smoothed = int(sum(camera_data['recent_counts']) / max(1, len(camera_data['recent_counts'])))
        
        # Scale factor to approximate vehicles in full intersection from ROI
        approx_vehicle_count = max(0, min(80, int(smoothed * 1.8)))
        
        return approx_vehicle_count
    
    def _detect_emergency_flashers(self, camera_data: dict) -> bool:
        """
        Detect emergency vehicle flashers based on red/blue light patterns.
        
        Returns True if emergency vehicle flashers are detected.
        """
        if len(camera_data['red_series']) < 8 or len(camera_data['blue_series']) < 8:
            return False
        
        red_vals = list(camera_data['red_series'])
        blue_vals = list(camera_data['blue_series'])
        
        red_range = max(red_vals) - min(red_vals)
        blue_range = max(blue_vals) - min(blue_vals)
        
        # Require both colors to show significant pulsing and at least one high peak
        has_peaks = (max(red_vals) > self.emergency_flasher_threshold and 
                    max(blue_vals) > self.emergency_flasher_threshold)
        pulsing = (red_range > self.emergency_pulse_threshold and 
                  blue_range > self.emergency_pulse_threshold)
        
        return bool(has_peaks and pulsing)
    
    def _get_fallback_analysis(self, intersection_id: str) -> Dict[str, Any]:
        """Get fallback analysis data when camera is unavailable."""
        return {
            'vehicle_count': 5,  # Moderate traffic assumption
            'density': 'Medium',
            'emergency': False,
            'timestamp': time.time(),
            'note': 'Camera unavailable - using fallback data'
        }
    
    def _get_synthetic_analysis(self, intersection_id: str) -> Dict[str, Any]:
        """Generate synthetic analysis data for demonstration."""
        # Generate a synthetic pulse between 10 and 35
        synth_count = 10 + int((time.time() % 10) * 2.5)
        
        if synth_count >= self.traffic_density_high_threshold:
            density = "High"
        elif synth_count >= self.traffic_density_medium_threshold:
            density = "Medium"
        else:
            density = "Low"
        
        return {
            'vehicle_count': synth_count,
            'density': density,
            'emergency': False,
            'timestamp': time.time(),
            'note': 'Synthetic data - camera unavailable'
        }
    
    def get_analysis_history(self, intersection_id: str) -> list:
        """Get analysis history for an intersection."""
        return list(self.detection_history.get(intersection_id, []))
    
    def cleanup(self):
        """Clean up camera resources."""
        for intersection_id, camera_data in self.cameras.items():
            if 'cap' in camera_data and camera_data['cap'].isOpened():
                camera_data['cap'].release()
                print(f"Released camera for {intersection_id}")
        
        self.cameras.clear()
        self.detection_history.clear()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
