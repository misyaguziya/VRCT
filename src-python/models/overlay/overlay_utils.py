"""Utility functions for 3D matrix transformations required for overlay positioning."""
import numpy as np
from numpy import ndarray
from typing import Tuple

def toHomogeneous(matrix: ndarray) -> ndarray:
    """
    Converts a 3x4 transformation matrix to a 4x4 homogeneous matrix.

    Args:
        matrix: A 3x4 NumPy array representing the transformation matrix.

    Returns:
        A 4x4 NumPy array representing the homogeneous transformation matrix.
    """
    homogeneous_matrix = np.vstack([matrix, [0, 0, 0, 1]])
    return homogeneous_matrix

def calcTranslationMatrix(translation: Tuple[float, float, float]) -> ndarray:
    """
    Generates a 4x4 translation matrix.

    Args:
        translation: A tuple (tx, ty, tz) representing the translation vector.

    Returns:
        A 4x4 NumPy array representing the translation matrix.
    """
    tx, ty, tz = translation
    return np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ], dtype=float)

def calcRotationMatrixX(angle: float) -> ndarray:
    """
    Generates a 4x4 rotation matrix around the X-axis.

    Args:
        angle: The rotation angle in degrees.

    Returns:
        A 4x4 NumPy array representing the rotation matrix.
    """
    c = np.cos(np.deg2rad(angle)) # Use np.deg2rad for clarity
    s = np.sin(np.deg2rad(angle))
    return np.array([
        [1, 0, 0, 0],
        [0, c, -s, 0],
        [0, s, c, 0],
        [0, 0, 0, 1]
    ], dtype=float)

def calcRotationMatrixY(angle: float) -> ndarray:
    """
    Generates a 4x4 rotation matrix around the Y-axis.

    Args:
        angle: The rotation angle in degrees.

    Returns:
        A 4x4 NumPy array representing the rotation matrix.
    """
    c = np.cos(np.deg2rad(angle))
    s = np.sin(np.deg2rad(angle))
    return np.array([
        [c, 0, s, 0],
        [0, 1, 0, 0],
        [-s, 0, c, 0],
        [0, 0, 0, 1]
    ], dtype=float)

def calcRotationMatrixZ(angle: float) -> ndarray:
    """
    Generates a 4x4 rotation matrix around the Z-axis.

    Args:
        angle: The rotation angle in degrees.

    Returns:
        A 4x4 NumPy array representing the rotation matrix.
    """
    c = np.cos(np.deg2rad(angle))
    s = np.sin(np.deg2rad(angle))
    return np.array([
        [c, -s, 0, 0],
        [s, c, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ], dtype=float)

def transform_matrix(base_matrix: ndarray, translation: Tuple[float, float, float], rotation: Tuple[float, float, float]) -> ndarray:
    """
    Applies translation and rotation to a base 3x4 transformation matrix.

    The rotation is applied first, then the translation relative to the base matrix's original orientation.
    The final transformation is base_matrix * rotation_matrix * translation_matrix.
    However, the original implementation composes it as base_matrix * (translation_part_of_combined * rotation_part_of_combined)
    Let's re-verify the intended order. The original code structure suggests base * combined_local_transform.
    The current implementation applies rotation to the identity matrix, then translation, then multiplies by base.
    It should be: homogeneous_base_matrix @ combined_transformation_matrix
    where combined_transformation_matrix is T * R.

    Args:
        base_matrix: A 3x4 NumPy array, the initial transformation matrix.
        translation: A tuple (tx, ty, tz) for local translation.
        rotation: A tuple (rx, ry, rz) for local rotation angles in degrees (X, Y, Z order).

    Returns:
        A 3x4 NumPy array representing the new transformation matrix.
    """
    homogeneous_base_matrix = toHomogeneous(base_matrix)
    
    # Create combined rotation matrix
    rotation_matrix_x = calcRotationMatrixX(rotation[0])
    rotation_matrix_y = calcRotationMatrixY(rotation[1])
    rotation_matrix_z = calcRotationMatrixZ(rotation[2])
    # Order: ZYX for Euler angles often means applying Z, then Y, then X rotation locally.
    # So, R = Rz @ Ry @ Rx
    rotation_matrix = np.dot(rotation_matrix_z, np.dot(rotation_matrix_y, rotation_matrix_x))

    # Create translation matrix
    translation_matrix = calcTranslationMatrix(translation)

    # Combine local transformations: T @ R (apply rotation first, then translation in local frame)
    # Or R @ T (apply translation first, then rotation in local frame)
    # The original code's `transformation_matrix = translation_matrix.copy(); transformation_matrix[:3, :3] = rotation_matrix[:3, :3]`
    # effectively creates a matrix that has the rotation of `rotation_matrix` and translation of `translation_matrix`.
    # This is equivalent to T_world_local * R_local if applied as M_new = M_base * M_local_combined
    
    # Let's assume the goal is to apply a local rotation, then a local translation.
    # This means the combined local transform is T_local * R_local.
    # M_combined_local = np.dot(translation_matrix, rotation_matrix)
    
    # The original code's approach:
    # It takes the rotation part from the combined rotation and the translation part from the translation_matrix.
    # This creates a matrix M_local = [R_local | t_local ]
    #                                  [  0    |   1   ]
    local_transformation_matrix = np.eye(4)
    local_transformation_matrix[:3,:3] = rotation_matrix[:3,:3]
    local_transformation_matrix[:3, 3] = translation_matrix[:3, 3]

    result_matrix_homogeneous = np.dot(homogeneous_base_matrix, local_transformation_matrix)
    return result_matrix_homogeneous[:3, :]


def euler_to_rotation_matrix(angles: Tuple[float, float, float]) -> ndarray:
    """
    Converts Euler angles (in degrees) to a 3x3 rotation matrix.
    The order of rotation is assumed to be X, then Y, then Z (intrinsic).
    This corresponds to R = Rz * Ry * Rx for extrinsic rotations or a specific
    convention for intrinsic (e.g. Tait-Bryan ZYX). The original code implements Rz @ Ry @ Rx.

    Args:
        angles: A tuple (phi, theta, psi) representing rotations around X, Y, Z axes in degrees.

    Returns:
        A 3x3 NumPy array representing the rotation matrix.
    """
    phi = np.deg2rad(angles[0])   # Roll (X-axis rotation)
    theta = np.deg2rad(angles[1]) # Pitch (Y-axis rotation)
    psi = np.deg2rad(angles[2])   # Yaw (Z-axis rotation)
    
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(phi), -np.sin(phi)],
                    [0, np.sin(phi), np.cos(phi)]], dtype=float)
    R_y = np.array([[np.cos(theta), 0, np.sin(theta)],
                    [0, 1, 0],
                    [-np.sin(theta), 0, np.cos(theta)]], dtype=float)
    R_z = np.array([[np.cos(psi), -np.sin(psi), 0],
                    [np.sin(psi), np.cos(psi), 0],
                    [0, 0, 1]], dtype=float)
    
    # R = Rz Ry Rx (standard for many applications, e.g. aerospace yaw, pitch, roll)
    rotation_matrix = np.dot(R_z, np.dot(R_y, R_x))
    return rotation_matrix

if __name__ == "__main__":
    base_matrix = np.array([
        [1, 0, 0, 1],
        [0, 1, 0, 1],
        [0, 0, 1, 1]
    ])
    translation = [1, 2, 3]
    rotation = [0, 0, 90]
    result_matrix = transform_matrix(base_matrix, translation, rotation)
    print(result_matrix)