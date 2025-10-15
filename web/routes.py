"""
Web routes and API endpoints for the Smart Traffic Light Controller.

This module provides REST API endpoints for monitoring and controlling the traffic system,
as well as serving the web dashboard.
"""

from flask import render_template, jsonify, request, current_app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import db
from models.database import Incident
from services.camera_input import CameraAnalyzer
from services.traffic_optimizer import TrafficOptimizer
from services.signal_controller import SignalController
import time
import random
import threading

# Initialize services
camera_analyzer = CameraAnalyzer()
traffic_optimizer = TrafficOptimizer()
signal_controller = SignalController()

# Get the Flask app instance
def get_app():
    from web.app import app
    return app

app = get_app()

# Simulation state
simulation_state = {
    'active': False,
    'intersections': 3,
    'vehicle_counts': {},
    'emergency_states': {},
    'traffic_scenarios': {},
    'simulation_thread': None
}

# Predefined traffic scenarios
TRAFFIC_SCENARIOS = {
    'rush_hour': {
        'name': 'Rush Hour',
        'description': 'High traffic during peak hours',
        'vehicle_counts': {'intersection_1': 45, 'intersection_2': 38, 'intersection_3': 42},
        'emergency_probability': 0.05
    },
    'light_traffic': {
        'name': 'Light Traffic',
        'description': 'Low traffic during off-peak hours',
        'vehicle_counts': {'intersection_1': 8, 'intersection_2': 5, 'intersection_3': 12},
        'emergency_probability': 0.01
    },
    'emergency_heavy': {
        'name': 'Emergency Heavy',
        'description': 'High traffic with frequent emergency vehicles',
        'vehicle_counts': {'intersection_1': 35, 'intersection_2': 28, 'intersection_3': 32},
        'emergency_probability': 0.15
    },
    'congestion': {
        'name': 'Traffic Congestion',
        'description': 'Severe congestion with long wait times',
        'vehicle_counts': {'intersection_1': 60, 'intersection_2': 55, 'intersection_3': 58},
        'emergency_probability': 0.08
    },
    'night_time': {
        'name': 'Night Time',
        'description': 'Very light traffic during night hours',
        'vehicle_counts': {'intersection_1': 3, 'intersection_2': 2, 'intersection_3': 4},
        'emergency_probability': 0.02
    }
}


def simulation_worker():
    """Background worker for traffic simulation."""
    while simulation_state['active']:
        try:
            # Update vehicle counts based on simulation
            for i in range(1, simulation_state['intersections'] + 1):
                intersection_id = f"intersection_{i}"
                
                # Get base vehicle count from scenario or manual setting
                base_count = simulation_state['vehicle_counts'].get(intersection_id, 0)
                
                # Add some randomness to make it more realistic
                variation = random.randint(-3, 3)
                vehicle_count = max(0, base_count + variation)
                
                # Update emergency state
                emergency = simulation_state['emergency_states'].get(intersection_id, False)
                
                # Simulate emergency vehicle appearance
                if random.random() < 0.02:  # 2% chance per cycle
                    simulation_state['emergency_states'][intersection_id] = True
                    emergency = True
                elif emergency and random.random() < 0.1:  # 10% chance to clear emergency
                    simulation_state['emergency_states'][intersection_id] = False
                    emergency = False
                
                # Update the camera analyzer with simulated data
                camera_analyzer.detection_history[intersection_id] = [{
                    'vehicle_count': vehicle_count,
                    'density': 'High' if vehicle_count >= 30 else 'Medium' if vehicle_count >= 15 else 'Low',
                    'emergency': emergency,
                    'timestamp': time.time()
                }]
            
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            print(f"Simulation error: {e}")
            time.sleep(5)


@app.route('/')
def index():
    """Serve the main dashboard."""
    return render_template('dashboard.html')


@app.route('/simulation')
def simulation_dashboard():
    """Serve the simulation dashboard."""
    return render_template('simulation_dashboard.html')


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
        
        # This part simulates the optimization logic for the dashboard view
        traffic_analysis_data = [{
            'intersection_id': intersection_id,
            'vehicle_count': camera_data['vehicle_count'],
            'density': camera_data['density'],
            'wait_time': 0, # Placeholder, true wait time is calculated in the main thread
            'emergency': camera_data['emergency'],
            'incident_present': is_incident
        }]
        
        # Use the optimizer to get a signal suggestion
        optimized_signals = traffic_optimizer.optimize_traffic_signals(traffic_analysis_data)
        
        if not optimized_signals:
            return jsonify({"error": "No optimized signals generated"}), 500
        
        optimized_signal_data = optimized_signals[0]
        
        # Apply the signal change via the signal controller
        signal_result = signal_controller.update_signal(
            intersection_id=intersection_id,
            target_signal=optimized_signal_data['signal'],
            duration=optimized_signal_data['duration'],
            reason=optimized_signal_data['reason']
        )
        
        # Get the actual current state after the update (could be Yellow during transition)
        final_signal_state = signal_controller.get_signal_state(intersection_id)
        
        return jsonify({
            "vehicle_count": camera_data['vehicle_count'],
            "density": camera_data['density'],
            "traffic_light": {
                "signal": final_signal_state['signal'],
                "duration": final_signal_state['duration'],
                "reason": final_signal_state['reason'],
                "transition": final_signal_state['in_transition']
            },
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
        # Define mock intersection IDs as the main controller would manage these
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


@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    """Start traffic simulation."""
    try:
        data = request.get_json()
        num_intersections = data.get('intersections', 3)
        
        # Initialize simulation state
        simulation_state['intersections'] = num_intersections
        simulation_state['vehicle_counts'] = {f"intersection_{i}": 0 for i in range(1, num_intersections + 1)}
        simulation_state['emergency_states'] = {f"intersection_{i}": False for i in range(1, num_intersections + 1)}
        
        # Start simulation thread
        if not simulation_state['active']:
            simulation_state['active'] = True
            simulation_state['simulation_thread'] = threading.Thread(target=simulation_worker, daemon=True)
            simulation_state['simulation_thread'].start()
        
        return jsonify({
            "success": True,
            "message": f"Simulation started with {num_intersections} intersections",
            "intersections": num_intersections
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    """Stop traffic simulation."""
    try:
        simulation_state['active'] = False
        return jsonify({
            "success": True,
            "message": "Simulation stopped"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation/status')
def get_simulation_status():
    """Get simulation status."""
    return jsonify({
        "active": simulation_state['active'],
        "intersections": simulation_state['intersections'],
        "vehicle_counts": simulation_state['vehicle_counts'],
        "emergency_states": simulation_state['emergency_states']
    })


@app.route('/api/simulation/scenarios')
def get_traffic_scenarios():
    """Get available traffic scenarios."""
    return jsonify({
        "scenarios": TRAFFIC_SCENARIOS
    })


@app.route('/api/simulation/load_scenario', methods=['POST'])
def load_traffic_scenario():
    """Load a predefined traffic scenario."""
    try:
        data = request.get_json()
        scenario_id = data.get('scenario_id')
        
        if scenario_id not in TRAFFIC_SCENARIOS:
            return jsonify({"error": "Invalid scenario ID"}), 400
        
        scenario = TRAFFIC_SCENARIOS[scenario_id]
        
        # Update vehicle counts
        for intersection_id, count in scenario['vehicle_counts'].items():
            simulation_state['vehicle_counts'][intersection_id] = count
        
        return jsonify({
            "success": True,
            "message": f"Loaded scenario: {scenario['name']}",
            "scenario": scenario
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation/set_vehicles', methods=['POST'])
def set_vehicle_count():
    """Set vehicle count for a specific intersection."""
    try:
        data = request.get_json()
        intersection_id = data.get('intersection_id')
        vehicle_count = data.get('vehicle_count', 0)
        
        if intersection_id:
            simulation_state['vehicle_counts'][intersection_id] = max(0, vehicle_count)
        
        return jsonify({
            "success": True,
            "message": f"Set {intersection_id} to {vehicle_count} vehicles"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation/trigger_emergency', methods=['POST'])
def trigger_emergency():
    """Trigger emergency vehicle at a specific intersection."""
    try:
        data = request.get_json()
        intersection_id = data.get('intersection_id')
        emergency_type = data.get('type', 'Emergency Vehicle')
        
        if intersection_id:
            simulation_state['emergency_states'][intersection_id] = True
            
            # Also trigger emergency override in signal controller
            signal_controller.emergency_override(intersection_id, emergency_type)
        
        return jsonify({
            "success": True,
            "message": f"Emergency triggered at {intersection_id}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation/clear_emergency', methods=['POST'])
def clear_emergency():
    """Clear emergency state at a specific intersection."""
    try:
        data = request.get_json()
        intersection_id = data.get('intersection_id')
        
        if intersection_id:
            simulation_state['emergency_states'][intersection_id] = False
        
        return jsonify({
            "success": True,
            "message": f"Emergency cleared at {intersection_id}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500
