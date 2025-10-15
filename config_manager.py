#!/usr/bin/env python3
"""
Configuration management system for the Smart Traffic Light Controller.

This module provides dynamic configuration management, allowing runtime
adjustment of system parameters without restarting the system.
"""

import json
import os
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from config import Config


@dataclass
class TrafficConfig:
    """Traffic-specific configuration parameters."""
    optimization_interval: int = 5
    camera_analysis_interval: int = 2
    min_green_time: int = 15
    max_green_time: int = 90
    yellow_time: int = 3
    min_red_time: int = 5
    min_vehicle_area: int = 500
    traffic_density_high_threshold: int = 30
    traffic_density_medium_threshold: int = 15
    emergency_flasher_threshold: int = 200
    emergency_pulse_threshold: int = 40


@dataclass
class OptimizationConfig:
    """Optimization algorithm configuration parameters."""
    wait_time_weight: float = 0.4
    vehicle_count_weight: float = 0.3
    emergency_weight: float = 0.3
    max_consecutive_green: int = 3
    fairness_window: int = 300
    priority_boost_emergency: float = 100.0
    priority_boost_incident: float = 50.0
    priority_boost_high_traffic: float = 30.0
    priority_boost_medium_traffic: float = 15.0


@dataclass
class SystemConfig:
    """System-wide configuration parameters."""
    log_level: str = "INFO"
    enable_web_interface: bool = True
    web_port: int = 5000
    enable_database: bool = True
    max_intersections: int = 20
    system_timeout: int = 3600  # 1 hour
    cleanup_interval: int = 300  # 5 minutes


class ConfigManager:
    """Manages dynamic configuration for the traffic control system."""
    
    def __init__(self, config_file: str = "traffic_config.json"):
        self.config_file = config_file
        self.traffic_config = TrafficConfig()
        self.optimization_config = OptimizationConfig()
        self.system_config = SystemConfig()
        self.last_modified = 0
        self.load_config()
    
    def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Update configurations
                if 'traffic' in data:
                    self.traffic_config = TrafficConfig(**data['traffic'])
                
                if 'optimization' in data:
                    self.optimization_config = OptimizationConfig(**data['optimization'])
                
                if 'system' in data:
                    self.system_config = SystemConfig(**data['system'])
                
                self.last_modified = os.path.getmtime(self.config_file)
                print(f"Configuration loaded from {self.config_file}")
                return True
            else:
                # Create default configuration file
                self.save_config()
                print(f"Created default configuration file: {self.config_file}")
                return True
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            config_data = {
                'traffic': asdict(self.traffic_config),
                'optimization': asdict(self.optimization_config),
                'system': asdict(self.system_config),
                'last_updated': time.time()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.last_modified = os.path.getmtime(self.config_file)
            print(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def check_for_updates(self) -> bool:
        """Check if configuration file has been updated."""
        if os.path.exists(self.config_file):
            current_modified = os.path.getmtime(self.config_file)
            if current_modified > self.last_modified:
                return self.load_config()
        return False
    
    def get_traffic_config(self) -> TrafficConfig:
        """Get current traffic configuration."""
        return self.traffic_config
    
    def get_optimization_config(self) -> OptimizationConfig:
        """Get current optimization configuration."""
        return self.optimization_config
    
    def get_system_config(self) -> SystemConfig:
        """Get current system configuration."""
        return self.system_config
    
    def update_traffic_config(self, **kwargs) -> bool:
        """Update traffic configuration parameters."""
        try:
            for key, value in kwargs.items():
                if hasattr(self.traffic_config, key):
                    setattr(self.traffic_config, key, value)
                else:
                    print(f"Unknown traffic config parameter: {key}")
            
            return self.save_config()
        except Exception as e:
            print(f"Error updating traffic config: {e}")
            return False
    
    def update_optimization_config(self, **kwargs) -> bool:
        """Update optimization configuration parameters."""
        try:
            for key, value in kwargs.items():
                if hasattr(self.optimization_config, key):
                    setattr(self.optimization_config, key, value)
                else:
                    print(f"Unknown optimization config parameter: {key}")
            
            return self.save_config()
        except Exception as e:
            print(f"Error updating optimization config: {e}")
            return False
    
    def update_system_config(self, **kwargs) -> bool:
        """Update system configuration parameters."""
        try:
            for key, value in kwargs.items():
                if hasattr(self.system_config, key):
                    setattr(self.system_config, key, value)
                else:
                    print(f"Unknown system config parameter: {key}")
            
            return self.save_config()
        except Exception as e:
            print(f"Error updating system config: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return {
            'traffic': asdict(self.traffic_config),
            'optimization': asdict(self.optimization_config),
            'system': asdict(self.system_config),
            'last_modified': self.last_modified
        }
    
    def reset_to_defaults(self) -> bool:
        """Reset all configurations to default values."""
        try:
            self.traffic_config = TrafficConfig()
            self.optimization_config = OptimizationConfig()
            self.system_config = SystemConfig()
            return self.save_config()
        except Exception as e:
            print(f"Error resetting to defaults: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration and return validation results."""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Validate traffic config
        if self.traffic_config.min_green_time >= self.traffic_config.max_green_time:
            validation_results['errors'].append("min_green_time must be less than max_green_time")
            validation_results['valid'] = False
        
        if self.traffic_config.traffic_density_medium_threshold >= self.traffic_config.traffic_density_high_threshold:
            validation_results['errors'].append("medium_threshold must be less than high_threshold")
            validation_results['valid'] = False
        
        # Validate optimization config
        total_weight = (self.optimization_config.wait_time_weight + 
                       self.optimization_config.vehicle_count_weight + 
                       self.optimization_config.emergency_weight)
        
        if abs(total_weight - 1.0) > 0.01:
            validation_results['warnings'].append(f"Optimization weights sum to {total_weight:.2f}, should be 1.0")
        
        if self.optimization_config.max_consecutive_green < 1:
            validation_results['errors'].append("max_consecutive_green must be at least 1")
            validation_results['valid'] = False
        
        # Validate system config
        if self.system_config.web_port < 1024 or self.system_config.web_port > 65535:
            validation_results['errors'].append("web_port must be between 1024 and 65535")
            validation_results['valid'] = False
        
        if self.system_config.max_intersections < 1:
            validation_results['errors'].append("max_intersections must be at least 1")
            validation_results['valid'] = False
        
        return validation_results


# Global configuration manager instance
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager


if __name__ == "__main__":
    # Test the configuration manager
    print("🔧 Testing Configuration Manager")
    print("="*40)
    
    manager = ConfigManager("test_config.json")
    
    # Test loading and saving
    print("1. Testing configuration loading...")
    manager.load_config()
    
    print("2. Testing configuration update...")
    manager.update_traffic_config(min_green_time=20, max_green_time=100)
    
    print("3. Testing configuration validation...")
    validation = manager.validate_config()
    print(f"   Valid: {validation['valid']}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    if validation['errors']:
        print(f"   Errors: {validation['errors']}")
    
    print("4. Testing configuration retrieval...")
    all_config = manager.get_all_config()
    print(f"   Traffic config keys: {list(all_config['traffic'].keys())}")
    print(f"   Optimization config keys: {list(all_config['optimization'].keys())}")
    print(f"   System config keys: {list(all_config['system'].keys())}")
    
    print("✅ Configuration manager test completed!")
    
    # Clean up test file
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
        print("🧹 Test configuration file cleaned up")
