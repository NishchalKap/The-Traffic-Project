"""
Database models for the Smart Traffic Light Controller.
"""

from .database import db, GPSData, Incident
from .traffic import TrafficIntersection, TrafficSignal

__all__ = ['db', 'GPSData', 'Incident', 'TrafficIntersection', 'TrafficSignal']