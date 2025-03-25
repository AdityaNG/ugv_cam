"""
Playback UGV logs with visualization
"""

import os
import csv
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

import pygame
import cv2
import numpy as np

from .kinematics import predict_trajectory
from .utils import project_trajectory

class UGVPlayback:
    """Visualizes recorded UGV data using PyGame"""
    
    # Display settings
    WINDOW_WIDTH = 640 + 250
    WINDOW_HEIGHT = 480
    SIDEBAR_WIDTH = 250
    VIDEO_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
    VIDEO_AREA_HEIGHT = WINDOW_HEIGHT
    FPS = 30
    
    # Colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (120, 120, 120)
    LIGHT_GRAY = (200, 200, 200)
    BLUE = (50, 100, 255)
    GREEN = (50, 200, 50)
    RED = (255, 50, 50)
    YELLOW = (255, 255, 0)

    def __init__(self, log_dir: str):
        """Initialize playback with path to log directory"""
        pygame.init()
        pygame.font.init()
        
        # Set up the display
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("UGV Log Playback")
        self.clock = pygame.time.Clock()
        
        # Set up fonts
        self.title_font = pygame.font.SysFont('Arial', 24, bold=True)
        self.info_font = pygame.font.SysFont('Arial', 18)
        self.small_font = pygame.font.SysFont('Arial', 14)
        
        # Load log data
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / 'logs.csv'
        self.data = self.load_log_data()
        
        # Playback state
        self.current_frame = 0
        self.is_playing = True
        self.is_running = True
        self.playback_speed = 1.0
        
        # Battery history for visualization
        self.battery_history = []
        self.max_history_points = 100
        
        print(f"Loaded {len(self.data)} frames from {self.log_file}")

    def load_log_data(self):
        """Load data from CSV log file"""
        data = []
        with open(self.log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric strings to floats where possible
                for key in row:
                    try:
                        if row[key] and row[key] != "":
                            row[key] = float(row[key])
                    except ValueError:
                        pass
                data.append(row)
        return data

    def load_image(self, image_path):
        """Load image from file"""
        if not image_path:
            return None
            
        full_path = self.log_dir / image_path
        if not full_path.exists():
            return None
            
        try:
            img = cv2.imread(str(full_path))
            if img is None:
                return None
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None

    def get_future_speeds(self, start_frame: int, duration: float) -> List[Tuple[float, float]]:
        """Get sequence of speed pairs for next 'duration' seconds"""
        fps = 30  # Assuming 30fps data
        n_frames = int(duration * fps)
        speeds = []
        
        for i in range(start_frame, min(start_frame + n_frames, len(self.data))):
            frame = self.data[i]
            left = float(frame.get('left_speed', 0))
            right = float(frame.get('right_speed', 0))
            speeds.append((left, right))
            
        return speeds

    def draw_video_feed(self, image_path):
        """Draw the recorded video frame"""
        img = self.load_image(image_path)
        
        if img is None:
            # Draw placeholder if no image
            video_area = pygame.Rect(0, 0, self.VIDEO_AREA_WIDTH, self.VIDEO_AREA_HEIGHT)
            pygame.draw.rect(self.screen, self.GRAY, video_area)
            no_video_text = self.title_font.render("No Video Frame", True, self.WHITE)
            text_rect = no_video_text.get_rect(center=(self.VIDEO_AREA_WIDTH // 2, self.VIDEO_AREA_HEIGHT // 2))
            self.screen.blit(no_video_text, text_rect)
            return

        try:
            duration = 5.0  # seconds
            dt = 1.0/30.0
            n_steps = round(duration/dt)

            # Get future speeds for next few seconds
            future_speeds = self.get_future_speeds(self.current_frame, duration=duration)
            
            # Predict trajectory
            trajectory = predict_trajectory(future_speeds, dt=dt, n_steps=n_steps)
            
            # Project trajectory onto image
            img = project_trajectory(img, trajectory)

            # Rotate the image 90 degrees counterclockwise
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            img = cv2.flip(img, 0)
            
            # Convert to PyGame surface
            pygame_img = pygame.surfarray.make_surface(img)
            
            # Scale to fit the video area while maintaining aspect ratio
            scale = min(self.VIDEO_AREA_WIDTH / img.shape[1],
                    self.VIDEO_AREA_HEIGHT / img.shape[0])
            
            new_height = int(img.shape[1] * scale)
            new_width = int(img.shape[0] * scale)
            
            pygame_img = pygame.transform.scale(pygame_img, (new_width, new_height))
            
            # Center the image in the video area
            x_offset = (self.VIDEO_AREA_WIDTH - new_width) // 2
            y_offset = (self.VIDEO_AREA_HEIGHT - new_height) // 2
            
            self.screen.blit(pygame_img, (x_offset, y_offset))
            
        except Exception as e:
            print(f"Error displaying video: {e}")
            import traceback
            traceback.print_exc()

    def draw_sidebar(self, frame_data):
        """Draw the sidebar with recorded sensor data"""
        # Draw sidebar background
        sidebar_rect = pygame.Rect(self.VIDEO_AREA_WIDTH, 0, self.SIDEBAR_WIDTH, self.WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, self.LIGHT_GRAY, sidebar_rect)
        
        # Title
        title = self.title_font.render("UGV Playback", True, self.BLACK)
        self.screen.blit(title, (self.VIDEO_AREA_WIDTH + 10, 10))
        
        y_pos = 50
        
        # Playback controls
        controls = f"{'Playing' if self.is_playing else 'Paused'} ({self.playback_speed}x)"
        controls_text = self.info_font.render(controls, True, self.BLACK)
        self.screen.blit(controls_text, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 30
        
        # Frame info
        frame_text = self.info_font.render(f"Frame: {self.current_frame + 1}/{len(self.data)}", True, self.BLACK)
        self.screen.blit(frame_text, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 35
        
        # Speed data
        speed_title = self.info_font.render("Recorded Speed (m/s):", True, self.BLACK)
        self.screen.blit(speed_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        left_speed = frame_data.get('left_speed', 0)
        right_speed = frame_data.get('right_speed', 0)
        
        left_text = self.info_font.render(f"Left: {left_speed:.2f}", True, self.BLUE)
        self.screen.blit(left_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
        y_pos += 25
        
        right_text = self.info_font.render(f"Right: {right_speed:.2f}", True, self.BLUE)
        self.screen.blit(right_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
        y_pos += 35
        
        # Sensor data
        sensor_title = self.info_font.render("Sensor Data:", True, self.BLACK)
        self.screen.blit(sensor_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        # Display available sensor readings
        for label, key in [
            ("Roll", "roll"),
            ("Pitch", "pitch"),
            ("Temperature", "temperature"),
            ("Voltage", "voltage")
        ]:
            if key in frame_data and frame_data[key] != "":
                text = self.small_font.render(f"{label}: {frame_data[key]:.2f}", True, self.BLACK)
                self.screen.blit(text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
                y_pos += 20
        
        # Controls guide
        y_pos = self.WINDOW_HEIGHT - 100
        controls_title = self.info_font.render("Controls:", True, self.BLACK)
        self.screen.blit(controls_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        controls = [
            "SPACE - Play/Pause",
            "→/← - Step forward/backward",
            "+/- - Adjust speed",
            "ESC - Exit"
        ]
        
        for text in controls:
            control_text = self.small_font.render(text, True, self.BLACK)
            self.screen.blit(control_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 20

    def handle_input(self):
        """Handle keyboard input for playback control"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
                elif event.key == pygame.K_SPACE:
                    self.is_playing = not self.is_playing
                elif event.key == pygame.K_RIGHT and not self.is_playing:
                    self.current_frame = min(self.current_frame + 1, len(self.data) - 1)
                elif event.key == pygame.K_LEFT and not self.is_playing:
                    self.current_frame = max(self.current_frame - 1, 0)
                elif event.key == pygame.K_EQUALS:  # Plus key
                    self.playback_speed = min(self.playback_speed * 1.5, 8.0)
                elif event.key == pygame.K_MINUS:
                    self.playback_speed = max(self.playback_speed / 1.5, 0.25)

    def run(self):
        """Main playback loop"""
        try:
            last_frame_time = time.time()
            
            while self.is_running and self.current_frame < len(self.data):
                self.handle_input()
                
                # Update frame if playing
                current_time = time.time()
                if self.is_playing and (current_time - last_frame_time) >= (1.0 / (self.FPS * self.playback_speed)):
                    self.current_frame += 1
                    if self.current_frame >= len(self.data):
                        self.current_frame = 0  # Loop playback
                    last_frame_time = current_time
                
                # Clear screen
                self.screen.fill(self.BLACK)
                
                # Get current frame data
                frame_data = self.data[self.current_frame]
                
                # Draw interface
                self.draw_video_feed(frame_data['image_path'])
                self.draw_sidebar(frame_data)
                
                # Update display
                pygame.display.flip()
                self.clock.tick(self.FPS)
                
        finally:
            pygame.quit()
            print("Playback ended")


def main():
    """Parse arguments and run the playback"""
    parser = argparse.ArgumentParser(description='UGV Log Playback')
    parser.add_argument('log_dir', type=str, help='Directory containing log files')
    
    args = parser.parse_args()
    
    player = UGVPlayback(args.log_dir)
    player.run()


if __name__ == "__main__":
    main()