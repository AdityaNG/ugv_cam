"""
PyGame demo:
- Connects to the device
- Visualizes the temperature, feedback, voltage, IMU on screen
- Shows the video feed on screen
- Takes WASD input from the keyboard and passes it as tank controls to the agent
"""

import time
from . import Agent, Action, ActionEnum, State

def main():
    # Initialize the agent
    agent = Agent(
        ugv_url="http://192.168.4.1",
        m5cam_url="http://192.168.4.6",
    )
    
    try:
        # Move forward for 2 seconds
        print("Moving forward...")
        action = Action(
            action_type=ActionEnum.CMD_SPEED_CTRL,
            data={"L": 0.3, "R": 0.3}
        )
        
        start_time = time.time()
        while time.time() - start_time < 2:
            state = agent.step(action)
            if state.feedback:
                print(f"Speed: L={state.feedback.L:.2f}, R={state.feedback.R:.2f}, Battery: {state.feedback.v:.2f}V")
            time.sleep(0.1)
        
        # Turn right for 1 second
        print("\nTurning right...")
        action = Action(
            action_type=ActionEnum.CMD_SPEED_CTRL,
            data={"L": 0.3, "R": -0.3}
        )
        
        start_time = time.time()
        while time.time() - start_time < 1:
            state = agent.step(action)
            if state.feedback:
                print(f"Speed: L={state.feedback.L:.2f}, R={state.feedback.R:.2f}, Roll: {state.feedback.r:.2f}, Pitch: {state.feedback.p:.2f}")
            time.sleep(0.1)
        
        # Stop
        print("\nStopping...")
        action = Action(
            action_type=ActionEnum.CMD_SPEED_CTRL,
            data={"L": 0, "R": 0}
        )
        state = agent.step(action)
        
        # Get IMU data
        print("\nGetting IMU data...")
        action = Action(
            action_type=ActionEnum.CMD_GET_IMU_DATA,
            data={}
        )
        state = agent.step(action)
        if state.sensors:
            print(f"IMU data: Roll={state.sensors.r:.2f}, Pitch={state.sensors.p:.2f}")
            if state.sensors.ax is not None:
                print(f"Accelerometer: X={state.sensors.ax:.2f}, Y={state.sensors.ay:.2f}, Z={state.sensors.az:.2f}")
        
    finally:
        # Ensure we stop the robot and clean up resources
        agent.close()

if __name__ == "__main__":
    main()