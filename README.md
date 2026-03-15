# Smart Traffic Light Controller

A sophisticated traffic light control system that optimizes signal timing across multiple intersections to minimize total wait time while maintaining fairness and safety.

## Features

- **Multi-Intersection Support**: Handle any number of intersecting roads
- **Real-time Vehicle Detection**: Uses OpenCV for camera-based vehicle counting
- **Emergency Vehicle Detection**: Automatically detects emergency vehicle flashers
- **Traffic Optimization Algorithm**: Minimizes total wait time across all intersections
- **Fairness Controls**: Prevents intersection starvation with configurable fairness parameters
- **Incident Management**: Handle traffic incidents with automatic signal adjustments
- **Web Dashboard**: Real-time monitoring and manual control interface
- **Safety Features**: Proper signal transitions with yellow phases

## Project Structure

```
SmartTrafficController/
├── main.py                 # Main entry point
├── config.py              # Configuration settings
├── models/
│   ├── __init__.py
│   ├── database.py        # Database models (GPS, incidents)
│   └── traffic.py         # Traffic intersection models
├── services/
│   ├── __init__.py
│   ├── camera_input.py    # Camera feed analysis
│   ├── traffic_optimizer.py # Multi-intersection optimization
│   └── signal_controller.py # Traffic light control logic
├── web/
│   ├── __init__.py
│   ├── app.py            # Flask app configuration
│   ├── routes.py         # Web routes and API endpoints
│   └── templates/
│       └── dashboard.html # Web dashboard
├── static/
│   └── css/
│       └── styles.css    # Dashboard styling
├── requirements.txt       # Dependencies
└── README.md             # This file
```

## Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up camera source** (optional):
   ```bash
   # For webcam (default)
   export OPENCV_VIDEO_SOURCE=0
   
   # For video file
   export OPENCV_VIDEO_SOURCE=path/to/video.mp4
   ```

## Usage

### Command Line Interface

Run the main traffic controller:

```bash
python main.py
```

The system will:
1. Ask for the number of intersections
2. Initialize camera feeds for each intersection
3. Start the optimization algorithm
4. Begin real-time traffic monitoring and signal control

### Web Dashboard

Start the web interface:

```bash
python web/app.py
```

Then open your browser to `http://localhost:5000` to access the dashboard.

The dashboard provides:
- Real-time traffic data visualization
- Manual signal control
- Emergency override capabilities
- Incident reporting and monitoring
- System statistics

## API Endpoints

- `GET /api/traffic_data` - Get current traffic data for an intersection
- `GET /api/intersections` - Get data for all intersections
- `POST /api/signal_control/<id>/<signal>` - Manually control a signal
- `POST /api/emergency/<id>` - Trigger emergency override
- `GET/POST /api/incidents` - Report or retrieve traffic incidents
- `GET /api/optimization_stats` - Get optimization statistics

## Configuration

Edit `config.py` to customize:

- **Traffic Light Timing**: Minimum/maximum green times, yellow duration
- **Vehicle Detection**: Detection thresholds and parameters
- **Optimization**: Weights for different factors in the algorithm
- **Fairness**: Maximum consecutive green cycles and fairness windows

## Key Components

### Traffic Optimizer
Implements a sophisticated algorithm that:
- Calculates priority scores based on vehicle count, wait time, and emergencies
- Applies fairness constraints to prevent intersection starvation
- Optimizes signal timing to minimize total system wait time
- Handles emergency overrides and incident management

### Camera Analyzer
Provides vehicle detection using:
- Background subtraction for motion detection
- Contour analysis for vehicle counting
- Emergency vehicle detection via flashing light analysis
- Fallback mechanisms for camera failures

### Signal Controller
Manages individual traffic signals with:
- Proper state transitions (Red → Yellow → Green)
- Timing constraints and safety checks
- Emergency override capabilities
- Historical tracking for optimization

## Safety Features

- **Proper Transitions**: All signal changes include yellow phases
- **Emergency Overrides**: Immediate priority for emergency vehicles
- **Incident Handling**: Automatic red signals for blocked intersections
- **System Failures**: Graceful degradation when cameras fail
- **Fairness Controls**: Prevents any intersection from being starved

## Development

### Adding New Features

1. **New Detection Methods**: Extend `CameraAnalyzer` class
2. **Optimization Algorithms**: Modify `TrafficOptimizer` class
3. **Signal Types**: Update `SignalController` for new signal states
4. **Web Interface**: Add new routes in `web/routes.py`

### Testing

The system includes built-in testing capabilities:
- Force green/red signals via web interface
- Emergency override testing
- Synthetic data generation when cameras unavailable

## Troubleshooting

### Common Issues

1. **Camera Not Working**: Check `OPENCV_VIDEO_SOURCE` environment variable
2. **Database Errors**: Ensure `instance/` directory exists and is writable
3. **Port Conflicts**: Change port in `web/app.py` if 5000 is occupied

### Debug Mode

Run with debug information:
```bash
export FLASK_DEBUG=1
python web/app.py
```

## License

This project is provided as-is for educational and development purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code comments for implementation details
3. Test with the built-in simulation modes
