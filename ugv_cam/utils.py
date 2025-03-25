import math
import numpy as np
import cv2

import numpy as np
import math

def estimate_extrinsics(
    x: float = 0.0,
    y: float = -0.15,
    z: float = 0.0,
    R: float = 5.0,
    P: float = 0.0,
    Y: float = 0.0,
) -> np.ndarray:
    """
    Estimate camera extrinsic matrix from position and Euler angle rotations.
    
    The extrinsic matrix transforms points from world coordinates to camera coordinates.
    
    Args:
    - x, y, z: Translation coordinates (camera position in world frame)
    - R, P, Y: Rotation angles in degrees (roll, pitch, yaw)
    
    Returns:
    - 4x4 extrinsic matrix in the form:
      [[R11 R12 R13 tx]
       [R21 R22 R23 ty]
       [R31 R32 R33 tz]
       [ 0   0   0   1]]
    """
    # Convert rotation angles from degrees to radians
    roll = math.radians(R)
    pitch = math.radians(P)
    yaw = math.radians(Y)
    
    # Create rotation matrices for each axis
    # Rotation order: Z-Y-X (yaw-pitch-roll)
    
    # Rotation matrix for yaw (Z-axis)
    Rz = np.array([
        [math.cos(yaw), -math.sin(yaw), 0],
        [math.sin(yaw), math.cos(yaw), 0],
        [0, 0, 1]
    ])
    
    # Rotation matrix for pitch (Y-axis)
    Ry = np.array([
        [math.cos(pitch), 0, math.sin(pitch)],
        [0, 1, 0],
        [-math.sin(pitch), 0, math.cos(pitch)]
    ])
    
    # Rotation matrix for roll (X-axis)
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(roll), -math.sin(roll)],
        [0, math.sin(roll), math.cos(roll)]
    ])
    
    # Combined rotation matrix (Z-Y-X order)
    R = Rz @ Ry @ Rx
    
    # Create 4x4 extrinsic matrix
    extrinsic_matrix = np.eye(4)
    extrinsic_matrix[:3, :3] = R
    extrinsic_matrix[:3, 3] = [x, y, z]
    
    return extrinsic_matrix

def decompose_extrinsics(extrinsic_matrix: np.ndarray) -> tuple:
    """
    Decompose an extrinsic matrix into translation and Euler angles.
    
    Args:
    - extrinsic_matrix: 4x4 extrinsic matrix
    
    Returns:
    - Tuple of (x, y, z, roll, pitch, yaw) in degrees
    """
    # Extract translation
    x, y, z = extrinsic_matrix[:3, 3]
    
    # Extract rotation matrix
    R = extrinsic_matrix[:3, :3]
    
    # Extract Euler angles
    # Note: This uses the same Z-Y-X (yaw-pitch-roll) convention
    sy = math.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
    singular = sy < 1e-6
    
    if not singular:
        roll = math.degrees(math.atan2(R[2,1], R[2,2]))
        pitch = math.degrees(math.atan2(-R[2,0], sy))
        yaw = math.degrees(math.atan2(R[1,0], R[0,0]))
    else:
        roll = math.degrees(math.atan2(-R[1,2], R[1,1]))
        pitch = math.degrees(math.atan2(-R[2,0], sy))
        yaw = 0
    
    return x, y, z, roll, pitch, yaw

def estimate_intrinsics(
    fov_x: float = 66.5,  # degrees
    height: float = 480.0, # px
    width: float = 640.0,  # px
) -> np.ndarray:  # returns the 3x3 intrinsic matrix
    """
    Estimate camera intrinsic matrix based on horizontal field of view and image dimensions.
    
    The intrinsic matrix represents the camera's internal geometric parameters:
    - Focal length in pixels
    - Principal point (optical center)
    
    Args:
    - fov_x: Horizontal field of view in degrees
    - height: Image height in pixels
    - width: Image width in pixels
    
    Returns:
    - 3x3 intrinsic matrix in the form:
      [[fx  0  cx]
       [ 0 fy  cy]
       [ 0  0   1]]
    """
    # Convert horizontal FOV from degrees to radians
    fov_x_rad = math.radians(fov_x)
    
    # Calculate focal length in pixels
    # Using the relationship: tan(FOV/2) = (width/2) / focal_length
    focal_length_x = (width / 2) / math.tan(fov_x_rad / 2)
    
    # Assume symmetric pixels (fx = fy)
    # For most cameras, this is a reasonable approximation
    focal_length_y = focal_length_x
    
    # Set principal point at the image center
    principal_point_x = width / 2
    principal_point_y = height / 2
    
    # Construct the intrinsic matrix
    intrinsic_matrix = np.array([
        [focal_length_x, 0, principal_point_x],
        [0, focal_length_y, principal_point_y],
        [0, 0, 1]
    ])
    
    return intrinsic_matrix


def compute_vertical_fov(
    fov_x: float,  # horizontal FOV in degrees
    width: float,  # image width in pixels
    height: float  # image height in pixels
) -> float:
    """
    Compute vertical field of view based on horizontal FOV and aspect ratio.
    
    Args:
    - fov_x: Horizontal field of view in degrees
    - width: Image width in pixels
    - height: Image height in pixels
    
    Returns:
    - Vertical field of view in degrees
    """
    aspect_ratio = width / height
    
    # Convert horizontal FOV to radians
    fov_x_rad = math.radians(fov_x)
    
    # Calculate vertical FOV using trigonometry
    vertical_fov_rad = 2 * math.atan(
        math.tan(fov_x_rad / 2) / aspect_ratio
    )
    
    # Convert back to degrees
    return math.degrees(vertical_fov_rad)

def project_trajectory(
    img: np.ndarray,         # (HxWx3)
    trajectory: np.ndarray,  # (Nx3)
    intrinsics: np.ndarray = estimate_intrinsics(),  # (3x3)
    extrinsics: np.ndarray = estimate_extrinsics(),  # (4x4)
) -> np.ndarray:  # returns image with projected trajectory
    """
    Project a 3D trajectory onto an image using camera intrinsics and extrinsics.
    
    Args:
    - img: Input image (height x width x 3 color channels)
    - trajectory: 3D trajectory points (N x 3)
    - intrinsics: Camera intrinsic matrix (3 x 3)
    - extrinsics: Camera extrinsic matrix (4 x 4)
    
    Returns:
    - Image with trajectory points projected and drawn
    """
    # Create a copy of the image to avoid modifying the original
    output_img = img.copy()
    
    # Convert trajectory points to homogeneous coordinates
    trajectory_homogeneous = np.column_stack((trajectory, np.ones(len(trajectory))))
    
    # Transform trajectory to camera coordinates using extrinsics
    # Note: We use the inverse of extrinsics to transform from world to camera coordinates
    camera_coords = np.linalg.inv(extrinsics) @ trajectory_homogeneous.T
    
    # Convert to 3D points (remove homogeneous coordinate)
    camera_coords = camera_coords[:3, :].T
    
    # Project 3D points to 2D image plane using camera intrinsics
    # First, apply perspective projection
    projected_points = intrinsics @ camera_coords.T
    
    # Normalize by the third coordinate (depth)
    projected_points = projected_points / projected_points[2, :]
    
    # Take the first two rows (x and y pixel coordinates)
    pixel_coords = projected_points[:2, :].T
    
    # Draw circles for each projected point
    for point in pixel_coords:
        try:
            cv2.circle(
                output_img, 
                (int(point[0]), int(point[1])), 
                radius=3,  # circle radius
                color=(0, 255, 0),  # green color
                thickness=-1  # filled circle
            )
        except:
            pass
        finally:
            pass
    
    return output_img