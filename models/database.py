"""
Database models for storing GPS data and traffic incidents.
"""

from flask_sqlalchemy import SQLAlchemy
import time

# Initialize database
db = SQLAlchemy()


class GPSData(db.Model):
    """Model for storing vehicle GPS data."""
    
    __tablename__ = 'gps_data'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.String(50), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.Integer, default=lambda: int(time.time()), index=True)
    
    def __repr__(self):
        return f'<GPSData {self.vehicle_id}: ({self.latitude}, {self.longitude}) at {self.timestamp}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed': self.speed,
            'timestamp': self.timestamp
        }


class Incident(db.Model):
    """Model for storing traffic incidents."""
    
    __tablename__ = 'incidents'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_type = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), default='Medium')  # Low, Medium, High, Critical
    status = db.Column(db.String(20), default='Active')  # Active, Resolved, False Alarm
    timestamp = db.Column(db.Integer, default=lambda: int(time.time()), index=True)
    resolved_at = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f'<Incident {self.incident_type} at ({self.latitude}, {self.longitude})>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'incident_type': self.incident_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'description': self.description,
            'severity': self.severity,
            'status': self.status,
            'timestamp': self.timestamp,
            'resolved_at': self.resolved_at
        }
    
    def resolve(self):
        """Mark incident as resolved."""
        self.status = 'Resolved'
        self.resolved_at = int(time.time())
