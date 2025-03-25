"""
Agent definition
- Agent must have a subprocesses that keeps pulling the video feed from the m5 camera
- The agent must be able to ping the UGV with the requested action and return the feedback from that call along with the latest image from the subprocess's output queue
"""
import time
import json
import logging
import threading
import queue
import requests
from typing import Optional
import cv2
import numpy as np
from .schema import Action, State, ChassisFeedback, ImuData

logger = logging.getLogger(__name__)


class VideoStream:
    """Handles video streaming from M5Stack TimerCam in a separate thread"""
    
    def __init__(self, url: str, max_queue_size: int = 5):
        """
        Initialize video stream
        
        Args:
            url: URL to the M5Stack TimerCam stream (e.g., "http://192.168.4.6")
            max_queue_size: Maximum number of frames to keep in the queue
        """
        self.url = url
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.stop_event = threading.Event()
        self.thread = None
        self.last_frame = None
        self.connected = False
    
    def start(self):
        """Start the video streaming thread"""
        if self.thread is not None and self.thread.is_alive():
            logger.warning("Video stream thread is already running")
            return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._stream_video, daemon=True)
        self.thread.start()
        logger.info(f"Started video streaming from {self.url}")
    
    def stop(self):
        """Stop the video streaming thread"""
        if self.thread is None or not self.thread.is_alive():
            return
        
        self.stop_event.set()
        self.thread.join(timeout=5.0)
        self.connected = False
        logger.info("Stopped video streaming")
    
    def _stream_video(self):
        """Thread function to continuously fetch video frames"""
        stream_url = f"{self.url.rstrip('/')}"
        
        # Check if the URL already includes a video path
        if not (stream_url.endswith('.mjpeg') or stream_url.endswith('.mjpg')):
            # Default M5 TimerCam URL format
            stream_url = stream_url
        
        cap = cv2.VideoCapture(stream_url)
        
        try:
            if not cap.isOpened():
                logger.error(f"Failed to open video stream at {stream_url}")
                self.connected = False
                return
            
            self.connected = True
            logger.info(f"Successfully connected to video stream at {stream_url}")
            
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to receive frame from video stream")
                    time.sleep(0.1)
                    continue
                
                # Keep only the most recent frame by emptying the queue first
                while not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.task_done()
                    except queue.Empty:
                        break
                
                try:
                    self.frame_queue.put_nowait(frame)
                    self.last_frame = frame
                except queue.Full:
                    # This shouldn't happen as we just emptied the queue
                    pass
        
        finally:
            cap.release()
            self.connected = False
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame from the queue, non-blocking"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return self.last_frame


class Agent:
    """Agent for interacting with UGV and M5Stack TimerCam"""
    
    def __init__(self, ugv_url: str, m5cam_url: str):
        """
        Initialize the agent
        
        Args:
            ugv_url: URL to the UGV API (e.g., "http://192.168.4.1")
            m5cam_url: URL to the M5Stack TimerCam stream (e.g., "http://192.168.4.6")
        """
        self.ugv_url = ugv_url.rstrip('/')
        self.m5cam_url = m5cam_url.rstrip('/')
        
        # Initialize video stream
        self.video_stream = VideoStream(self.m5cam_url)
        self.video_stream.start()
        
        # Wait for video connection to establish
        start_time = time.time()
        while not self.video_stream.connected and time.time() - start_time < 10:
            time.sleep(0.5)
        
        if not self.video_stream.connected:
            logger.warning(f"Could not establish connection to camera at {self.m5cam_url}")
        
        # Test connection to UGV
        try:
            self._send_command({"T": 130})  # CMD_BASE_FEEDBACK
            logger.info(f"Successfully connected to UGV at {self.ugv_url}")
        except Exception as e:
            logger.warning(f"Could not connect to UGV at {self.ugv_url}: {e}")
    
    def _send_command(self, command: dict) -> dict:
        """
        Send a command to the UGV and return the response
        
        Args:
            command: Command dictionary to send
            
        Returns:
            Response from the UGV
        """
        try:
            response = requests.post(
                f"{self.ugv_url}/js",
                json=command,
                timeout=2.0
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending command to UGV: {e}")
            raise
    
    def step(self, action: Action) -> State:
        """
        Execute an action and return the resulting state
        
        Args:
            action: Action to execute
            
        Returns:
            State after executing the action
        """
        # Send the command to the UGV
        response = self._send_command(action.to_json_dict())
        
        # Process the response based on its type
        feedback = None
        sensors = None
        
        if isinstance(response, dict):
            if "T" in response:
                if response["T"] == 1001:  # ChassisFeedback
                    feedback = ChassisFeedback(**response)
                    # Extract IMU data from feedback
                    sensors = ImuData(r=response["r"], p=response["p"])
                elif response["T"] == 1002:  # Full IMU data
                    sensors = ImuData(**{k: v for k, v in response.items() if k != "T"})
        
        # Get the latest camera frame
        frame = self.video_stream.get_latest_frame()
        image_bytes = None
        if frame is not None:
            # Convert the frame to bytes for the State object
            _, buffer = cv2.imencode('.jpg', frame)
            image_bytes = buffer.tobytes()
        
        # Create and return the state
        return State(
            sensors=sensors,
            feedback=feedback,
            image=image_bytes
        )
    
    def get_latest_state(self) -> State:
        """
        Get the latest state without sending a command
        
        Returns:
            Current state
        """
        # Send a feedback request
        response = self._send_command({"T": 130})  # CMD_BASE_FEEDBACK
        
        feedback = None
        sensors = None
        
        if isinstance(response, dict) and "T" in response:
            if response["T"] == 1001:  # ChassisFeedback
                feedback = ChassisFeedback(**response)
                # Extract IMU data from feedback
                sensors = ImuData(r=response["r"], p=response["p"])
        
        # Get the latest camera frame
        frame = self.video_stream.get_latest_frame()
        image_bytes = None
        if frame is not None:
            # Convert the frame to bytes for the State object
            _, buffer = cv2.imencode('.jpg', frame)
            image_bytes = buffer.tobytes()
        
        # Create and return the state
        return State(
            sensors=sensors,
            feedback=feedback,
            image=image_bytes
        )
    
    def close(self):
        """Clean up resources"""
        # Stop the robot
        try:
            self._send_command({"T": 1, "L": 0, "R": 0})  # Stop motion
        except Exception as e:
            logger.warning(f"Error stopping robot: {e}")
        
        # Stop the video stream
        self.video_stream.stop()