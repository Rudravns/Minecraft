import moderngl
import numpy as np
from pyglm import glm
import pygame
from math import sin, cos, floor, ceil
from perlin_noise import PerlinNoise
import random
from PIL import Image
import threading
import minecraft_classes
from Graphics_Textures import *


# -------------------- Config --------------------
WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
CHUNK_X, CHUNK_Y, CHUNK_Z = 16,20,16
CUBE_SIZE = 1.0
CAMERA_SIZE = glm.vec3(-0.5, 0.5, -0.5)
EYE_HEIGHT = 0.7
 



# -------- Vertex layout --------
FLOATS_PER_VERTEX = 9
VERTS_PER_FACE = 6

# Reshape ONCE
cube_vertices = cube_vertices.reshape(-1, FLOATS_PER_VERTEX)

# Extract faces (NOW 2D)
FACE_FRONT  = cube_vertices[0:6]
FACE_BACK   = cube_vertices[6:12]
FACE_LEFT   = cube_vertices[12:18]
FACE_RIGHT  = cube_vertices[18:24]
FACE_TOP    = cube_vertices[24:30]
FACE_BOTTOM = cube_vertices[30:36]

assert FACE_FRONT.ndim == 2, FACE_FRONT.shape
assert FACE_FRONT.shape == (6, 9), FACE_FRONT.shape

Max_break_dist = 13.0
#------------------CHUNK MESH----------------------------
def build_chunk_mesh(chunk, chunk_x, chunk_z):
    vertices = []

    for x in range(CHUNK_X):
        for y in range(CHUNK_Y):
            for z in range(CHUNK_Z):
                block = chunk[x, y, z]
                if block == 0:
                    continue

                wx = chunk_x * CHUNK_X + x
                wy = y
                wz = chunk_z * CHUNK_Z + z

                # FRONT
                if is_air(chunk, x, y, z - 1):
                    vertices.extend(translate_face(FACE_FRONT, wx, wy, wz, block))

                # BACK
                if is_air(chunk, x, y, z + 1):
                    vertices.extend(translate_face(FACE_BACK, wx, wy, wz, block))

                # LEFT
                if is_air(chunk, x - 1, y, z):
                    vertices.extend(translate_face(FACE_LEFT, wx, wy, wz, block))

                # RIGHT
                if is_air(chunk, x + 1, y, z):
                    vertices.extend(translate_face(FACE_RIGHT, wx, wy, wz, block))

                # TOP
                if is_air(chunk, x, y + 1, z):
                    vertices.extend(translate_face(FACE_TOP, wx, wy, wz, block))

                # BOTTOM
                if is_air(chunk, x, y - 1, z):
                    vertices.extend(translate_face(FACE_BOTTOM, wx, wy, wz, block))

    return np.array(vertices, dtype="f4")

def is_air(chunk, x, y, z):
    if x < 0 or x >= CHUNK_X:
        return True
    if y < 0 or y >= CHUNK_Y:
        return True
    if z < 0 or z >= CHUNK_Z:
        return True
    return chunk[x, y, z] == 0

def translate_face(face, wx, wy, wz, block):
    out = face.copy()

    out[:, 0] += wx
    out[:, 1] += (wy-EYE_HEIGHT)
    out[:, 2] += wz

    out[:, 8] = block - 1

    return out.flatten()

def raycast(world, origin, direction, max_dist=Max_break_dist, step=0.05):
    pos = glm.vec3(origin)

    for _ in range(int(max_dist / step)):
        pos += direction * step

        bx = round(pos.x)
        by = round(pos.y + EYE_HEIGHT)
        bz = round(pos.z)

        if world.get_block(bx, by, bz) != 0:
            return bx, by, bz

    return None

def raycast_place(world, origin, direction, max_dist=Max_break_dist, step=0.05):
    pos = glm.vec3(origin)
    
    last_bx = round(pos.x)
    last_by = round(pos.y + EYE_HEIGHT)
    last_bz = round(pos.z)

    for _ in range(int(max_dist / step)):
        pos += direction * step

        bx = round(pos.x)
        by = round(pos.y + EYE_HEIGHT)
        bz = round(pos.z)

        if world.get_block(bx, by, bz) != 0:
            return (last_bx, last_by, last_bz)
        
        last_bx, last_by, last_bz = bx, by, bz

    return None

def aabb_intersect(min_a, max_a, min_b, max_b):
    return (
        min_a.x <= max_b.x and max_a.x >= min_b.x and
        min_a.y <= max_b.y and max_a.y >= min_b.y and
        min_a.z <= max_b.z and max_a.z >= min_b.z
    )

def can_place_block(camera, block_pos):
    bx, by, bz = block_pos

    # Block AABB
    block_min = glm.vec3(bx, by, bz)
    block_max = block_min + glm.vec3(1, 1, 1)

    # Player AABB
    block_placing_cam_size = glm.vec3(0.7, 1.5, 0.7)
    player_min = camera.pos - block_placing_cam_size
    player_max = camera.pos + block_placing_cam_size

    return not aabb_intersect(block_min, block_max, player_min, player_max)

# -------------------- Camera --------------------
class Camera:
    def __init__(self):
        self.pos = glm.vec3(4, CHUNK_Y+2, 4)
        self.yaw = 0
        self.pitch = 0
        self.speed = 8 
        self.sensitivity = 0.003
        self.velocity = glm.vec3(0, 0, 0)
        self.on_ground = False
        self.jump_height = 13

    def forward(self):
        return glm.vec3(sin(self.yaw), 0, -cos(self.yaw))

    def right(self):
        return glm.normalize(glm.cross(self.forward(), glm.vec3(0,1,0)))

    def up(self):
        return glm.vec3(0,1,0)

    def view(self):
        dir = glm.vec3(
            sin(self.yaw)*cos(self.pitch),
            sin(self.pitch),
            -cos(self.yaw)*cos(self.pitch)
        )
        return glm.lookAt(self.pos, self.pos + dir, glm.vec3(0,1,0))

    def look_dir(self):
        return glm.normalize(glm.vec3(
            sin(self.yaw) * cos(self.pitch),
            sin(self.pitch),
            -cos(self.yaw) * cos(self.pitch)
        ))



# -------------------- World / Terrain --------------------
class World:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.noise = PerlinNoise(octaves=4, seed=self.seed)
        self.chunks = {}

    def generate_chunk(self, chunk_x, chunk_z):
        chunk = np.zeros((CHUNK_X, CHUNK_Y, CHUNK_Z), dtype=int)

        for x in range(CHUNK_X):
            for z in range(CHUNK_Z):

                world_x = chunk_x * CHUNK_X + x
                world_z = chunk_z * CHUNK_Z + z

                height = int(
                    (self.noise([world_x / 50, world_z / 50]) + 1) / 2 * (CHUNK_Y - 1)
                )

                # --- Terrain ---
                for y in range(CHUNK_Y):
                    if y > height:
                        block = 0 #air
                    elif y == height:
                        block = 1
                    elif y > height - 3:
                        block = 2
                    elif y == 0:
                        block = 7
                    else: block = 3


                    chunk[x, y, z] = block

                # --- Tree spawn (AFTER terrain is done) ---
                if random.randint(0, 100) < 2:  # 2% chance
                    radius = 3
                    if x - radius >= 0 and x + radius < CHUNK_X and z - radius >= 0 and z + radius < CHUNK_Z:
                        self._place_tree_in_chunk(chunk, x, height + 1, z)




        self.chunks[(chunk_x, chunk_z)] = chunk
        self.dirty = True

    def get_block(self, x, y, z):
        """Get block type at world coordinates."""
        chunk_x, local_x = divmod(x, CHUNK_X)
        chunk_z, local_z = divmod(z, CHUNK_Z)

        if (chunk_x, chunk_z) not in self.chunks:
            self.generate_chunk(chunk_x, chunk_z)

        if 0 <= y < CHUNK_Y:
            return self.chunks[(chunk_x, chunk_z)][local_x, y, local_z]
        return 0
    
    
    def check_collision(self, pos, size):
        min_corner = pos - size
        max_corner = pos + size

        # Determine chunk the camera is in
        chunk_x = int(pos.x) // CHUNK_X
        chunk_z = int(pos.z) // CHUNK_Z

        if (chunk_x, chunk_z) not in self.chunks:
            return False  # no chunk = no collision

        chunk = self.chunks[(chunk_x, chunk_z)]

        # Convert world coords → local chunk coords
        min_x = int(np.floor(min_corner.x)) - chunk_x * CHUNK_X
        max_x = int(np.ceil (max_corner.x)) - chunk_x * CHUNK_X
        min_z = int(np.floor(min_corner.z)) - chunk_z * CHUNK_Z
        max_z = int(np.ceil (max_corner.z)) - chunk_z * CHUNK_Z

        min_y = int(np.floor(min_corner.y))
        max_y = int(np.ceil (max_corner.y))

        # Clamp to chunk bounds
        min_x = max(0, min(CHUNK_X - 1, min_x))
        max_x = max(0, min(CHUNK_X - 1, max_x))
        min_z = max(0, min(CHUNK_Z - 1, min_z))
        max_z = max(0, min(CHUNK_Z - 1, max_z))
        min_y = max(0, min(CHUNK_Y - 1, min_y))
        max_y = max(0, min(CHUNK_Y - 1, max_y))

        # Check blocks
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    if chunk[x, y, z] != 0:
                        return True

        return False

    def ensure_chunks_around(self, chunk_x, chunk_z, radius=1):
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                key = (chunk_x + dx, chunk_z + dz)
                if key not in self.chunks:
                    self.generate_chunk(*key)

    def break_block(self, x, y, z):
        chunk_x, local_x = divmod(x, CHUNK_X)
        chunk_z, local_z = divmod(z, CHUNK_Z)
        chunk = self.chunks[(chunk_x, chunk_z)]
        chunk[local_x, y, local_z] = 0
    
    def place_block(self, x, y, z, block_type=1):
        """
        Place a block at the given world coordinates.
        Automatically generates the chunk if it doesn't exist.
        """
        # Determine which chunk this block belongs to
        x, y, z = int(x), int(y), int(z)
        chunk_x, local_x = divmod(x, CHUNK_X)
        chunk_z, local_z = divmod(z, CHUNK_Z)

        if (chunk_x, chunk_z) not in self.chunks:
            self.generate_chunk(chunk_x, chunk_z)

        chunk = self.chunks[(chunk_x, chunk_z)]
        if 0 <= y < CHUNK_Y:
            chunk[local_x, y, local_z] = block_type

    def _place_tree_in_chunk(self, chunk, x, y, z):
        trunk_height = random.randint(4, 6)

        # --- Trunk ---
        for i in range(trunk_height):
            ty = y + i
            if ty < CHUNK_Y:
                chunk[x, ty, z] = 4  # log

        top = y + trunk_height - 1

        # --- Leaves (bottom → top) ---
        leaf_layers = [
            (0, 3),
            (1, 2),
            (2, 1),
        ]

        for dy, radius in leaf_layers:
            ly = top + dy
            if not (0 <= ly < CHUNK_Y):
                continue

            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) + abs(dz) <= radius:
                        lx = x + dx
                        lz = z + dz

                        if (
                            0 <= lx < CHUNK_X and
                            0 <= lz < CHUNK_Z
                        ):
                            if chunk[lx, ly, lz] == 0:
                                chunk[lx, ly, lz] = 5  # leaves
                        
