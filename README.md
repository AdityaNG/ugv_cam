# UGV_CAM: Drive By Wire Platform

<img src="media/bot.png">

<img src="media/demo_playback.gif">

This is a codebase to interface with the UGV+Camera platform:
1. UGV01 / UGV02: REST JSON API to control the actuators and get IMU feedback
2. M5Stack-TimerCam: Get video stream

Example usage
```
from ugv_cam import Agent, Action, ActionEnum, State
agent = Agent(
    ugv_url="192.168.4.1",
    m5cam_url="192.168.4.6",
)

action = Action(
    ActionEnum.CMD_SPEED_CTRL,
    data=dict(
        L=0.5,
        R=0.5,
    )
)
# The action is validated (correct list of parameters and values for the given action type)

state: State = agent.step(action)
state.sensors   # IMU Data, temperature, etc.
state.feedback  # Chassis information feedback
state.image     # Image from the M5 stack
```
