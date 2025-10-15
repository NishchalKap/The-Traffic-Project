# 🚦 Smart Traffic Light Controller

A sophisticated, modular traffic management system that dynamically optimizes traffic light timing across multiple intersections to minimize wait times, prevent congestion, and improve overall traffic flow.

## ✨ Key Features

### 🎯 **Core Functionality**
- **Multi-Intersection Support**: Handle and coordinate any number of intersections simultaneously
- **Dynamic Optimization**: Real-time signal timing optimization based on traffic conditions
- **Emergency Vehicle Detection**: Automatic detection and priority handling for emergency vehicles
- **Fairness Controls**: Prevents intersection starvation with intelligent fairness algorithms
- **Safety Measures**: Proper yellow light transitions for all signal changes

### 🔧 **Advanced Capabilities**
- **Real-time Monitoring**: Comprehensive web dashboard with live metrics
- **Performance Analytics**: Detailed system performance tracking and alerting
- **Configuration Management**: Dynamic configuration updates without system restart
- **Robust Error Handling**: Graceful degradation and fallback mechanisms
- **Comprehensive Testing**: Full test suite with unit and integration tests

### 🌐 **Web Interface**
- **Live Dashboard**: Real-time traffic metrics and signal status
- **Manual Controls**: Override signals for emergency situations
- **Incident Reporting**: Track and manage traffic incidents
- **System Statistics**: Performance metrics and optimization statistics

## 🏗️ Architecture

The system is built with a modular architecture for maintainability and scalability:

```
Smart Traffic Light Controller/
├── main.py                 # Main orchestrator and entry point
├── config.py              # Configuration settings
├── config_manager.py      # Dynamic configuration management
├── monitoring.py          # System monitoring and alerting
├── test_traffic_system.py # Comprehensive test suite
├── models/
│   ├── traffic.py         # Traffic intersection models
│   └── database.py        # Database models for incidents
├── services/
│   ├── camera_input.py    # Camera analysis and vehicle detection
│   ├── signal_controller.py # Signal state management
│   └── traffic_optimizer.py # Core optimization algorithms
└── web/
    ├── app.py            # Flask web application
    ├── routes.py         # API endpoints
    ├── templates/
    │   └── dashboard.html # Web dashboard
    └── static/css/
        └── styles.css    # Dashboard styling
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- OpenCV for camera processing
- Flask for web interface

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TrafficProject
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the system**
   ```bash
   python main.py
   ```

4. **Access the web dashboard**
   Open your browser and navigate to `http://localhost:5000`

### Configuration

The system uses a hierarchical configuration system:

1. **Default Configuration** (`config.py`): Base settings
2. **Dynamic Configuration** (`config_manager.py`): Runtime adjustments
3. **Environment Variables**: Override specific settings

Example configuration file (`traffic_config.json`):
```json
{
  "traffic": {
    "optimization_interval": 5,
    "camera_analysis_interval": 2,
    "min_green_time": 15,
    "max_green_time": 90,
    "yellow_time": 3
  },
  "optimization": {
    "wait_time_weight": 0.4,
    "vehicle_count_weight": 0.3,
    "emergency_weight": 0.3,
    "max_consecutive_green": 3
  },
  "system": {
    "log_level": "INFO",
    "enable_web_interface": true,
    "web_port": 5000
  }
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_traffic_system.py
```

The test suite includes:
- Unit tests for all components
- Integration tests for system workflows
- Performance tests for optimization algorithms
- Error handling and edge case testing

## 📊 Monitoring and Alerting

The system includes comprehensive monitoring capabilities:

### Performance Metrics
- Optimization cycle timing
- Camera analysis performance
- Signal change frequency
- System resource usage
- Error rates and patterns

### Alert System
- **INFO**: General system events
- **WARNING**: Performance issues, high resource usage
- **ERROR**: System errors, optimization failures
- **CRITICAL**: System failures, safety issues

### Monitoring Dashboard
Access real-time monitoring at `http://localhost:5000`:
- Live traffic metrics
- Signal status and countdown timers
- Emergency vehicle alerts
- Incident reports
- System performance statistics

## 🔧 API Endpoints

The system provides RESTful API endpoints for integration:

### Traffic Data
- `GET /api/traffic_data` - Get current traffic data for an intersection
- `GET /api/intersections` - Get data for all intersections

### Signal Control
- `GET /api/signal_control/<intersection_id>/<signal>` - Manually control signals
- `GET /api/emergency/<intersection_id>` - Trigger emergency override

### Incidents
- `GET /api/incidents` - Get incident reports
- `POST /api/incidents` - Report new incidents

### System Status
- `GET /api/optimization_stats` - Get optimization statistics

## 🎛️ Manual Controls

The web dashboard provides manual control capabilities:

- **Force Green**: Override to green signal
- **Force Red**: Override to red signal
- **Force Yellow**: Override to yellow signal
- **Emergency Override**: Priority for emergency vehicles
- **System Reset**: Reset to safe state

## 🔍 Troubleshooting

### Common Issues

1. **Camera not working**
   - Check camera permissions
   - Verify OpenCV installation
   - System will use fallback data

2. **High CPU usage**
   - Reduce optimization frequency
   - Check camera analysis settings
   - Monitor system alerts

3. **Web dashboard not loading**
   - Check Flask installation
   - Verify port 5000 is available
   - Check firewall settings

### Logs

System logs are written to:
- Console output (real-time)
- `traffic_controller.log` (file logging)

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenCV for computer vision capabilities
- Flask for web framework
- The traffic engineering community for optimization algorithms

## 📞 Support

For support and questions:
- Check the troubleshooting section
- Review system logs
- Open an issue on GitHub

---

**Note**: This system is designed for educational and research purposes. For production use in real traffic systems, additional safety certifications and regulatory compliance may be required.