import os
import csv
from datetime import datetime
from pathlib import Path

from .schema import Action, ActionEnum, State, ImuData, ChassisFeedback

class UGVLogger:
    """Handles logging of UGV data and images"""
    
    def __init__(self):
        """Initialize the logger with paths"""
        # Create base directory ~/.ugv_cam/
        self.base_dir = Path.home() / '.ugv_cam'
        
        # Create session directory with timestamp
        session_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = self.base_dir / session_time
        self.data_dir = self.session_dir / 'data'
        
        # Create directories
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup CSV log file
        self.log_file = self.session_dir / 'logs.csv'
        self.setup_csv()
        
        print(f"Logging data to: {self.session_dir}")
    
    def setup_csv(self):
        """Create CSV file with headers"""
        headers = [
            'timestamp',
            'image_path',
            'left_speed',
            'right_speed',
            'roll',
            'pitch',
            'voltage',
            'temperature',
            'accel_x',
            'accel_y',
            'accel_z',
            'gyro_x',
            'gyro_y',
            'gyro_z'
        ]
        
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def log_state(self, state: State, left_speed: float, right_speed: float):
        """Log current state and control inputs"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
        # Save image if present
        image_path = None
        if state.image is not None:
            image_path = self.data_dir / f"{timestamp}.jpg"
            with open(image_path, 'wb') as f:
                f.write(state.image)
            image_path = str(image_path.relative_to(self.session_dir))
        
        # Prepare row data
        row_data = [
            timestamp,
            image_path,
            f"{left_speed:.3f}",
            f"{right_speed:.3f}",
            f"{state.sensors.r:.3f}" if state.sensors else "",
            f"{state.sensors.p:.3f}" if state.sensors else "",
            f"{state.feedback.v:.3f}" if state.feedback else "",
            f"{state.sensors.temp:.2f}" if state.sensors and state.sensors.temp else "",
            f"{state.sensors.ax:.3f}" if state.sensors and state.sensors.ax is not None else "",
            f"{state.sensors.ay:.3f}" if state.sensors and state.sensors.ay is not None else "",
            f"{state.sensors.az:.3f}" if state.sensors and state.sensors.az is not None else "",
            f"{state.sensors.gx:.3f}" if state.sensors and state.sensors.gx is not None else "",
            f"{state.sensors.gy:.3f}" if state.sensors and state.sensors.gy is not None else "",
            f"{state.sensors.gz:.3f}" if state.sensors and state.sensors.gz is not None else ""
        ]
        
        # Write to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)