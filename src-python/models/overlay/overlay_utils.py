import numpy as np

def toHomogeneous(matrix):
    homogeneous_matrix = np.vstack([matrix, [0, 0, 0, 1]])
    return homogeneous_matrix

# 移動行列を生成する関数
def calcTranslationMatrix(translation):
    tx, ty, tz = translation
    return np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ])

# X軸周りの回転行列を生成する関数
def calcRotationMatrixX(angle):
    c = np.cos(np.pi/180*angle)
    s = np.sin(np.pi/180*angle)
    return np.array([
        [1, 0, 0, 0],
        [0, c, -s, 0],
        [0, s, c, 0],
        [0, 0, 0, 1]
    ])

# Y軸周りの回転行列を生成する関数
def calcRotationMatrixY(angle):
    c = np.cos(np.pi/180*angle)
    s = np.sin(np.pi/180*angle)
    return np.array([
        [c, 0, s, 0],
        [0, 1, 0, 0],
        [-s, 0, c, 0],
        [0, 0, 0, 1]
    ])

# Z軸周りの回転行列を生成する関数
def calcRotationMatrixZ(angle):
    c = np.cos(np.pi/180*angle)
    s = np.sin(np.pi/180*angle)
    return np.array([
        [c, -s, 0, 0],
        [s, c, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

# 3x4行列の座標を基準として回転や移動を行う関数
def transform_matrix(base_matrix, translation, rotation):
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

def euler_to_rotation_matrix(angles):
    phi = angles[0] * np.pi / 180
    theta = angles[1] * np.pi / 180
    psi = angles[2]* np.pi / 180
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