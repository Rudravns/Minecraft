import pygame, os, sys, random
from math import *
import json
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import moderngl

pygame.font.init()
pygame.init()
pygame.display.init()

def time_taken(func):
    def wrapper(*args, **kwargs):
        start_time = pygame.time.get_ticks()
        result = func(*args, **kwargs)
        end_time = pygame.time.get_ticks()
        print(f"Time taken by {func.__name__}: {end_time - start_time} ms")
        return result
        


def get_screen(override=None):
    pygame.init()
    screen_info = pygame.display.Info()
    screen_l, screen_w = screen_info.current_w, screen_info.current_h
    return (screen_l, screen_w) if override == None else override



def save(world_data, path="data.json"):
    """
    Save the world data to a JSON file.
    Converts NumPy arrays to lists for serialization.
    """
    data_to_save = world_data.copy()
    data_to_save["Block_data"] = {}

    # Convert tuple keys to strings and arrays to lists
    for key, chunk in world_data["Block_data"].items():
        data_to_save["Block_data"][f"{key[0]},{key[1]}"] = chunk.tolist()

    # Ensure the folder exists
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    
    # Save JSON once
    with open(path, "w") as f:
        json.dump(data_to_save, f)


def load(path="data.json"):
    """
    Load world data from a JSON file.
    Converts lists back into NumPy arrays and keys back to tuples.
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Convert block data back to NumPy arrays and keys back to tuples
        block_data = {}
        for key_str, chunk_list in data.get("Block_data", {}).items():
            x, z = map(int, key_str.split(","))
            block_data[(x, z)] = np.array(chunk_list, dtype=int)
        data["Block_data"] = block_data

        return data 
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def scale_size(size: float, round_result=True) -> int | float:
    win = pygame.display.get_window_size()
    scale_factor = min(win[0] / 800, win[1] / 600)
    return round(size * scale_factor) if round_result else size * scale_factor


def scale_pos(pos: tuple, round_result=False) -> tuple:
    win = pygame.display.get_window_size()
    scale_factor = min(win[0] / 800, win[1] / 600)
    x = pos[0] * scale_factor
    y = pos[1] * scale_factor
    return (round(x), round(y)) if round_result else (x, y)


def clamp(value, min_value: int | float,
          max_value: int | float) -> int | float:
    return max(min_value, min(max_value, value))



class buttons(pygame.sprite.Sprite):
    """Use to make it Simple buttons with Text"""

    def __init__(self,
                 x,
                 y,
                 font,
                 size,
                 text,
                 color,
                 txtcolor,
                 edge: str | tuple = None,
                 Invisable=False,
                 special_name=None):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.font_name = font
        self.base_size = int(size)
        self.text = text
        self.color = color
        self.txtcolor = txtcolor
        self.edge = edge
        self.scale = 1.0
        self.target_scale = 1.0
        self.scale_speed = 0.05
        self.invisible = Invisable
        self.special_name = special_name
        self.update_surface()

    def change_style(self, txt, color, txtcolor):
        self.color = color
        self.txtcolor = txtcolor
        self.text = txt
        self.update_surface()

    def update_surface(self):
        scaled_size = int(self.base_size * self.scale)
        self.font = pygame.font.Font(
            self.font_name,
            scaled_size) if self.font_name != "" else pygame.font.SysFont(
                self.font_name, scaled_size)
        self.text_surface = self.font.render(str(self.text), True,
                                             self.txtcolor)
        self.text_rect = self.text_surface.get_rect(center=(self.x, self.y))

        self.box_rect = pygame.Rect(self.text_rect.left - 20,
                                    self.text_rect.top - 10,
                                    self.text_rect.width + 40,
                                    self.text_rect.height + 20)

        self.image = pygame.Surface(
            (self.box_rect.width, self.box_rect.height), pygame.SRCALPHA)

        if not self.invisible:
            pygame.draw.rect(self.image,
                             self.color,
                             (0, 0, self.box_rect.width, self.box_rect.height),
                             border_radius=scale_size(10))

            self.image.blit(self.text_surface, (20, 10))
            if self.edge != None:
                pygame.draw.rect(
                    self.image,
                    "black", (0, 0, self.box_rect.width, self.box_rect.height),
                    border_radius=scale_size(10))
            self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self, mouse_pos):
        # Check hover
        if self.box_rect.collidepoint(mouse_pos):
            self.target_scale = 1.2
        else:
            self.target_scale = 1.0

        # Smooth scale interpolation
        if abs(self.scale - self.target_scale) > 0.01:
            self.scale += (self.target_scale - self.scale) * self.scale_speed
            self.update_surface()

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def get_rect(self, topleft=None):
        if topleft:
            temp_rect = self.box_rect.copy()
            temp_rect.topleft = topleft
            return temp_rect
        return self.box_rect

    def __str__(self):
        if self.special_name:
            return self.special_name

pygame.font.init()

_font_cache = {}
_text_cache = {}

def get_text_texture(ctx, text, size, color):
    key = (text, size, color)

    if key in _text_cache:
        return _text_cache[key]

    font = pygame.font.SysFont("Arial", size)
    surf = font.render(text, True, color)
    surf = pygame.transform.flip(surf, False, True)

    tex = ctx.texture(
        surf.get_size(),
        4,
        pygame.image.tostring(surf, "RGBA")
    )

    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    tex.repeat_x = False
    tex.repeat_y = False

    _text_cache[key] = (tex, surf.get_size())
    return _text_cache[key]

def draw_text(text, x, y, size=24, color=(255, 255, 255)):
    # --- font cache ---
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("Arial", size)
    font = _font_cache[size]

    # --- render text to RGBA surface with real transparency ---
    text_surface = font.render(text, True, color)
    surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
    surface.blit(text_surface, (0, 0))

    width, height = surface.get_size()
    pixel_data = pygame.image.tostring(surface, "RGBA", True)

    # --- OpenGL draw ---
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    glWindowPos2i(x, y)
    glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixel_data)

    glDisable(GL_BLEND)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)