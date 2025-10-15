"""
Configuration settings for the Smart Traffic Light Controller.
"""

import os

class Config:
    """Main configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-traffic-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///traffic_controller.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Camera/Video settings
    VIDEO_SOURCE = os.environ.get('OPENCV_VIDEO_SOURCE', '0')  # Default to webcam
    
    # Traffic optimization settings
    OPTIMIZATION_INTERVAL = 5  # seconds between optimization cycles
    CAMERA_ANALYSIS_INTERVAL = 2  # seconds between camera analysis cycles
    
    # Traffic light timing constraints
    MIN_GREEN_TIME = 15  # minimum green light duration (seconds)
    MAX_GREEN_TIME = 90  # maximum green light duration (seconds)
    YELLOW_TIME = 3  # yellow light duration (seconds)
    MIN_RED_TIME = 5  # minimum red light duration (seconds)
    
    # Vehicle detection settings
    MIN_VEHICLE_AREA = 500  # minimum area for vehicle detection
    TRAFFIC_DENSITY_HIGH_THRESHOLD = 30
    TRAFFIC_DENSITY_MEDIUM_THRESHOLD = 15
    
    # Emergency vehicle detection
    EMERGENCY_FLASHER_THRESHOLD = 200  # brightness threshold for emergency lights
    EMERGENCY_PULSE_THRESHOLD = 40  # pulse variation threshold
    
    # Database settings
    DATABASE_INSTANCE_PATH = 'instance'
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Create instance directory for database
        import os
        os.makedirs(Config.DATABASE_INSTANCE_PATH, exist_ok=True)
