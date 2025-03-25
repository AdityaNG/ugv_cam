"""
PyDantic schemas to define the state, action, etc.
"""
import time
from enum import Enum, auto
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, validator

class ActionEnum(Enum):
    """Enum for UGV JSON commands as defined in the API docs"""
    # Motion Control Commands
    CMD_SPEED_CTRL = 1
    CMD_PWM_INPUT = 11
    CMD_ROS_CTRL = 13
    CMD_SET_MOTOR_PID = 2
    
    # OLED Display Control
    CMD_OLED_CTRL = 3
    CMD_OLED_DEFAULT = -3
    
    # Module Type
    CMD_MODULE_TYPE = 4
    
    # IMU Related Functions
    CMD_GET_IMU_DATA = 126
    CMD_CALI_IMU_STEP = 127
    CMD_GET_IMU_OFFSET = 128
    CMD_SET_IMU_OFFSET = 129
    
    # Chassis Information Feedback
    CMD_BASE_FEEDBACK = 130
    CMD_BASE_FEEDBACK_FLOW = 131
    CMD_FEEDBACK_FLOW_INTERVAL = 142
    CMD_UART_ECHO_MODE = 143
    
    # WiFi Configuration
    CMD_WIFI_ON_BOOT = 401
    CMD_SET_AP = 402
    CMD_SET_STA = 403
    CMD_WIFI_APSTA = 404
    CMD_WIFI_INFO = 405
    CMD_WIFI_CONFIG_CREATE_BY_STATUS = 406
    CMD_WIFI_CONFIG_CREATE_BY_INPUT = 407
    CMD_WIFI_STOP = 408
    
    # 12V Switch and Gimbal Settings
    CMD_LED_CTRL = 132
    CMD_GIMBAL_CTRL_SIMPLE = 133
    CMD_GIMBAL_CTRL_MOVE = 134
    CMD_GIMBAL_CTRL_STOP = 135
    CMD_GIMBAL_STEADY = 137
    CMD_GIMBAL_USER_CTRL = 141
    
    # Robotic Arm Control
    CMD_MOVE_INIT = 100
    CMD_SINGLE_JOINT_CTRL = 101
    CMD_JOINTS_RAD_CTRL = 102
    CMD_SINGLE_AXIS_CTRL = 103
    CMD_XYZT_GOAL_CTRL = 104
    CMD_XYZT_DIRECT_CTRL = 1041
    CMD_SERVO_RAD_FEEDBACK = 105
    CMD_EOAT_HAND_CTRL = 106
    CMD_EOAT_GRAB_TORQUE = 107
    CMD_SET_JOINT_PID = 108
    CMD_RESET_PID = 109
    CMD_SET_NEW_X = 110
    CMD_DYNAMIC_ADAPTATION = 112
    
    # Other Settings
    CMD_HEART_BEAT_SET = 136
    CMD_SET_SPD_RATE = 138
    CMD_GET_SPD_RATE = 139
    
    # ESP-NOW Related Settings
    CMD_BROADCAST_FOLLOWER = 300
    CMD_GET_MAC_ADDRESS = 302
    CMD_ESP_NOW_ADD_FOLLOWER = 303
    CMD_ESP_NOW_REMOVE_FOLLOWER = 304
    CMD_ESP_NOW_GROUP_CTRL = 305
    CMD_ESP_NOW_SINGLE = 306
    
    # Task File Related Functions
    CMD_SCAN_FILES = 200
    CMD_CREATE_FILE = 201
    CMD_READ_FILE = 202
    CMD_DELETE_FILE = 203
    CMD_APPEND_LINE = 204
    CMD_INSERT_LINE = 205
    CMD_REPLACE_LINE = 206
    
    # Servo Settings
    CMD_SET_SERVO_ID = 501
    CMD_SET_MIDDLE = 502
    CMD_SET_SERVO_PID = 503
    
    # ESP32 Related Features
    CMD_REBOOT = 600
    CMD_FREE_FLASH_SPACE = 601
    CMD_BOOT_MISSION_INFO = 602
    CMD_RESET_BOOT_MISSION = 603
    CMD_NVS_CLEAR = 604
    CMD_INFO_PRINT = 605


class ImuData(BaseModel):
    """IMU sensor data"""
    r: float  # Roll
    p: float  # Pitch
    ax: Optional[float] = None  # Accelerometer X
    ay: Optional[float] = None  # Accelerometer Y
    az: Optional[float] = None  # Accelerometer Z
    gx: Optional[float] = None  # Gyroscope X
    gy: Optional[float] = None  # Gyroscope Y
    gz: Optional[float] = None  # Gyroscope Z
    mx: Optional[float] = None  # Magnetometer X
    my: Optional[float] = None  # Magnetometer Y
    mz: Optional[float] = None  # Magnetometer Z
    temp: Optional[float] = None  # Temperature


class ChassisFeedback(BaseModel):
    """Basic chassis feedback data"""
    T: int  # Type (should be 1001)
    L: float  # Left wheel velocity
    R: float  # Right wheel velocity
    r: float  # Roll
    p: float  # Pitch
    v: float  # Battery voltage


class Action(BaseModel):
    """UGV action to be sent via REST API"""
    action_type: ActionEnum
    data: Dict[str, Any]
    
    def to_json_dict(self):
        """Convert to the format expected by the UGV API"""
        result = {"T": self.action_type.value}
        result.update(self.data)
        return result
    
    @validator('data')
    def validate_data_for_action_type(cls, data, values):
        """Validate that the data contains the required fields for the given action type"""
        if 'action_type' not in values:
            return data
        
        action_type = values['action_type']
        
        # Define required fields for each action type
        required_fields = {
            ActionEnum.CMD_SPEED_CTRL: ['L', 'R'],
            ActionEnum.CMD_PWM_INPUT: ['L', 'R'],
            ActionEnum.CMD_ROS_CTRL: ['X', 'Z'],
            # Add other action types and their required fields as needed
        }
        
        # Check if the action type has defined required fields
        if action_type in required_fields:
            missing_fields = [field for field in required_fields[action_type] if field not in data]
            if missing_fields:
                raise ValueError(f"Missing required fields for {action_type}: {missing_fields}")
        
        return data


class State(BaseModel):
    """UGV state including sensor data and camera image"""
    sensors: Optional[ImuData] = None
    feedback: Optional[ChassisFeedback] = None
    image: Optional[bytes] = None
    timestamp: float = Field(default_factory=lambda: time.time())