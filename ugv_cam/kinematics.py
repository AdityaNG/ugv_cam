import numpy as np
from typing import Tuple, List

def tank_model(
    v_l: float, v_r: float, current_pose: Tuple[float, float, float, float], dt: float
) -> Tuple[float, float, float, float]:
    """
    Tank drive kinematics model in right-handed coordinate system where:
    x -> right
    y -> down  
    z -> forward (direction of motion)
    
    Args:
        v_l: Left wheel velocity (m/s)
        v_r: Right wheel velocity (m/s) 
        current_pose: (x, y, z, yaw) where yaw is heading in radians
        dt: Time step in seconds
        
    Returns:
        new_pose: (x, y, z, yaw) for next position and heading
    """
    # Vehicle parameters
    WHEEL_BASE = 0.22  # meters, distance between left and right wheels
    
    x, y, z, yaw = current_pose
    
    # Calculate vehicle motion in local frame
    v_center = (v_r + v_l) / 2.0  # Linear velocity at center
    omega = (v_r - v_l) / WHEEL_BASE  # Angular velocity
    
    # Update yaw
    yaw_new = yaw + omega * dt
    
    # Calculate motion in local frame
    if abs(omega) < 1e-6:  # Straight motion
        dz = v_center * dt  # Forward motion
        dx = 0
    else:  # Turning motion
        R = v_center / omega  # Turn radius
        dx = R * (1 - np.cos(omega * dt))  # Local x motion
        dz = R * np.sin(omega * dt)  # Local z motion
    
    # Transform local motion to global frame using current yaw
    x_new = x + dx * np.cos(yaw) - dz * np.sin(yaw)
    z_new = z + dx * np.sin(yaw) + dz * np.cos(yaw)
    y_new = y  # No vertical motion
    
    return (x_new, y_new, z_new, yaw_new)

def predict_trajectory(speeds: List[Tuple[float, float]], dt: float, n_steps: int) -> np.ndarray:
    """
    Predict vehicle trajectory given sequence of wheel speeds
    
    Args:
        speeds: List of (left_speed, right_speed) tuples
        dt: Time step between speed measurements
        n_steps: Number of steps to predict
        
    Returns:
        trajectory: Nx3 array of (x,y,z) positions following right-handed coordinate system
    """
    # Start at origin with zero heading
    pose = (0.0, 0.0, 0.0, 0.0)  # x, y, z, yaw
    trajectory = [(0.0, 0.0, 0.0)]  # Store only position
    
    # Predict forward using speed sequence
    for i in range(min(len(speeds), n_steps)):
        v_l, v_r = speeds[i]
        pose = tank_model(v_l, v_r, pose, dt)
        trajectory.append((pose[0], pose[1], pose[2]))  # Store position only
        
    return np.array(trajectory)