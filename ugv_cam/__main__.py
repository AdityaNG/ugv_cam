"""
PyGame demo:
- Connects to the device
- Visualizes the temperature, feedback, voltage, IMU on screen
- Shows the video feed on screen
- Takes WASD input from the keyboard and passes it as tank controls to the agent
"""

import time
import sys
from typing import Optional

import argparse
import pygame
import numpy as np
import cv2
from . import Agent, Action, ActionEnum, State


class UGVDemo:
    """PyGame-based demo for UGV control and visualization"""
    
    # Control settings
    MAX_SPEED = 0.5  # Maximum speed in m/s
    SPEED_STEP = 0.1  # Speed increment/decrement step
    
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

    # Controller settings
    JOYSTICK_DEADZONE = 0.01  # Ignore small stick movements
    TRIGGER_DEADZONE = 0.1    # Ignore small trigger movements
    
    def __init__(self, ugv_url="http://192.168.4.1", m5cam_url="http://192.168.4.6"):
        """Initialize the demo with connection to UGV and camera"""
        pygame.init()
        pygame.joystick.init()
        pygame.font.init()

        # Initialize gamepad if available
        self.gamepad: Optional[pygame.joystick.Joystick] = None
        self.setup_gamepad()
        
        # Set up the display
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("UGV Control Panel")
        self.clock = pygame.time.Clock()
        
        # Set up fonts
        self.title_font = pygame.font.SysFont('Arial', 24, bold=True)
        self.info_font = pygame.font.SysFont('Arial', 18)
        self.small_font = pygame.font.SysFont('Arial', 14)
        
        # Initialize the agent
        print(f"Connecting to UGV at {ugv_url} and camera at {m5cam_url}...")
        self.agent = Agent(ugv_url=ugv_url, m5cam_url=m5cam_url)
        
        # Control state
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.is_running = True
        
        # Data for visualization
        self.current_state = None
        self.battery_history = []
        self.max_history_points = 100
        
        # Timer for status updates
        self.last_update_time = time.time()
        self.update_interval = 0.1  # seconds
        
        print("UGV Demo initialized. Use WASD to control the robot.")
        print("Press ESCAPE or close the window to exit.")
    
    def setup_gamepad(self):
        """Initialize the first available gamepad"""
        try:
            if pygame.joystick.get_count() > 0:
                self.gamepad = pygame.joystick.Joystick(0)
                self.gamepad.init()
                print(f"Gamepad detected: {self.gamepad.get_name()}")
            else:
                print("No gamepad detected, using keyboard controls")
        except Exception as e:
            print(f"Error initializing gamepad: {e}")
            self.gamepad = None

    def get_gamepad_input(self):
        """Get normalized input values from gamepad using more intuitive controls"""
        if not self.gamepad:
            return None
        
        try:
            # Right stick Y-axis for forward/backward (inverted)
            forward = -self.gamepad.get_axis(3)  # Invert because Y-axis is inverted
            # Right stick X-axis for turning
            turn = -self.gamepad.get_axis(0)
            boost = (self.gamepad.get_axis(4) + 1) / 2.0
            
            # Apply deadzone
            forward = 0.0 if abs(forward) < self.JOYSTICK_DEADZONE else forward
            turn = 0.0 if abs(turn) < self.JOYSTICK_DEADZONE else turn

            boost = boost * 0.75 + 0.25
            
            # Convert to tank controls
            # When turning right (positive turn), right track slows down
            # When turning left (negative turn), left track slows down
            left_y = forward - turn
            right_y = forward + turn
            
            # if turn != 0:
            #     # Clamp values
            #     left_y = max(min(left_y, 0.25), -0.25)
            #     right_y = max(min(right_y, 0.25), -0.25)
            # else:
            #     # Clamp values
            #     left_y = max(min(left_y, 1.0), -1.0)
            #     right_y = max(min(right_y, 1.0), -1.0)
            
            clamp = 0.25 + boost
            
            left_y = max(min(left_y, clamp), -clamp)
            right_y = max(min(right_y, clamp), -clamp)
            
            return left_y, right_y
        except Exception as e:
            print(f"Error reading gamepad: {e}")
            return None

    def update_speeds(self):
        """Update speeds from either gamepad or keyboard"""
        # Try gamepad first
        gamepad_input = self.get_gamepad_input()
        if gamepad_input:
            left_y, right_y = gamepad_input
            self.left_speed = left_y * self.MAX_SPEED
            self.right_speed = right_y * self.MAX_SPEED
            return

        # Fall back to keyboard if no gamepad input
        keys = pygame.key.get_pressed()
        self.update_speeds_from_keys(keys)

    def update_speeds_from_keys(self, keys):
        """Update motor speeds based on keyboard input"""
        # Reset speeds if no movement keys are pressed
        if not (keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]):
            self.left_speed = 0.0
            self.right_speed = 0.0
            return
        
        # Forward/backward movement (W/S keys)
        if keys[pygame.K_w]:
            self.left_speed = min(self.left_speed + self.SPEED_STEP, self.MAX_SPEED)
            self.right_speed = min(self.right_speed + self.SPEED_STEP, self.MAX_SPEED)
        elif keys[pygame.K_s]:
            self.left_speed = max(self.left_speed - self.SPEED_STEP, -self.MAX_SPEED)
            self.right_speed = max(self.right_speed - self.SPEED_STEP, -self.MAX_SPEED)
        
        # Turning (A/D keys) - adjusts the differential between wheels
        if keys[pygame.K_a]:
            self.left_speed = max(self.left_speed - self.SPEED_STEP, -self.MAX_SPEED)
            self.right_speed = min(self.right_speed + self.SPEED_STEP, self.MAX_SPEED)
        elif keys[pygame.K_d]:
            self.left_speed = min(self.left_speed + self.SPEED_STEP, self.MAX_SPEED)
            self.right_speed = max(self.right_speed - self.SPEED_STEP, -self.MAX_SPEED)
    
    def send_speed_command(self):
        """Send the current speed settings to the agent"""
        action = Action(
            action_type=ActionEnum.CMD_SPEED_CTRL,
            data={"L": self.left_speed, "R": self.right_speed}
        )
        
        try:
            self.current_state = self.agent.step(action)
            
            # Add battery voltage to history if available
            if self.current_state.feedback and hasattr(self.current_state.feedback, 'v'):
                self.battery_history.append(self.current_state.feedback.v)
                if len(self.battery_history) > self.max_history_points:
                    self.battery_history.pop(0)
                    
        except Exception as e:
            print(f"Error sending command: {e}")
    
    def draw_video_feed(self):
        """Draw the camera feed from M5Stack"""
        if not self.current_state or not self.current_state.image:
            # Draw placeholder if no image
            video_area = pygame.Rect(0, 0, self.VIDEO_AREA_WIDTH, self.VIDEO_AREA_HEIGHT)
            pygame.draw.rect(self.screen, self.GRAY, video_area)
            no_video_text = self.title_font.render("No Video Feed", True, self.WHITE)
            text_rect = no_video_text.get_rect(center=(self.VIDEO_AREA_WIDTH // 2, self.VIDEO_AREA_HEIGHT // 2))
            self.screen.blit(no_video_text, text_rect)
            return
        
        # Convert image bytes to pygame surface
        try:
            image_array = np.frombuffer(self.current_state.image, dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
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
            # Draw placeholder on error
            video_area = pygame.Rect(0, 0, self.VIDEO_AREA_WIDTH, self.VIDEO_AREA_HEIGHT)
            pygame.draw.rect(self.screen, self.GRAY, video_area)
            error_text = self.info_font.render(f"Video Error: {str(e)[:30]}", True, self.RED)
            self.screen.blit(error_text, (10, self.VIDEO_AREA_HEIGHT // 2))
    
    def draw_sidebar(self):
        """Draw the sidebar with sensor data and controls"""
        # Draw sidebar background
        sidebar_rect = pygame.Rect(self.VIDEO_AREA_WIDTH, 0, self.SIDEBAR_WIDTH, self.WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, self.LIGHT_GRAY, sidebar_rect)
        
        # Title
        title = self.title_font.render("UGV Control Panel", True, self.BLACK)
        self.screen.blit(title, (self.VIDEO_AREA_WIDTH + 10, 10))
        
        y_pos = 50
        
        # Current Speed
        speed_title = self.info_font.render("Current Speed (m/s):", True, self.BLACK)
        self.screen.blit(speed_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        left_text = self.info_font.render(f"Left: {self.left_speed:.2f}", True, self.BLUE)
        self.screen.blit(left_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
        y_pos += 25
        
        right_text = self.info_font.render(f"Right: {self.right_speed:.2f}", True, self.BLUE)
        self.screen.blit(right_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
        y_pos += 35
        
        # Draw speed control bars
        bar_width = self.SIDEBAR_WIDTH - 40
        bar_height = 20
        
        # Left speed bar
        pygame.draw.rect(self.screen, self.GRAY, (self.VIDEO_AREA_WIDTH + 20, y_pos, bar_width, bar_height))
        left_fill_width = int((self.left_speed / self.MAX_SPEED) * (bar_width / 2))
        if self.left_speed >= 0:
            left_fill_rect = pygame.Rect(bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos, left_fill_width, bar_height)
            pygame.draw.rect(self.screen, self.GREEN, left_fill_rect)
        else:
            left_fill_rect = pygame.Rect(bar_width // 2 + self.VIDEO_AREA_WIDTH + 20 + left_fill_width, y_pos, -left_fill_width, bar_height)
            pygame.draw.rect(self.screen, self.RED, left_fill_rect)
        pygame.draw.line(self.screen, self.BLACK, (bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos), 
                          (bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos + bar_height), 2)
        
        y_pos += bar_height + 10
        
        # Right speed bar
        pygame.draw.rect(self.screen, self.GRAY, (self.VIDEO_AREA_WIDTH + 20, y_pos, bar_width, bar_height))
        right_fill_width = int((self.right_speed / self.MAX_SPEED) * (bar_width / 2))
        if self.right_speed >= 0:
            right_fill_rect = pygame.Rect(bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos, right_fill_width, bar_height)
            pygame.draw.rect(self.screen, self.GREEN, right_fill_rect)
        else:
            right_fill_rect = pygame.Rect(bar_width // 2 + self.VIDEO_AREA_WIDTH + 20 + right_fill_width, y_pos, -right_fill_width, bar_height)
            pygame.draw.rect(self.screen, self.RED, right_fill_rect)
        pygame.draw.line(self.screen, self.BLACK, (bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos), 
                          (bar_width // 2 + self.VIDEO_AREA_WIDTH + 20, y_pos + bar_height), 2)
        
        y_pos += bar_height + 30
        
        # Sensor data
        sensor_title = self.info_font.render("Sensor Data:", True, self.BLACK)
        self.screen.blit(sensor_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        if self.current_state and self.current_state.sensors:
            sensors = self.current_state.sensors
            roll_text = self.small_font.render(f"Roll: {sensors.r:.2f}°", True, self.BLACK)
            self.screen.blit(roll_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 20
            
            pitch_text = self.small_font.render(f"Pitch: {sensors.p:.2f}°", True, self.BLACK)
            self.screen.blit(pitch_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 20
            
            if hasattr(sensors, 'temp') and sensors.temp is not None:
                temp_text = self.small_font.render(f"Temperature: {sensors.temp:.1f}°C", True, self.BLACK)
                self.screen.blit(temp_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
                y_pos += 20
            
            if all(hasattr(sensors, attr) and getattr(sensors, attr) is not None for attr in ['ax', 'ay', 'az']):
                accel_text = self.small_font.render(f"Accel: X={sensors.ax:.2f}, Y={sensors.ay:.2f}, Z={sensors.az:.2f}", True, self.BLACK)
                self.screen.blit(accel_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
                y_pos += 20
        else:
            no_sensor_text = self.small_font.render("No sensor data available", True, self.RED)
            self.screen.blit(no_sensor_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 20
        
        y_pos += 10
        
        # Battery voltage
        battery_title = self.info_font.render("Battery:", True, self.BLACK)
        self.screen.blit(battery_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        if self.current_state and self.current_state.feedback and hasattr(self.current_state.feedback, 'v'):
            voltage = self.current_state.feedback.v
            
            # Color based on battery level
            if voltage > 11.5:
                color = self.GREEN
            elif voltage > 10.8:
                color = self.YELLOW
            else:
                color = self.RED
                
            voltage_text = self.info_font.render(f"{voltage:.2f}V", True, color)
            self.screen.blit(voltage_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 30
            
            # Battery voltage history graph
            if self.battery_history:
                graph_width = self.SIDEBAR_WIDTH - 40
                graph_height = 40
                graph_rect = pygame.Rect(self.VIDEO_AREA_WIDTH + 20, y_pos, graph_width, graph_height)
                pygame.draw.rect(self.screen, self.WHITE, graph_rect)
                pygame.draw.rect(self.screen, self.BLACK, graph_rect, 1)
                
                # Draw graph lines
                if len(self.battery_history) > 1:
                    min_v = min(10.0, min(self.battery_history))  # Floor at 10V
                    max_v = max(12.6, max(self.battery_history))  # Ceiling at 12.6V
                    v_range = max_v - min_v
                    
                    points = []
                    for i, v in enumerate(self.battery_history):
                        x = self.VIDEO_AREA_WIDTH + 20 + i * graph_width // (len(self.battery_history) - 1 or 1)
                        y = y_pos + graph_height - int((v - min_v) / v_range * graph_height)
                        points.append((x, y))
                    
                    if len(points) > 1:
                        pygame.draw.lines(self.screen, self.BLUE, False, points, 2)
                
                y_pos += graph_height + 10
        else:
            voltage_text = self.small_font.render("No voltage data available", True, self.RED)
            self.screen.blit(voltage_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 30
        
        # Controls guide
        y_pos = self.WINDOW_HEIGHT - 160  # Adjusted to make room for more controls
        controls_title = self.info_font.render("Controls:", True, self.BLACK)
        self.screen.blit(controls_title, (self.VIDEO_AREA_WIDTH + 10, y_pos))
        y_pos += 25
        
        controls_text = [
            "Keyboard:",
            "W - Forward",
            "S - Backward",
            "A - Turn Left",
            "D - Turn Right",
            "Gamepad:",
            "Right Stick Up/Down - Forward/Backward",
            "Right Stick Left/Right - Turn Left/Right",
            "ESC - Exit"
        ]
        
        for text in controls_text:
            control_text = self.small_font.render(text, True, self.BLACK)
            self.screen.blit(control_text, (self.VIDEO_AREA_WIDTH + 20, y_pos))
            y_pos += 20
    
    def draw_interface(self):
        """Draw the complete interface"""
        # Clear the screen
        self.screen.fill(self.BLACK)
        
        # Draw the video feed
        self.draw_video_feed()
        
        # Draw the sidebar
        self.draw_sidebar()
        
        # Update the display
        pygame.display.flip()
    
    def run(self):
        """Main loop for the demo"""
        try:
            while self.is_running:
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.is_running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.is_running = False
                    elif event.type == pygame.JOYBUTTONDOWN:
                        if event.button == 7:  # Usually the START button
                            self.is_running = False
                
                # Update speeds using either gamepad or keyboard
                self.update_speeds()
                
                # Update robot state at intervals
                current_time = time.time()
                if current_time - self.last_update_time >= self.update_interval:
                    self.send_speed_command()
                    self.last_update_time = current_time
                
                # Draw the interface
                self.draw_interface()
                
                # Cap the frame rate
                self.clock.tick(self.FPS)
        
        finally:
            # Ensure we stop the robot before exiting
            try:
                stop_action = Action(
                    action_type=ActionEnum.CMD_SPEED_CTRL,
                    data={"L": 0, "R": 0}
                )
                self.agent.step(stop_action)
                print("Robot stopped.")
            except Exception as e:
                print(f"Error stopping robot: {e}")
            
            # Clean up
            self.agent.close()
            pygame.quit()
            print("Demo terminated.")


def main():
    """Parse arguments and run the demo"""
    parser = argparse.ArgumentParser(description='UGV Control Demo with PyGame')
    parser.add_argument('--ugv-url', type=str, default='http://192.168.4.1',
                        help='URL to connect to UGV')
    parser.add_argument('--m5cam-url', type=str, default='http://192.168.4.2',
                        help='URL to connect to M5 Camera')
    
    args = parser.parse_args()
    
    demo = UGVDemo(ugv_url=args.ugv_url, m5cam_url=args.m5cam_url)
    demo.run()


if __name__ == "__main__":
    main()