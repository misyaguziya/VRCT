import numpy as np
from typing import Sequence


def toHomogeneous(matrix: np.ndarray) -> np.ndarray:
    """Convert a 3x4 base matrix to a 4x4 homogeneous matrix.

    Args:
        matrix: 3x4 numpy array

    Returns:
        4x4 numpy array with last row [0, 0, 0, 1]
    """
    homogeneous_matrix = np.vstack([matrix, [0, 0, 0, 1]])
    return homogeneous_matrix

# 移動行列を生成する関数
def calcTranslationMatrix(translation: Sequence[float]) -> np.ndarray:
    """Create a 4x4 translation matrix from a 3-element translation.

    Args:
        translation: (tx, ty, tz)

    Returns:
        4x4 numpy translation matrix
    """
    tx, ty, tz = translation
    return np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ])

# X軸周りの回転行列を生成する関数
def calcRotationMatrixX(angle: float) -> np.ndarray:
    """Rotation matrix around X axis for given angle in degrees."""
    c = np.cos(np.pi / 180 * angle)
    s = np.sin(np.pi / 180 * angle)
    return np.array([
        [1, 0, 0, 0],
        [0, c, -s, 0],
        [0, s, c, 0],
        [0, 0, 0, 1]
    ])

# Y軸周りの回転行列を生成する関数
def calcRotationMatrixY(angle: float) -> np.ndarray:
    """Rotation matrix around Y axis for given angle in degrees."""
    c = np.cos(np.pi / 180 * angle)
    s = np.sin(np.pi / 180 * angle)
    return np.array([
        [c, 0, s, 0],
        [0, 1, 0, 0],
        [-s, 0, c, 0],
        [0, 0, 0, 1]
    ])

# Z軸周りの回転行列を生成する関数
def calcRotationMatrixZ(angle: float) -> np.ndarray:
    """Rotation matrix around Z axis for given angle in degrees."""
    c = np.cos(np.pi / 180 * angle)
    s = np.sin(np.pi / 180 * angle)
    return np.array([
        [c, -s, 0, 0],
        [s, c, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

# 3x4行列の座標を基準として回転や移動を行う関数
def transform_matrix(base_matrix: np.ndarray, translation: Sequence[float], rotation: Sequence[float]) -> np.ndarray:
    """Apply translation and Euler rotations to a 3x4 base matrix.

    Args:
        base_matrix: 3x4 base transform matrix
        translation: (tx, ty, tz)
        rotation: (x_deg, y_deg, z_deg)

    Returns:
        Transformed 3x4 matrix (numpy.ndarray)
    """
    homogeneous_base_matrix = toHomogeneous(base_matrix)
    translation_matrix = calcTranslationMatrix(translation)
    rotation_matrix_x = calcRotationMatrixX(rotation[0])
    rotation_matrix_y = calcRotationMatrixY(rotation[1])
    rotation_matrix_z = calcRotationMatrixZ(rotation[2])
    rotation_matrix = np.dot(rotation_matrix_z, np.dot(rotation_matrix_y, rotation_matrix_x))
    transformation_matrix = translation_matrix.copy()
    transformation_matrix[:3, :3] = rotation_matrix[:3, :3]
    result_matrix = np.dot(homogeneous_base_matrix, transformation_matrix)
    return result_matrix[:3, :]

def euler_to_rotation_matrix(angles: Sequence[float]) -> np.ndarray:
    """Convert Euler angles in degrees to a 3x3 rotation matrix.

    Args:
        angles: (x_deg, y_deg, z_deg)

    Returns:
        3x3 rotation matrix
    """
    phi = angles[0] * np.pi / 180
    theta = angles[1] * np.pi / 180
    psi = angles[2] * np.pi / 180
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(phi), -np.sin(phi)],
                    [0, np.sin(phi), np.cos(phi)]])
    R_y = np.array([[np.cos(theta), 0, np.sin(theta)],
                    [0, 1, 0],
                    [-np.sin(theta), 0, np.cos(theta)]])
    R_z = np.array([[np.cos(psi), -np.sin(psi), 0],
                    [np.sin(psi), np.cos(psi), 0],
                    [0, 0, 1]])
    return np.dot(R_z, np.dot(R_y, R_x))

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