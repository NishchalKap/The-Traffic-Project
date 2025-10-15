#!/usr/bin/env python3
"""
Monitoring and alerting system for the Smart Traffic Light Controller.

This module provides real-time monitoring, performance metrics, and alerting
capabilities for the traffic control system.
"""

import time
import threading
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import logging


@dataclass
class Alert:
    """Represents a system alert."""
    alert_id: str
    level: str  # INFO, WARNING, ERROR, CRITICAL
    category: str  # SYSTEM, TRAFFIC, CAMERA, OPTIMIZATION, SIGNAL
    message: str
    timestamp: float
    intersection_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for the system."""
    timestamp: float
    optimization_count: int
    error_count: int
    average_optimization_time: float
    camera_analysis_time: float
    signal_change_count: int
    emergency_count: int
    system_uptime: float
    memory_usage: float
    cpu_usage: float


class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts = deque(maxlen=max_alerts)
        self.alert_handlers = []
        self.alert_counters = defaultdict(int)
        self.alert_thresholds = {
            'ERROR': 10,  # Max errors per minute
            'WARNING': 50,  # Max warnings per minute
            'CRITICAL': 1   # Max critical alerts per minute
        }
        self.rate_limiting = defaultdict(list)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def create_alert(self, level: str, category: str, message: str, 
                    intersection_id: Optional[str] = None, 
                    data: Optional[Dict[str, Any]] = None) -> Alert:
        """Create a new alert."""
        alert_id = f"{category}_{int(time.time() * 1000)}"
        alert = Alert(
            alert_id=alert_id,
            level=level,
            category=category,
            message=message,
            timestamp=time.time(),
            intersection_id=intersection_id,
            data=data
        )
        
        # Check rate limiting
        if self._is_rate_limited(level):
            return None
        
        # Add to alerts list
        self.alerts.append(alert)
        self.alert_counters[level] += 1
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logging.error(f"Error in alert handler: {e}")
        
        return alert
    
    def _is_rate_limited(self, level: str) -> bool:
        """Check if alert level is rate limited."""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean old entries
        self.rate_limiting[level] = [
            timestamp for timestamp in self.rate_limiting[level] 
            if timestamp > minute_ago
        ]
        
        # Check threshold
        if len(self.rate_limiting[level]) >= self.alert_thresholds.get(level, 10):
            return True
        
        # Add current timestamp
        self.rate_limiting[level].append(current_time)
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts if not alert.resolve]
    
    def get_alerts_by_level(self, level: str) -> List[Alert]:
        """Get alerts by level."""
        return [alert for alert in self.alerts if alert.level == level]
    
    def get_alerts_by_category(self, category: str) -> List[Alert]:
        """Get alerts by category."""
        return [alert for alert in self.alerts if alert.category == category]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert by ID."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = time.time()
                return True
        return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())
        
        level_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for alert in self.alerts:
            level_counts[alert.level] += 1
            category_counts[alert.category] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'level_counts': dict(level_counts),
            'category_counts': dict(category_counts),
            'alert_counters': dict(self.alert_counters)
        }


class PerformanceMonitor:
    """Monitors system performance metrics."""
    
    def __init__(self, max_metrics: int = 1000):
        self.metrics = deque(maxlen=max_metrics)
        self.optimization_times = deque(maxlen=100)
        self.camera_analysis_times = deque(maxlen=100)
        self.start_time = time.time()
        self.optimization_count = 0
        self.error_count = 0
        self.signal_change_count = 0
        self.emergency_count = 0
    
    def record_optimization(self, duration: float):
        """Record optimization performance."""
        self.optimization_times.append(duration)
        self.optimization_count += 1
    
    def record_camera_analysis(self, duration: float):
        """Record camera analysis performance."""
        self.camera_analysis_times.append(duration)
    
    def record_signal_change(self):
        """Record a signal change."""
        self.signal_change_count += 1
    
    def record_emergency(self):
        """Record an emergency event."""
        self.emergency_count += 1
    
    def record_error(self):
        """Record an error."""
        self.error_count += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        current_time = time.time()
        
        # Calculate average optimization time
        avg_optimization_time = (
            sum(self.optimization_times) / len(self.optimization_times)
            if self.optimization_times else 0.0
        )
        
        # Calculate average camera analysis time
        avg_camera_time = (
            sum(self.camera_analysis_times) / len(self.camera_analysis_times)
            if self.camera_analysis_times else 0.0
        )
        
        # Get system resource usage (simplified)
        import psutil
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent()
        
        metrics = PerformanceMetrics(
            timestamp=current_time,
            optimization_count=self.optimization_count,
            error_count=self.error_count,
            average_optimization_time=avg_optimization_time,
            camera_analysis_time=avg_camera_time,
            signal_change_count=self.signal_change_count,
            emergency_count=self.emergency_count,
            system_uptime=current_time - self.start_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )
        
        self.metrics.append(metrics)
        return metrics
    
    def get_metrics_history(self, limit: int = 100) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        return list(self.metrics)[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.metrics:
            return {}
        
        recent_metrics = list(self.metrics)[-10:]  # Last 10 measurements
        
        avg_optimization_time = sum(m.average_optimization_time for m in recent_metrics) / len(recent_metrics)
        avg_camera_time = sum(m.camera_analysis_time for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        
        return {
            'total_optimizations': self.optimization_count,
            'total_errors': self.error_count,
            'total_signal_changes': self.signal_change_count,
            'total_emergencies': self.emergency_count,
            'average_optimization_time': avg_optimization_time,
            'average_camera_analysis_time': avg_camera_time,
            'average_memory_usage': avg_memory,
            'average_cpu_usage': avg_cpu,
            'system_uptime': time.time() - self.start_time
        }


class SystemMonitor:
    """Main system monitoring class."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.performance_monitor = PerformanceMonitor()
        self.monitoring_active = False
        self.monitoring_thread = None
        self.intersection_states = {}
        self.last_health_check = time.time()
        
        # Set up default alert handlers
        self.alert_manager.add_alert_handler(self._log_alert)
        self.alert_manager.add_alert_handler(self._console_alert)
    
    def start_monitoring(self):
        """Start the monitoring system."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.alert_manager.create_alert(
            "INFO", "SYSTEM", "System monitoring started"
        )
    
    def stop_monitoring(self):
        """Stop the monitoring system."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.alert_manager.create_alert(
            "INFO", "SYSTEM", "System monitoring stopped"
        )
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._health_check()
                self._performance_check()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.alert_manager.create_alert(
                    "ERROR", "SYSTEM", f"Monitoring loop error: {e}"
                )
    
    def _health_check(self):
        """Perform system health check."""
        current_time = time.time()
        
        # Check if system is responsive
        if current_time - self.last_health_check > 60:
            self.alert_manager.create_alert(
                "WARNING", "SYSTEM", "System health check overdue"
            )
        
        self.last_health_check = current_time
    
    def _performance_check(self):
        """Check system performance metrics."""
        metrics = self.performance_monitor.get_current_metrics()
        
        # Check memory usage
        if metrics.memory_usage > 90:
            self.alert_manager.create_alert(
                "WARNING", "SYSTEM", f"High memory usage: {metrics.memory_usage:.1f}%"
            )
        
        # Check CPU usage
        if metrics.cpu_usage > 80:
            self.alert_manager.create_alert(
                "WARNING", "SYSTEM", f"High CPU usage: {metrics.cpu_usage:.1f}%"
            )
        
        # Check error rate
        if metrics.error_count > 10:
            self.alert_manager.create_alert(
                "ERROR", "SYSTEM", f"High error count: {metrics.error_count}"
            )
    
    def _log_alert(self, alert: Alert):
        """Log alert to file."""
        logging.info(f"ALERT [{alert.level}] {alert.category}: {alert.message}")
    
    def _console_alert(self, alert: Alert):
        """Print alert to console."""
        if alert.level in ["ERROR", "CRITICAL"]:
            print(f"🚨 {alert.level}: {alert.message}")
        elif alert.level == "WARNING":
            print(f"⚠️  WARNING: {alert.message}")
        else:
            print(f"ℹ️  INFO: {alert.message}")
    
    def update_intersection_state(self, intersection_id: str, state: Dict[str, Any]):
        """Update intersection state for monitoring."""
        self.intersection_states[intersection_id] = {
            **state,
            'last_update': time.time()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'monitoring_active': self.monitoring_active,
            'performance_metrics': self.performance_monitor.get_current_metrics(),
            'alert_statistics': self.alert_manager.get_alert_statistics(),
            'intersection_states': self.intersection_states,
            'last_health_check': self.last_health_check
        }
    
    def get_alerts(self, level: Optional[str] = None, 
                  category: Optional[str] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = list(self.alert_manager.alerts)
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        return alerts


# Global monitoring instance
system_monitor = SystemMonitor()


def get_system_monitor() -> SystemMonitor:
    """Get the global system monitor instance."""
    return system_monitor


if __name__ == "__main__":
    # Test the monitoring system
    print("📊 Testing System Monitor")
    print("="*40)
    
    monitor = SystemMonitor()
    
    # Start monitoring
    print("1. Starting monitoring...")
    monitor.start_monitoring()
    
    # Create some test alerts
    print("2. Creating test alerts...")
    monitor.alert_manager.create_alert("INFO", "TRAFFIC", "Test traffic alert")
    monitor.alert_manager.create_alert("WARNING", "CAMERA", "Camera connection lost")
    monitor.alert_manager.create_alert("ERROR", "OPTIMIZATION", "Optimization failed")
    
    # Record some performance metrics
    print("3. Recording performance metrics...")
    monitor.performance_monitor.record_optimization(0.5)
    monitor.performance_monitor.record_camera_analysis(0.2)
    monitor.performance_monitor.record_signal_change()
    
    # Get system status
    print("4. Getting system status...")
    status = monitor.get_system_status()
    print(f"   Monitoring active: {status['monitoring_active']}")
    print(f"   Total optimizations: {status['performance_metrics'].optimization_count}")
    print(f"   Total alerts: {status['alert_statistics']['total_alerts']}")
    
    # Get alerts
    print("5. Getting alerts...")
    alerts = monitor.get_alerts()
    print(f"   Total alerts: {len(alerts)}")
    for alert in alerts[-3:]:  # Show last 3
        print(f"   - {alert.level}: {alert.message}")
    
    # Stop monitoring
    print("6. Stopping monitoring...")
    monitor.stop_monitoring()
    
    print("✅ System monitor test completed!")
