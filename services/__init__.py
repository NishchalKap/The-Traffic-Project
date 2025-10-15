"""
Services module for the Smart Traffic Light Controller.

This module contains the core business logic services:
- CameraInput: Handles camera feed analysis and vehicle detection
- TrafficOptimizer: Optimizes traffic signal timing across intersections
- SignalController: Controls individual traffic signals
"""

from .camera_input import CameraAnalyzer
from .traffic_optimizer import TrafficOptimizer
from .signal_controller import SignalController

__all__ = ['CameraAnalyzer', 'TrafficOptimizer', 'SignalController']