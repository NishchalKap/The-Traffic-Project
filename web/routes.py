"""
Web routes and API endpoints for the Smart Traffic Light Controller.

This module provides REST API endpoints for monitoring and controlling the traffic system,
as well as serving the web dashboard.
"""

from flask import render_template, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import db
from models.database import Incident
from services.camera_input import CameraAnalyzer
from services.traffic_optimizer import TrafficOptimizer
from services.signal_controller import SignalController
import time

# Initialize services
camera_analyzer = CameraAnalyzer()
traffic_optimizer = TrafficOptimizer()
signal_controller = SignalController()


@app.route('/')
def index():
    """Serve the main dashboard."""
    return render_template('dashboard.html')


@app.route('/api/traffic_data')
def get_traffic_data():
    """
    Get current traffic data for all intersections.
    
    Returns:
        JSON response with traffic data, signal states, and incidents
    """
    try:
        # Get testing parameters
        force_emergency = request.args.get('force_emergency', 'false').lower() == 'true'
        force_green = request.args.get('force_green', 'false').lower() == 'true'
        intersection_id = request.args.get('intersection_id', 'intersection_1')
        
        # Analyze camera feed (or use simulated data)
        camera_data = camera_analyzer.analyze_intersection(intersection_id)
        
        # Apply testing overrides
        if force_green:
            camera_data['density'] = 'High'
            camera_data['vehicle_count'] = max(camera_data.get('vehicle_count', 0), 20)
        if force_emergency:
            camera_data['emergency'] = True
        
        # Get latest incident
        latest_incident = Incident.query.order_by(Incident.timestamp.desc()).first()
        incident_report = None
        is_incident = False
        
        if latest_incident:
            is_incident = True
            incident_report = {
                "type": latest_incident.incident_type,
                "location": f"{latest_incident.latitude}, {latest_incident.longitude}",
                "description": latest_incident.description,
                "severity": latest_incident.severity,
                "status": latest_incident.status
            }
        
        # Get current signal state
        signal_state = signal_controller.get_signal_state(intersection_id)
        if not signal_state:
            # Initialize with default state
            signal_state = signal_controller.update_signal(
                intersection_id, "Red", 30, "Initialization"
            )
        
        # Control traffic light based on analysis
        light_signal = control_traffic_light(
            camera_data['density'],
            incident_present=is_incident,
            emergency_present=camera_data.get('emergency', False),
            vehicle_count=camera_data.get('vehicle_count', 0),
            intersection_id=intersection_id
        )
        
        return jsonify({
            "vehicle_count": camera_data['vehicle_count'],
            "density": camera_data['density'],
            "traffic_light": light_signal,
            "emergency": camera_data.get('emergency', False),
            "latest_incident": incident_report,
            "intersection_id": intersection_id,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/intersections')
def get_all_intersections():
    """Get data for all intersections."""
    try:
        # Get all intersection IDs (this would come from the main controller in a real system)
        intersection_ids = ['intersection_1', 'intersection_2', 'intersection_3']
        
        intersections_data = []
        for intersection_id in intersection_ids:
            # Get signal state
            signal_state = signal_controller.get_signal_state(intersection_id)
            if not signal_state:
                signal_state = signal_controller.update_signal(
                    intersection_id, "Red", 30, "Initialization"
                )
            
            # Get traffic analysis
            camera_data = camera_analyzer.analyze_intersection(intersection_id)
            
            intersections_data.append({
                "intersection_id": intersection_id,
                "name": f"Intersection {intersection_id.split('_')[1]}",
                "signal": signal_state,
                "traffic": camera_data
            })
        
        return jsonify({
            "intersections": intersections_data,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/signal_control/<intersection_id>/<signal>')
def control_signal(intersection_id, signal):
    """Manually control a specific signal."""
    try:
        if signal not in ['Red', 'Yellow', 'Green']:
            return jsonify({"error": "Invalid signal color"}), 400
        
        duration = int(request.args.get('duration', 30))
        reason = request.args.get('reason', f'Manual control to {signal}')
        
        result = signal_controller.update_signal(intersection_id, signal, duration, reason)
        
        return jsonify({
            "success": True,
            "signal_control": result,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/emergency/<intersection_id>')
def emergency_override(intersection_id):
    """Trigger emergency override for an intersection."""
    try:
        emergency_type = request.args.get('type', 'Emergency Vehicle')
        
        signal_controller.emergency_override(intersection_id, emergency_type)
        
        return jsonify({
            "success": True,
            "message": f"Emergency override activated for {intersection_id}",
            "emergency_type": emergency_type,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/incidents', methods=['GET', 'POST'])
def handle_incidents():
    """Handle traffic incident reporting and retrieval."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            incident = Incident(
                incident_type=data.get('incident_type'),
                latitude=float(data.get('latitude')),
                longitude=float(data.get('longitude')),
                description=data.get('description'),
                severity=data.get('severity', 'Medium')
            )
            
            db.session.add(incident)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Incident reported successfully",
                "incident_id": incident.id
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    else:  # GET
        try:
            incidents = Incident.query.order_by(Incident.timestamp.desc()).limit(10).all()
            
            incidents_data = []
            for incident in incidents:
                incidents_data.append(incident.to_dict())
            
            return jsonify({
                "incidents": incidents_data,
                "timestamp": time.time()
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/optimization_stats')
def get_optimization_stats():
    """Get traffic optimization statistics."""
    try:
        stats = traffic_optimizer.get_optimization_stats()
        signal_stats = signal_controller.get_signal_statistics()
        
        return jsonify({
            "optimization_stats": stats,
            "signal_stats": signal_stats,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def control_traffic_light(vehicle_density, incident_present=False, emergency_present=False, 
                         vehicle_count=0, intersection_id='intersection_1'):
    """
    Control traffic light based on traffic conditions.
    
    This function implements the traffic light control logic from the original app/logic.py
    but adapted for the new modular structure.
    """
    
    # Emergency vehicle overrides to immediate green
    if emergency_present:
        signal_controller.emergency_override(intersection_id, "Emergency Vehicle")
        return {"signal": "Green", "duration": 90, "reason": "Emergency Vehicle"}
    
    # Incident overrides with solid red
    if incident_present and not emergency_present:
        signal_controller.force_signal(intersection_id, "Red", 120, "Incident Reported")
        return {"signal": "Red", "duration": 120, "reason": "Incident Reported"}
    
    # Normal traffic control
    target = "Green" if vehicle_density in ("High", "Medium") or vehicle_count > 0 else "Red"
    
    # Determine duration based on traffic density
    if target == "Green":
        if vehicle_density == "High":
            duration = 60
        elif vehicle_density == "Medium":
            duration = 40
        else:
            duration = 25
        reason = f"{vehicle_density} Traffic"
    else:
        duration = 15 if vehicle_count == 0 else 5
        reason = f"{vehicle_density} Traffic"
    
    # Update signal
    signal_controller.update_signal(intersection_id, target, duration, reason)
    
    return {"signal": target, "duration": duration, "reason": reason}


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
