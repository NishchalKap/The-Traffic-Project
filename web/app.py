"""
Flask application configuration for the Smart Traffic Light Controller web interface.
"""

from flask import Flask
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from models.database import db

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize database tables
def create_tables():
    """Create database tables if they don't exist."""
    with app.app_context():
        from models.database import GPSData, Incident
        db.create_all()

# Import routes directly
from flask import render_template, jsonify, request
import time
import random
import threading

# Initialize services
from services.camera_input import CameraAnalyzer
from services.traffic_optimizer import TrafficOptimizer
from services.signal_controller import SignalController

camera_analyzer = CameraAnalyzer()
traffic_optimizer = TrafficOptimizer()
signal_controller = SignalController()

# Coordinated signal cycle configuration (two-phase: Main vs Cross)
COORD_CYCLE = {
    'MAIN_GREEN': 40,   # seconds
    'MAIN_YELLOW': 4,   # seconds
    'CROSS_GREEN': 40,  # seconds
    'CROSS_YELLOW': 4   # seconds
}

def _total_cycle_seconds():
    return sum(COORD_CYCLE.values())

def _intersection_offset_seconds(index_zero_based: int) -> int:
    """Provide a small progression offset per intersection to create a green wave.
    Example: 0s, 3s, 6s, 9s, 12s ...
    """
    progression_step = 3  # seconds between intersections
    return progression_step * index_zero_based

def _phase_at_time(now_seconds: float, offset_seconds: int) -> tuple[str, int]:
    """Return (phase_name, seconds_into_phase) for given time and offset."""
    cycle = _total_cycle_seconds()
    t = int((now_seconds + offset_seconds) % cycle)
    a = COORD_CYCLE['MAIN_GREEN']
    b = a + COORD_CYCLE['MAIN_YELLOW']
    c = b + COORD_CYCLE['CROSS_GREEN']
    d = c + COORD_CYCLE['CROSS_YELLOW']
    if t < a:
        return ('MAIN_GREEN', t)
    if t < b:
        return ('MAIN_YELLOW', t - a)
    if t < c:
        return ('CROSS_GREEN', t - b)
    # t < d
    return ('CROSS_YELLOW', t - c)

def _remaining_in_phase(now_seconds: float, offset_seconds: int, phase_name: str, seconds_into_phase: int) -> int:
    phase_length = COORD_CYCLE[phase_name]
    return max(0, phase_length - seconds_into_phase)

def get_coordinated_target(intersection_id: str, intersections_count: int) -> dict:
    """Compute coordinated target signal and duration for an intersection.
    Returns dict: { signal, duration, reason }
    """
    try:
        # Determine index for offset (intersection_1 -> 0, etc.)
        try:
            idx = int(intersection_id.split('_')[-1]) - 1
        except Exception:
            idx = 0
        offset = _intersection_offset_seconds(idx)
        now_s = time.time()
        phase, into = _phase_at_time(now_s, offset)
        remaining = _remaining_in_phase(now_s, offset, phase, into)

        # Map phases to facing approach signal. We expose a single-head signal in UI, so
        # treat MAIN phases as Green/Yellow; CROSS phases as Red (during Main) and Green/Yellow during Cross.
        if phase == 'MAIN_GREEN':
            return { 'signal': 'Green', 'duration': remaining, 'reason': 'Coordinated main green' }
        if phase == 'MAIN_YELLOW':
            return { 'signal': 'Yellow', 'duration': remaining, 'reason': 'Coordinated main yellow' }
        if phase == 'CROSS_GREEN':
            return { 'signal': 'Red', 'duration': remaining, 'reason': 'Cross street green (red here)' }
        # CROSS_YELLOW
        return { 'signal': 'Red', 'duration': remaining, 'reason': 'Cross street yellow (red here)' }
    except Exception:
        # Fallback
        return { 'signal': 'Red', 'duration': 30, 'reason': 'Coordinator fallback' }

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

# Routes
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
    """Get current traffic data for all intersections."""
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
        latest_incident = None
        incident_report = None
        is_incident = False
        
        try:
            latest_incident = Incident.query.order_by(Incident.timestamp.desc()).first()
            if latest_incident:
                is_incident = True
                incident_report = {
                    "type": latest_incident.incident_type,
                    "location": f"{latest_incident.latitude}, {latest_incident.longitude}",
                    "description": latest_incident.description,
                    "severity": latest_incident.severity,
                    "status": latest_incident.status
                }
        except Exception as e:
            print(f"Error getting incident: {e}")
        
        # Create traffic analysis data
        traffic_analysis_data = [{
            'intersection_id': intersection_id,
            'vehicle_count': camera_data['vehicle_count'],
            'density': camera_data['density'],
            'wait_time': 0,  # Placeholder
            'emergency': camera_data['emergency'],
            'incident_present': is_incident
        }]
        
        # Coordinated scheduler with emergency preemption
        try:
            # Emergency preemption: if emergency at this intersection, force Green with a short yellow handoff
            emergency_active = simulation_state['emergency_states'].get(intersection_id, False) or camera_data.get('emergency', False)
            if emergency_active:
                # Immediately provide a protected green; UI shows transitioning when switching
                final_signal_state = {
                    'signal': 'Green',
                    'duration': 20,
                    'reason': 'Emergency preemption',
                    'in_transition': True
                }
            else:
                # Compute coordinated target
                coordinated = get_coordinated_target(intersection_id, simulation_state['intersections'])
                # Apply to controller to respect safe transitions (Yellow, etc.)
                signal_controller.update_signal(
                    intersection_id=intersection_id,
                    target_signal=coordinated['signal'],
                    duration=coordinated['duration'],
                    reason=coordinated['reason']
                )
                final_signal_state = signal_controller.get_signal_state(intersection_id)
        except Exception as e:
            print(f"Error in coordinated scheduler: {e}")
            final_signal_state = {
                'signal': 'Red',
                'duration': 30,
                'reason': 'Coordinator fallback',
                'in_transition': False
            }
        
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
        print(f"Error in traffic_data API: {e}")
        # Return fallback data
        return jsonify({
            "vehicle_count": 5,
            "density": "Medium",
            "traffic_light": {
                "signal": "Red",
                "duration": 30,
                "reason": "Error fallback",
                "transition": False
            },
            "emergency": False,
            "latest_incident": None,
            "intersection_id": intersection_id,
            "timestamp": time.time(),
            "error": str(e)
        })

@app.route('/api/optimization_stats')
def get_optimization_stats():
    """Get optimization statistics."""
    try:
        return jsonify({
            "uptime": time.time() - start_time if 'start_time' in globals() else 0,
            "optimization_count": 0,  # Placeholder
            "error_count": 0,  # Placeholder
            "active_intersections": simulation_state['intersections'],
            "simulation_active": simulation_state['active']
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

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
