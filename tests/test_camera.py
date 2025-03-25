#!/usr/bin/env python3
"""
Simple test script to connect to the M5 TimerCAM and display the video stream using requests.
"""

import sys
import time
import cv2
import argparse
import requests
import numpy as np
from io import BytesIO

def extract_jpeg(buffer):
    """Extract JPEG image from MJPEG stream buffer"""
    start = buffer.find(b'\xff\xd8')  # JPEG start marker
    end = buffer.find(b'\xff\xd9')    # JPEG end marker
    
    if start != -1 and end != -1:
        return buffer[start:end+2], buffer[end+2:]
    return None, buffer

def test_camera(url):
    """Test connection to M5 TimerCAM and display video stream"""
    stream_url = f"{url}/stream"  # Adjust this endpoint based on your camera's API
    print(f"Attempting to connect to {stream_url}")
    
    try:
        # Initialize stream
        response = requests.get(stream_url, stream=True, timeout=10)
        if not response.ok:
            print(f"Failed to connect: {response.status_code}")
            return False
            
        # Display setup
        window_name = "M5 TimerCAM Stream"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 640, 480)
        
        # Stream processing
        buffer = b''
        frame_count = 0
        start_time = time.time()
        
        for chunk in response.iter_content(chunk_size=1024):
            if not chunk:
                continue
                
            buffer += chunk
            frame_data, buffer = extract_jpeg(buffer)
            
            if frame_data is not None:
                # Convert to OpenCV format
                frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    print('frame', frame.shape)
                    frame_count += 1
                    elapsed = time.time() - start_time
                    
                    # Calculate and display FPS every second
                    if elapsed >= 1:
                        fps = frame_count / elapsed
                        print(f"FPS: {fps:.2f}")
                        frame_count = 0
                        start_time = time.time()
                    
                    # Display frame
                    cv2.imshow(window_name, frame)
                    
                    # Break on 'q' key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return False
    finally:
        cv2.destroyAllWindows()
        print("Stream closed")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Test M5 TimerCAM connection')
    parser.add_argument('--url', type=str, default='http://192.168.4.2',
                      help='URL of the M5 TimerCAM')
    
    args = parser.parse_args()
    
    if not test_camera(args.url):
        sys.exit(1)

if __name__ == "__main__":
    main()