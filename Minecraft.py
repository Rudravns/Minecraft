import pygame
import moderngl
import numpy as np
from pyglm import glm
from math import sin, cos
from perlin_noise import PerlinNoise
from typing import *
import random
import threading
import minecraft_classes
import Recipes
from minecraft_classes import get_text_texture
from Graphics_Textures import *
from World import *
from os import system, environ
import Controller
import inventory_manger
import copy
system("cls")


# -------------------- Config --------------------
pygame.init()
pygame.display.init()
pygame.font.init()
pygame.joystick.init()
WIDTH, HEIGHT = 800,600

# -------------------- Renderer --------------------
class Renderer:
    def __init__(self,  location:str = None , seed = random.randint(0, 999999), Render_Distance = 1):
        #os envi
        environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
        environ["SDL_VIDEO_CENTERED"] = "1"


        #------------------- World data/saving -------------------
        self.file_location = ("Minecraft//World_data//"+location+".json")  if location != None else ("Minecraft//World_data//World_"+str(seed)+".json")
        self.world_data = minecraft_classes.load(self.file_location)
        self.save = self.world_data == {}
        self.autosave = True

        if not self.save:
            if self.world_data["seed"] != seed and location != None:
                self.file_location = ("Minecraft//World_data//"+location+"("+str(seed)+").json")
                self.save = True
        self.seed = seed
        self.Render_Distance = Render_Distance
        # -------------------- Window / Input --------------------
        self.width, self.height = WIDTH, HEIGHT
        pygame.display.set_mode((self.width, self.height), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE | pygame.WINDOWDISPLAYCHANGED)
        pygame.display.set_caption("Minecraft V 1.3.5")
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        self.fullscreen = False
        self.windowed_size = (WIDTH, HEIGHT)

        # -------------------- OpenGL Context --------------------
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.ctx.front_face = 'ccw'
        self.ctx.cull_face = 'front'
        self.current_block = 1

        self.chunk_vaos = {}
        self.target_block = None

        # -------------------- Shaders --------------------
        self.prog = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )
        self.prog["overrideTex"].value = -1

        self.cross_prog = self.ctx.program(
            vertex_shader=CROSSHAIR_VERT,
            fragment_shader=CROSSHAIR_FRAG
        )

        # -------------------- 3D Block Cross (World Space) --------------------
        cross_size = 1
        cross_3d = np.array([
            -cross_size, 0, 0,   cross_size, 0, 0,
            0, -cross_size, 0,   0, cross_size, 0,
            0, 0, -cross_size,   0, 0, cross_size,
        ], dtype="f4")

        self.cross3d_vbo = self.ctx.buffer(cross_3d.tobytes())
        self.cross3d_vao = self.ctx.vertex_array(
            self.prog,
            [(self.cross3d_vbo, "3f", "in_pos")]
        )

        # -------------------- Screen Crosshair (2D) --------------------
        s = 0.045
        cross_vertices = np.array([
            -s / 2,  0.0,
            s / 2,  0.0,
            0.0,   -s,
            0.0,    s,
        ], dtype="f4")

        self.cross_vbo = self.ctx.buffer(cross_vertices.tobytes())
        self.cross_vao = self.ctx.vertex_array(
            self.cross_prog,
            [(self.cross_vbo, "2f", "in_pos")]
        )

        # -------------------- Cube Mesh --------------------
        self.vbo = self.ctx.buffer(cube_vertices.tobytes())
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.vbo, "3f 3f 2f 1f", "in_pos", "in_norm", "in_uv", "in_tex")]
        )
        # -------------------- Breaking Overlay Cube --------------------
        self.break_vbo = self.ctx.buffer(cube_vertices.tobytes())
        self.break_vao = self.ctx.vertex_array(
            self.prog,
            [(self.break_vbo, "3f 3f 2f 1f", "in_pos", "in_norm", "in_uv", "in_tex")]
        )


        # -------------------- Texture Array --------------------

        self.tex_array = self.ctx.texture_array(
            (w, h, layers),
            components=4,
            data=data
        )

        self.tex_array.build_mipmaps()
        self.tex_array.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # -------------------- Camera / Timing --------------------
        self.camera = Camera()
        self.clock = pygame.time.Clock()
        self.fly = False
        self.fast_break = False
        self.break_progress = 0.0
        self.last_scroll_time = 0
        self.breaking_block = None
        self.Controller = Controller.Dualsense()

        #----------- Text display ----------------------------
        self.text_prog = self.ctx.program(
            vertex_shader=TEXT_VERT,
            fragment_shader=TEXT_FRAG
        )
        text_quad = np.array([
            0, 0, 0, 0,
            1, 0, 1, 0,
            1, 1, 1, 1,

            0, 0, 0, 0,
            1, 1, 1, 1,
            0, 1, 0, 1,
        ], dtype="f4")

        self.text_vbo = self.ctx.buffer(text_quad.tobytes())
        self.text_vao = self.ctx.vertex_array(
            self.text_prog,
            [(self.text_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        #--------------------- Inventory ----------------------------
        self.inventory = False
        self.inventory_rects = {}
        self.big_crafting_grid_rects = {}
        self.inv_items = None

        self.ui_prog = self.ctx.program(
            vertex_shader=UI_VERT,
            fragment_shader=UI_FRAG
        )
        # Inventory panel (centered)
        w1, h1= 0.6, 0.7
        x_offset, y_offset = 0, 0  # move right and down
        panel = np.array([
            -w1 + x_offset, -h1 + y_offset, 0.0, 0.0,
            w1 + x_offset, -h1 + y_offset, 1.0, 0.0,
            w1 + x_offset,  h1 + y_offset, 1.0, 1.0,
            -w1 + x_offset, -h1 + y_offset, 0.0, 0.0,
            w1 + x_offset,  h1 + y_offset, 1.0, 1.0,
            -w1 + x_offset,  h1 + y_offset, 0.0, 1.0,
        ], dtype="f4")

        self.inv_vbo = self.ctx.buffer(panel.tobytes())
        self.inv_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.inv_vbo, "2f 2f", "in_pos", "in_uv")]
        )
        # -------------------- Inventory Slots --------------------

        slot_size = 0.08
        spacing = 0.045
        self.slot_attr = (slot_size, spacing)
        # Main inventory (9x4)
        inv_grid = self.build_ui_grid(
            cols=9,
            rows=4,
            slot_size=slot_size,
            spacing=spacing+0.003,
            origin=(-0.53, 0)
        )

        self.inv_slots_vbo = self.ctx.buffer(inv_grid.tobytes())
        self.inv_slots_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.inv_slots_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        #---------------- hotbar ----------------
        slot_size = 0.08
        spacing = 0.045
        self.slot_attr = (slot_size, spacing)
        # Main inventory (9x4)
        hotbar_grid = self.build_ui_grid(
            cols=9,
            rows=1,
            slot_size=slot_size,
            spacing=spacing+0.003,
            origin=(-0.53, -(4*(spacing+slot_size))-0.2),
            skip_rects=True
        )

        self.hotbar_vbo = self.ctx.buffer(hotbar_grid.tobytes())
        self.hotbar_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.hotbar_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        #----------------------- hotbar rect -------------------------

        w1, h1= 0.6,0.1

        x_offset, y_offset = 0,  -(4*(spacing+slot_size))-0.25  # move right and down
        panel = np.array([
            -w1 + x_offset, -h1 + y_offset, 0.0, 0.0,
            w1 + x_offset, -h1 + y_offset, 1.0, 0.0,
            w1 + x_offset,  h1 + y_offset, 1.0, 1.0,
            -w1 + x_offset, -h1 + y_offset, 0.0, 0.0,
            w1 + x_offset,  h1 + y_offset, 1.0, 1.0,
            -w1 + x_offset,  h1 + y_offset, 0.0, 1.0,
        ], dtype="f4")

        self.hbv_vbo = self.ctx.buffer(panel.tobytes())
        self.hbv_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.hbv_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        # -------------------- Hotbar Selection Quad --------------------
        sel_w = 0.06  # width of selection quad
        sel_h = 0.08  # height of selection quad

        selection_quad = np.array([
            -sel_w, -sel_h, 0.0, 0.0,
            sel_w, -sel_h, 1.0, 0.0,
            sel_w,  sel_h, 1.0, 1.0,

            -sel_w, -sel_h, 0.0, 0.0,
            sel_w,  sel_h, 1.0, 1.0,
            -sel_w,  sel_h, 0.0, 1.0,
        ], dtype="f4")


        self.sel_vbo = self.ctx.buffer(selection_quad.tobytes())
        self.sel_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.sel_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        # -------------------- Crafting Grid (3x3) --------------------
        craft_grid = self.build_ui_grid(
            cols=3,
            rows=3,
            slot_size=slot_size,
            spacing=spacing,
            origin=(0.1, 0.5)
        )

        self.craft_slots_vbo = self.ctx.buffer(craft_grid.tobytes())
        self.craft_slots_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.craft_slots_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        # -------------------- Crafting Output Slot --------------------
        self.output_slot_quad = self.build_ui_grid(
            cols=1,
            rows=1,
            slot_size=slot_size,
            spacing=0,
            origin=(0.1+(3*(spacing+slot_size)), 0.5-(spacing+0.03+slot_size))
        )

        self.output_slot_vbo = self.ctx.buffer(self.output_slot_quad.tobytes())
        self.output_slot_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.output_slot_vbo, "2f 2f", "in_pos", "in_uv")]
        )
            # -------------------- Inventory Item Quad --------------------
        item_width  = 0.06   # X size
        item_height = 0.1   # Y size

        item_quad = np.array([
            # x, y,           u, v
            0, 0,             0, 0,
            item_width, 0,    1, 0,
            item_width, -item_height, 1, 1,

            0, 0,             0, 0,
            item_width, -item_height, 1, 1,
            0, -item_height,  0, 1,
        ], dtype="f4")


        self.item_vbo = self.ctx.buffer(item_quad.tobytes())
        self.item_vao = self.ctx.vertex_array(
            self.ui_prog,
            [(self.item_vbo, "2f 2f", "in_pos", "in_uv")]
        )


        # --- Drag & Drop state ---
        self.dragging_item = None      # (block_id, count)
        self.mouse_up = False
        self.locked = False
        self.rect_touch_index = None
        self.craft_result = None

        
        # cache slot rects (screen-space)

    def run(self):
        # -------------------- Load or Create World --------------------
        seed = self.seed
        Render_Distance = self.Render_Distance
        self.world_data = minecraft_classes.load(self.file_location)
        if not self.world_data:  # no save found → create new
            self.save = True
            seed = seed or random.randint(1, 999999)
            self.world_data = {
                "seed": seed,
                "Render_Distance": Render_Distance,
                "inventory": copy.deepcopy(inventory_manger.inventory_dict),
                "pos": [self.camera.pos.x, self.camera.pos.y, self.camera.pos.z],
                "Block_data": {}
            }
            minecraft_classes.save(self.world_data, self.file_location)
        else:
            self.save = False
            seed = self.world_data.get("seed", random.randint(0, 999999))
            Render_Distance = self.world_data.get("Render_Distance", Render_Distance)

        # -------------------- Create World --------------------
        world = World(seed=seed)

        # Load chunks if they exist
        if not self.save:
            world.chunks = self.world_data.get("Block_data", {})
            pos = self.world_data.get("pos", [0, 0, 0])
            self.camera.pos = glm.vec3(*pos)
            inventory_manger.inventory_dict = copy.deepcopy(
                self.world_data.get("inventory", inventory_manger.inventory_dict)
            )



        # Generate initial chunk if empty
        if self.save:
            world.generate_chunk(0, 0)

        # Build initial meshes
        for (cx, cz) in world.chunks.keys():
            self.build_chunk_mesh(world, cx, cz)

        # Ensure camera starts above ground
        # make y go up if touching anything but air
        while world.get_block(int(self.camera.pos.x), int(self.camera.pos.y), int(self.camera.pos.z)) != 0:
            self.camera.pos.y += CUBE_SIZE
        self.camera.pos.y += CUBE_SIZE*2


        # -------------------- Main Loop --------------------
        while True:
            dt = self.clock.tick(120) / 1000

            #auto-save
            if pygame.time.get_ticks() % 5000 < 16 and self.autosave:
                minecraft_classes.save({
                "seed": world.seed,
                "Render_Distance": Render_Distance,
                "inventory": copy.deepcopy(inventory_manger.inventory_dict),
                "pos": [self.camera.pos.x, self.camera.pos.y, self.camera.pos.z],
                "Block_data": world.chunks
                }, self.file_location)


            # -------------------- Event Handling --------------------
            for e in pygame.event.get():
                self.Controller.handle_event(e)

                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    # Save before quitting
                    minecraft_classes.save({
                        "seed": world.seed,
                        "Render_Distance": Render_Distance,
                        "inventory": copy.deepcopy(inventory_manger.inventory_dict),
                        "pos": [self.camera.pos.x, self.camera.pos.y, self.camera.pos.z],
                        "Block_data": world.chunks
                    }, self.file_location)
                    pygame.quit()
                    exit()

                if e.type == pygame.VIDEORESIZE:
                    if not self.fullscreen: self.windowed_size = e.size
                    self.width, self.height = e.w, e.h
                    self.ctx.viewport = (0, 0, self.width, self.height)
                    self.build_inventory_slot_rects()

                if e.type == pygame.MOUSEBUTTONUP:
                    self.mouse_up = True
                if e.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_up = False

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_c:
                        self.fly = not self.fly
                    if e.key == pygame.K_r:
                        world = World(seed=seed)
                        world.generate_chunk(0, 0)
                        self.chunk_vaos.clear()
                        self.build_chunk_mesh(world, 0, 0)
                    if e.key == pygame.K_l:
                        pygame.mouse.set_visible(not pygame.mouse.get_visible())
                        pygame.event.set_grab(not pygame.event.get_grab())
                    if e.key == pygame.K_b:
                        self.fast_break = not self.fast_break
                    if e.key == pygame.K_e:
                        self.inventory = not self.inventory
                        if self.inventory:
                            self.build_inventory_slot_rects()
                    if e.key == pygame.K_F11:
                        self.toggle_fullscreen()

                if e.type == pygame.JOYBUTTONDOWN:

                    if e.button == 3:
                        self.inventory = not self.inventory
                        if self.inventory:
                            self.build_inventory_slot_rects()
                    if e.button == 10: # R1 ID from your dictionary
                        self.current_block = (self.current_block % 9 ) + 1
                    elif e.button == 9: # L1 ID from your dictionary
                        self.current_block = 9 if self.current_block == 1 else self.current_block - 1

            if self.Controller.joysticks:
                mpos = pygame.mouse.get_pos()
                cpos = self.Controller.get_axis(0, "left")
                pygame.mouse.set_pos(minecraft_classes.clamp(mpos[0] + cpos[0] * 10, 0, self.width-1), minecraft_classes.clamp(mpos[1] + cpos[1] * 10,0, self.height-1))
                #clamp pos




            # -------------------- Movement & Interaction --------------------
            self.movement(world, Render_Distance, dt)

           # -------------------- Rendering --------------------
            proj = glm.perspective(glm.radians(70), self.width / self.height, 0.1, 100)
            view = self.camera.view()

            self.ctx.clear(0.53, 0.81, 0.92)
            self.tex_array.use(0)
            self.prog["texArray"] = 0

            # 3D world
            self.render_world(world)
            self.render_breaking_overlay(world)
            # self.render_block_cross()  # optional
            self.render_crosshair()

            # -------------------- UI --------------------
            if self.inventory:
                self.inventory_logic()  # renders inventory properly
            else:
                self.render_hotbar()

            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.CULL_FACE)
            sx = 10  # pixels from left
            sy = 10
            size = 50
            # draw 2D overlays like FPS, coordinates
            self.draw_text_gl(f"FPS: {int(self.clock.get_fps())}",sx,sy ,size,(0, 0, 0))
            self.draw_text_gl(f"CORDS: {int(self.camera.pos.x)}, {int(self.camera.pos.y)}, {int(self.camera.pos.z)}", sx, sy + 30, size, (0,0,0))
            look = self.camera.look_dir()
            self.draw_text_gl(f"Direction: {look[0]:.2f}, {look[1]:.2f}, {look[2]:.2f}", sx, sy + 60, size, (0,0,0))
            self.draw_text_gl(f"Seed: {seed}", sx, sy +90, size, (0,0,0))
            self.draw_text_gl(f"Chunk Coords: {int(self.camera.pos.x) // CHUNK_X}, {int(self.camera.pos.z) // CHUNK_Z}", sx, sy +  120, size, (0,0,0))
            self.draw_text_gl(f"Inventory: {self.inventory}", sx, sy + 150, size, (0,0,0))
            self.draw_text_gl(f"box: {self.rect_touch_index}", sx, sy + 180, size, (0,0,0))
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.CULL_FACE)

            pygame.display.flip()

    def movement(self, world, Render_Distance, dt):
        mx, my = pygame.mouse.get_rel()
        if self.inventory: return
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)


        if self.Controller.joysticks:
            controller_sensitivity = 10.0  # Degrees per second
            axes_r = self.Controller.get_axis(0, "right")

            # Apply rotation using Delta Time (dt) so it's consistent
            self.camera.yaw += axes_r[0] * controller_sensitivity * dt
            self.camera.pitch -= axes_r[1] * controller_sensitivity * dt

        self.camera.yaw += mx * self.camera.sensitivity
        self.camera.pitch -= my * self.camera.sensitivity

        if self.fly: self.camera.velocity.y = 0

        #clamp camara pitch
        self.camera.pitch = max(-1.5, min(1.5, self.camera.pitch))

        keys = pygame.key.get_pressed()
        accel = glm.vec3(0, 0, 0)

        origin = self.camera.pos
        direction = self.camera.look_dir() #- glm.vec3(0, EYE_HEIGHT/2, 0)


        hit = raycast(world, origin, direction)
        self.target_block = hit
        place_pos = raycast_place(world, origin, direction)
        self.place_block_target = place_pos

        if (pygame.mouse.get_pressed()[2] or self.Controller.get_trigger(0, "l2") != 0) and self.place_block_target:
            block_type = inventory_manger.inventory_dict[str(self.current_block)]
            if can_place_block(self.camera, self.place_block_target) and block_type != None:
                px, py, pz = self.place_block_target
                world.place_block(px, py, pz, block_type=int(block_type[0]))
                self.build_chunk_mesh(world, px // CHUNK_X, pz // CHUNK_Z)
                inventory_manger.remove_item(block_type[0])


        if (pygame.mouse.get_pressed()[0] or self.Controller.get_trigger(0, "r2") != 0) and hit:
            if self.breaking_block != hit:
                self.breaking_block = hit
                self.break_progress = 0.0

            speed = self.break_speed(world)
            if speed > 0: self.break_progress += dt * self.clock.get_fps()

            if self.break_progress >= speed:
                x, y, z = hit
                item = world.get_block(int(x), int(y), int(z))
                inventory_manger.add_item(item)
                world.break_block(x, y, z)

                self.build_chunk_mesh(world, x // CHUNK_X, z // CHUNK_Z)
                self.break_progress = 0.0
                self.breaking_block = None
        else:
            self.break_progress = 0.0
            self.breaking_block = None



        # WASD movement

        if keys[pygame.K_w]: accel += self.camera.forward() * self.camera.speed * dt
        if keys[pygame.K_s]: accel -= self.camera.forward() * self.camera.speed * dt
        if keys[pygame.K_a]: accel -= self.camera.right() * self.camera.speed * dt
        if keys[pygame.K_d]: accel += self.camera.right() * self.camera.speed * dt
        if keys[pygame.K_LSHIFT] and self.fly: self.camera.velocity.y -= 15*dt
        if keys[pygame.K_SPACE] and self.fly: self.camera.pos.y += self.camera.jump_height*dt
        if self.Controller.joysticks:
            walkingx, walkingy = self.Controller.get_axis(0, "left")
            round(walkingx,1); round(walkingy,1)
            accel += self.camera.forward() * (self.camera.speed*-walkingy) * dt
            accel += self.camera.right() * (self.camera.speed * walkingx) * dt
            if self.Controller.get_button("l3") and self.fly: self.camera.pos.y += 15*dt
            if self.Controller.get_button("r3") and self.fly: self.camera.velocity.y -= 15*dt




        #blocks selection
        if keys[pygame.K_1]: self.current_block = 1
        if keys[pygame.K_2]: self.current_block = 2
        if keys[pygame.K_3]: self.current_block = 3
        if keys[pygame.K_4]: self.current_block = 4
        if keys[pygame.K_5]: self.current_block = 5
        if keys[pygame.K_6]: self.current_block = 6
        if keys[pygame.K_7]: self.current_block = 7
        if keys[pygame.K_8]: self.current_block = 8
        if keys[pygame.K_9]: self.current_block = 9







        # Apply horizontal velocity
        self.camera.velocity.x = accel.x
        self.camera.velocity.z = accel.z

        # Apply gravity
        if not self.fly: self.camera.velocity.y -= 0.5*dt  # gravity

        # Jump
        if (keys[pygame.K_SPACE] or self.Controller.get_button("cross")) and (self.camera.on_ground and not self.fly ):
            self.camera.velocity.y = self.camera.jump_height*dt  # jump speed

        # Predict next positions per axis for collision checking
        new_pos = glm.vec3(self.camera.pos)

        cam_chunk_x = int(self.camera.pos.x) // CHUNK_X
        cam_chunk_z = int(self.camera.pos.z) // CHUNK_Z

        # look direction
        look = self.camera.look_dir()

        # predict chunk in front (only X/Z)
        front_x = int(self.camera.pos.x + look.x * CHUNK_X) // CHUNK_X
        front_z = int(self.camera.pos.z + look.z * CHUNK_Z) // CHUNK_Z

        if (front_x, front_z) not in world.chunks:
            world.generate_chunk(front_x, front_z)

        world.ensure_chunks_around(cam_chunk_x, cam_chunk_z, radius=Render_Distance)
        world.ensure_chunks_around(front_x, front_z, radius=0)

       # Define half-size for collision checks
        half_size = CAMERA_SIZE * 0.5

        # X-axis
        next_pos = glm.vec3(new_pos.x + self.camera.velocity.x, new_pos.y, new_pos.z)
        if not world.check_collision(next_pos, half_size):
            new_pos.x += self.camera.velocity.x
        else:
            self.camera.velocity.x = 0

        # Y-axis
        next_pos = glm.vec3(new_pos.x, new_pos.y + self.camera.velocity.y, new_pos.z)
        if not world.check_collision(next_pos, half_size):
            new_pos.y += self.camera.velocity.y
            self.camera.on_ground = False
        else:
            if self.camera.velocity.y < 0:
                self.camera.on_ground = True
            self.camera.velocity.y = 0

        # Z-axis
        next_pos = glm.vec3(new_pos.x, new_pos.y, new_pos.z + self.camera.velocity.z)
        if not world.check_collision(next_pos, half_size):
            new_pos.z += self.camera.velocity.z
        else:
            self.camera.velocity.z = 0


        # Update camera position
        self.camera.pos = new_pos
        # Build meshes for any newly generated chunks
        for (cx, cz) in world.chunks.keys():
            if (cx, cz) not in self.chunk_vaos:
                self.build_chunk_mesh(world, cx, cz)

    def render_world(self, world):
        proj = glm.perspective(glm.radians(70), self.width / self.height, 0.1, 100)
        view = self.camera.view()

        self.prog["Model"].write(glm.mat4(1).to_bytes())

        for vao in self.chunk_vaos.values():
            self.prog["MVP"].write((proj * view).to_bytes())
            vao.render()

    def build_chunk_mesh(self, world, cx, cz):
        chunk = world.chunks[(cx, cz)]
        mesh = build_chunk_mesh(chunk, cx, cz)

        if len(mesh) == 0:
            return

        vbo = self.ctx.buffer(mesh.tobytes())
        vao = self.ctx.vertex_array(
            self.prog,
            [(vbo, "3f 3f 2f 1f", "in_pos", "in_norm", "in_uv", "in_tex")]
        )

        self.chunk_vaos[(cx, cz)] = vao

    def render_crosshair(self):
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.cross_vao.render(mode=moderngl.LINES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def render_block_cross(self):
        if not self.target_block:
            return

        x, y, z = self.target_block

        # center of the block
        model = glm.translate(glm.mat4(1), glm.vec3(x + 0.5, y + 0.5, z + 0.5))

        proj = glm.perspective(glm.radians(70), self.width / self.height, 0.1, 100)
        view = self.camera.view()

        self.prog["Model"].write(model.to_bytes())
        self.prog["MVP"].write((proj * view * model).to_bytes())

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.cross3d_vao.render(mode=moderngl.LINES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def break_speed(self, world):
        #get the number of the block that will break

        num = world.get_block(self.target_block[0], self.target_block[1], self.target_block[2])
        fps = self.clock.get_fps()
        breaking_times = {
            "HAND": {
                1: 500,
                2: 500,
                3: 2000,
                4: 500,
                5: 200,
                6: 500,
                7: -1,
                },
            "WOOD_PICKAXE": {
                1: 500,
                2: 500,
                3: 1300,
                4: 500,
                5: 200,
                6: 500,
                7: -1,
                },
            "Creative": {
                1: 1,
                2: 1,
                3: 1,
                4: 1,
                5: 1,
                6: 1,
                7: -1,
            }
        }
        dt = fps/1000

        return (breaking_times["HAND"][num]*dt) if not self.fast_break else (breaking_times["Creative"][num]*dt)

    def render_breaking_overlay(self, world):
        if not self.breaking_block:
            return

        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        x, y, z = self.breaking_block

        progress = self.break_progress / self.break_speed(world)
        stage = min(int(progress * 4), 3)

        crack_tex_index = len(imgs) + stage

        model = glm.mat4(1)
        model = glm.translate(model, glm.vec3(x,y-EYE_HEIGHT,z))
        model = glm.scale(model, glm.vec3(1.01))

        proj = glm.perspective(glm.radians(70), self.width / self.height, 0.1, 100)
        view = self.camera.view()

        self.prog["Model"].write(model.to_bytes())
        self.prog["MVP"].write((proj * view * model).to_bytes())

        self.prog["overrideTex"].value = crack_tex_index

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.break_vao.render()

        self.ctx.disable(moderngl.BLEND)

        # CRITICAL RESET
        self.prog["overrideTex"].value = -1.0

    def inventory_logic(self):
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

        proj = glm.ortho(-1, 1, -1, 1)
        self.ui_prog["model"].write(glm.mat4(1).to_bytes())
        self.ui_prog["proj"].write(proj.to_bytes())
        self.ui_prog["texIndex"].value = -1

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        added_alpha = 0


        # Background panel
        self.ui_prog["color"].value = (0.12, 0.12, 0.12, 0.9-added_alpha)
        self.inv_vao.render()

        # Inventory slots
        self.ui_prog["color"].value = (0.25, 0.25, 0.25, 0.95-added_alpha)
        self.inv_slots_vao.render()

        # Crafting grid
        self.ui_prog["color"].value = (0.3, 0.3, 0.3, 0.95-added_alpha)
        self.craft_slots_vao.render()

        # Output slot
        self.ui_prog["color"].value = (0.4, 0.4, 0.4, 1.0-added_alpha)
        self.output_slot_vao.render()


        # Inventory items
        self.render_inventory_items()

        mouse = pygame.mouse.get_pos()
        hovered = self.get_hovered_slot(mouse)
        hovered_key = None

        if isinstance(hovered, int):
            # Convert visual index to inventory key
            idx = hovered + 9 * (3 - 2 * ((hovered - 1) // 9))
            hovered_key = str(idx)
        elif isinstance(hovered, str):
            hovered_key = hovered

        # Handle Drag Start
        if (pygame.mouse.get_pressed()[0] == 1 or self.Controller.get_button("cross",0 )) and not self.locked and hovered_key:
            source_dict = None
            if hovered_key.startswith("craft_") and hovered_key != "craft_result":
                source_dict = inventory_manger.Crafting_grid
            elif hovered_key == "craft_result":
                pass # Result slot logic if needed
            else:
                source_dict = inventory_manger.inventory_dict
            
            if source_dict and source_dict.get(hovered_key) is not None:
                self.locked = True
                self.dragging_item = hovered_key
            elif hovered_key == "craft_result":
                res = inventory_manger.Crafting_grid.get("craft_result")
                if res:
                    inventory_manger.cursor_slot = res
                    self.dragging_item = "cursor_slot"
                    self.locked = True
                    
                    for i in range(1, 10):
                        k = f"craft_{i}"
                        if inventory_manger.Crafting_grid[k]:
                            inventory_manger.Crafting_grid[k][1] -= 1
                            if inventory_manger.Crafting_grid[k][1] <= 0:
                                inventory_manger.Crafting_grid[k] = None
                    
                    new_res = Recipes.craft(inventory_manger.Crafting_grid)
                    inventory_manger.Crafting_grid["craft_result"] = list(new_res) if new_res != (0,0) else None

        # Handle Drag End (Drop)
        if (pygame.mouse.get_pressed()[0] == 0 and not self.Controller.get_button("cross",0 )):
            if self.dragging_item == "cursor_slot":
                if hovered_key and not hovered_key.startswith("craft_result"):
                    tgt_dict = inventory_manger.Crafting_grid if hovered_key.startswith("craft_") else inventory_manger.inventory_dict
                    current = tgt_dict.get(hovered_key)
                    cursor = inventory_manger.cursor_slot
                    
                    if current is None:
                        tgt_dict[hovered_key] = cursor
                        inventory_manger.cursor_slot = None
                    elif current[0] == cursor[0]:
                        current[1] += cursor[1]
                        inventory_manger.cursor_slot = None
                    else:
                        inventory_manger.add_item(cursor[0], cursor[1])
                        inventory_manger.cursor_slot = None
                else:
                    if inventory_manger.cursor_slot:
                        inventory_manger.add_item(inventory_manger.cursor_slot[0], inventory_manger.cursor_slot[1])
                        inventory_manger.cursor_slot = None
                
                self.dragging_item = None
                self.locked = False
                
                new_res = Recipes.craft(inventory_manger.Crafting_grid)
                inventory_manger.Crafting_grid["craft_result"] = list(new_res) if new_res != (0,0) else None

            elif self.dragging_item and hovered_key:
                # Identify source and target dicts
                src_dict = inventory_manger.Crafting_grid if self.dragging_item.startswith("craft_") else inventory_manger.inventory_dict
                tgt_dict = None
                
                if hovered_key.startswith("craft_") and hovered_key != "craft_result":
                    tgt_dict = inventory_manger.Crafting_grid
                elif not hovered_key.startswith("craft_"):
                    tgt_dict = inventory_manger.inventory_dict
                
                if tgt_dict is not None:
                    # Swap items
                    src_item = src_dict[self.dragging_item]
                    tgt_item = tgt_dict[hovered_key]
                    
                    src_dict[self.dragging_item] = tgt_item
                    tgt_dict[hovered_key] = src_item
                    
                    # Update crafting result
                    new_res = Recipes.craft(inventory_manger.Crafting_grid)
                    inventory_manger.Crafting_grid["craft_result"] = list(new_res) if new_res != (0,0) else None
            
            self.locked = False
            self.dragging_item = None

        self.rect_touch_index = self.get_hovered_slot(mouse, "craft3x3")
        #print([list(self.slot_rects.keys())[i] for i in range(-10, 0, 1)])

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)

    def build_ui_grid(self, cols, rows, slot_size, spacing, origin, skip_rects=False):
        verts = []
        size_offset = 0.04
        ox, oy = origin

        for r in range(rows):
            for c in range(cols):
                x = ox + c * (slot_size + spacing)
                y = oy - r * (slot_size + spacing + 0.03)

                # UVs for full quad
                u0, v0 = 0.0, 0.0
                u1, v1 = 1.0, 1.0
                if not skip_rects and len(list(self.inventory_rects.keys())) < 36:
                    self.inventory_rects[len(list(self.inventory_rects.keys()))+1] = np.array([
                    x, y, u0, v0,
                    x + slot_size, y, u1, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,

                    x, y, u0, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,
                    x, y - (slot_size + size_offset), u0, v1,
                ], dtype="f4")
                
                elif not skip_rects and len(list(self.big_crafting_grid_rects.keys())) < 9:
                    self.big_crafting_grid_rects[len(list(self.big_crafting_grid_rects.keys()))+1] = np.array([
                    x, y, u0, v0,
                    x + slot_size, y, u1, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,

                    x, y, u0, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,
                    x, y - (slot_size + size_offset), u0, v1,
                ], dtype="f4")

                verts.extend([
                    x, y, u0, v0,
                    x + slot_size, y, u1, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,

                    x, y, u0, v0,
                    x + slot_size, y - (slot_size + size_offset), u1, v1,
                    x, y - (slot_size + size_offset), u0, v1,
                ])
        return np.array(verts, dtype="f4")

    def render_inventory_items(self, mode = 'inv'):
        self.tex_array.use(0)
        self.ui_prog["texArray"].value = 0

        slot_size, spacing = self.slot_attr
        ox, oy = (-0.53-0.03, 0)   # same origin as inventory grid




        item_width  = 0.06   # X size
        item_height = 0.1    # Y size
        max_rows = 4         # Number of inventory rows

        slot_index = 0
        for slot, data in inventory_manger.inventory_dict.items():

            if slot_index == 10 and mode == 'hb': break
            if data is None:
                slot_index += 1
                continue

            block_id, count = data

            # Column and row (invert row for bottom → top)
            col = slot_index % 9
            row = (max_rows - 1) - (slot_index // 9)

            # Slot position
            slot_x = ox + col * (slot_size + spacing+ 0.004)
            slot_y = oy - row * (slot_size + spacing + 0.03)

            # Center item in slot
            x = slot_x + (slot_size - item_width+ 0.05) * 0.5
            y = slot_y - (slot_size - item_height+0.05) * 0.5
            if mode == 'hb':
                y -= 0.23
            # Render item
           
            if slot == self.dragging_item:
                mx, my = pygame.mouse.get_pos()
                x, y = self.screen_to_ui(mx, my)
                x-=item_width/2; y+=item_height/2




            model = glm.translate(glm.mat4(1), glm.vec3(x, y, 0))
            self.ui_prog["model"].write(model.to_bytes())
            self.ui_prog["texIndex"].value = block_id - 1
            self.item_vao.render()



            slot_index += 1

            # Reset texIndex
        self.ui_prog["texIndex"].value = -1

        slot_index = 0
        for slot, data in inventory_manger.inventory_dict.items():
            if slot_index == 10 and mode == 'hb': break
            if data is None:
                slot_index += 1
                continue

            block_id, count = data

            # Column and row (invert row for bottom → top)
            col = slot_index % 9
            row = (max_rows - 1) - (slot_index // 9)

            # Slot position
            slot_x = ox + col * (slot_size + spacing+ 0.004)
            slot_y = oy - row * (slot_size + spacing + 0.03)

            # Center item in slot
            x = slot_x + (slot_size - item_width+ 0.05) * 0.5
            y = slot_y - (slot_size - item_height+0.05) * 0.5
            if mode == 'hb':
                y -= 0.23
            # Render item

            if slot == self.dragging_item:
                mx, my = pygame.mouse.get_pos()
                x, y = self.screen_to_ui(mx, my)
                x-=item_width/2; y+=item_height/2
            # Convert UI position to screen space
            sx, sy = self.ui_to_screen(
                (x + item_width * 0.6) + 0.025,   # move text to bottom-right of item
                (y - item_height * 0.8)+0.03
            )
            self.draw_text_gl(str(count), sx, sy, 50, (255,255,255))
            self.draw_text_gl(str(count), sx+1, sy+1, 50, (0,0,0))


            slot_index += 1
            
        # --- Render Crafting Text ---
        if mode == 'inv':
            for key, data in inventory_manger.Crafting_grid.items():
                if data is None: continue
                block_id, count = data
                
                if key == "craft_result":
                    ix = 0.443 + (0.08 - 0.06 + 0.05) * 0.5
                    iy = 0.345 - (0.08 - 0.1 + 0.05) * 0.5
                    
                    model = glm.translate(glm.mat4(1), glm.vec3(ix, iy, 0))
                    self.ui_prog["model"].write(model.to_bytes())
                    self.ui_prog["texIndex"].value = block_id - 1
                    self.item_vao.render()
                    
                    sx, sy = self.ui_to_screen(
                        (ix + 0.06 * 0.6) + 0.025,
                        (iy - 0.1 * 0.8) + 0.03
                    )
                    self.draw_text_gl(str(count), sx, sy, 50, (255,255,255))
                    self.draw_text_gl(str(count), sx+1, sy+1, 50, (0,0,0))
                    continue

                idx = int(key.split("_")[1])
                if idx in self.big_crafting_grid_rects:
                    quad = self.big_crafting_grid_rects[idx]
                    x, y = quad[0], quad[1]
                    ix = x + (0.08 - 0.06 + 0.05) * 0.5
                    iy = y - (0.08 - 0.1 + 0.05) * 0.5
                    
                    if key == self.dragging_item:
                        mx, my = pygame.mouse.get_pos()
                        ix, iy = self.screen_to_ui(mx, my)
                        ix -= 0.06/2; iy += 0.1/2
                    
                    sx, sy = self.ui_to_screen(
                        (ix + 0.06 * 0.6) + 0.025,
                        (iy - 0.1 * 0.8) + 0.03
                    )

                    model = glm.translate(glm.mat4(1), glm.vec3(ix - 0.06/2, iy, 0))
                    self.ui_prog["model"].write(model.to_bytes())
                    self.ui_prog["texIndex"].value = block_id - 1
                    self.item_vao.render()
                    self.draw_text_gl(str(count), sx, sy, 50, (255,255,255))
                    self.draw_text_gl(str(count), sx+1, sy+1, 50, (0,0,0))

        if inventory_manger.cursor_slot:
            block_id, count = inventory_manger.cursor_slot
            mx, my = pygame.mouse.get_pos()
            ix, iy = self.screen_to_ui(mx, my)
            ix -= 0.06/2; iy += 0.1/2
            
            model = glm.translate(glm.mat4(1), glm.vec3(ix, iy, 0))
            self.ui_prog["model"].write(model.to_bytes())
            self.ui_prog["texIndex"].value = block_id - 1
            self.item_vao.render()
            
            sx, sy = self.ui_to_screen(
                (ix + 0.06 * 0.6) + 0.025,
                (iy - 0.1 * 0.8) + 0.03
            )
            self.draw_text_gl(str(count), sx, sy, 50, (255,255,255))
            self.draw_text_gl(str(count), sx+1, sy+1, 50, (0,0,0))

    def render_selected_item_quad(self):
        slot_size, spacing = self.slot_attr

        # Hotbar origin (same as hotbar grid)
        ox = -0.53
        oy = -(4 * (spacing + slot_size)) - 0.2

        # Current hotbar index (0–8)
        index = self.current_block - 1

        # Slot position
        x = ox + index * (slot_size + spacing + 0.003) + slot_size / 2
        y = oy - slot_size / 2 - 0.01

        # UI projection
        proj = glm.ortho(-1, 1, -1, 1)
        model = glm.translate(glm.mat4(1), glm.vec3(x, y, 0))

        self.ui_prog["proj"].write(proj.to_bytes())
        self.ui_prog["model"].write(model.to_bytes())
        self.ui_prog["texIndex"].value = -1
        self.ui_prog["color"].value = (1.0, 1.0, 1.0, 0.5)

        self.sel_vao.render()

    def render_hotbar(self):
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

        proj = glm.ortho(-1, 1, -1, 1)
        self.ui_prog["model"].write(glm.mat4(1).to_bytes())
        self.ui_prog["proj"].write(proj.to_bytes())
        self.ui_prog["texIndex"].value = -1

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        added_alpha = 0

        #background
        self.ui_prog["color"].value = (0.12, 0.12, 0.12, 0.9-added_alpha)
        self.hbv_vao.render()

        # Inventory slots
        self.ui_prog["color"].value = (0.25, 0.25, 0.25, 0.95-added_alpha)
        self.hotbar_vao.render()

        self.render_selected_item_quad()


        # Inventory items
        self.render_inventory_items('hb')
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)

    def build_inventory_slot_rects(self):
        self.slot_rects = {}

        for index, quad in self.inventory_rects.items():
            # quad shape: (6 vertices * (x,y,u,v)) → take x,y only
            verts = quad.reshape(-1, 4)[:, :2]

            # Convert UI coords → screen coords
            screen_pts = np.array([
                self.ui_to_screen(x, y) for x, y in verts
            ])

            min_x, min_y = screen_pts.min(axis=0)
            max_x, max_y = screen_pts.max(axis=0)

            self.slot_rects[index] = np.array([
                min_x, min_y, max_x, max_y
            ], dtype=np.int32)

        for index, quad in self.big_crafting_grid_rects.items():
            # quad shape: (6 vertices * (x,y,u,v)) → take x,y only
            verts = quad.reshape(-1, 4)[:, :2]

            # Convert UI coords → screen coords
            screen_pts = np.array([
                self.ui_to_screen(x, y) for x, y in verts
            ])

            min_x, min_y = screen_pts.min(axis=0)
            max_x, max_y = screen_pts.max(axis=0)

            self.slot_rects[f"craft_{index}"] = np.array([
                min_x, min_y, max_x, max_y
            ], dtype=np.int32)

        #res_square
        quad = self.output_slot_quad.reshape(-1, 4)[:, :2]  # take x,y

        screen_pts = np.array([
            self.ui_to_screen(x, y) for x, y in quad
        ])

        min_x, min_y = screen_pts.min(axis=0)
        max_x, max_y = screen_pts.max(axis=0)

        self.slot_rects["craft_result"] = np.array(
            [min_x, min_y, max_x, max_y],
            dtype=np.int32
        )
       
    def mouse_over_rect(self, mouse, rect):
        mx, my = mouse
        x1, y1, x2, y2 = rect
        return (x1 <= mx <= x2) and (y1 <= my <= y2)

    def get_hovered_slot(self, mouse, mode = 'inv')-> int|None:
        """
        :param mouse: mouse position
        :param mode: inv for inventory, craft3x3 for crafting grid
        """

        if mode == 'inv':
            for index, rect in self.slot_rects.items():
                if self.mouse_over_rect(mouse, rect):
                    return index
            return None
        elif mode == 'craft3x3':
            for index, rect in self.slot_rects.items():
                if self.mouse_over_rect(mouse, rect):
                    return index
            return None
        else: return None

    def ui_to_screen(self, x, y):
        screen_x = int((x + 1) * 0.5 * self.width)
        screen_y = int((1 - (y + 1) * 0.5) * self.height)
        return screen_x, screen_y

    def screen_to_ui(self, mx, my):
        ux = (mx / self.width) * 2 - 1
        uy = -((my / self.height) * 2 - 1)
        return ux, uy

    def draw_text_gl(self, text, x, y, size=24, color=(255, 255, 255)):
        tex, (w, h) = get_text_texture(self.ctx, text, size, color)

        nx = (x / self.width) * 2 - 1
        ny = 1 - (y / self.height) * 2
        sx = w / self.width
        sy = h / self.height

        model = glm.mat4(1)
        model = glm.translate(model, glm.vec3(nx, ny - sy, 0))
        model = glm.scale(model, glm.vec3(sx, sy, 1))

        proj = glm.ortho(-1, 1, -1, 1)

        self.ctx.disable(moderngl.DEPTH_TEST)

        self.text_prog["model"].write(model.to_bytes())
        self.text_prog["proj"].write(proj.to_bytes())

        self.text_prog["color"].value = (1, 1, 1, 1)

        tex.use(0)
        self.ui_prog["texArray"].value = 0

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.text_vao.render()

        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

        if self.fullscreen:
            pygame.display.set_mode(
                (0, 0),
                pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN
            )
        else:
            pygame.display.set_mode(
                self.windowed_size,
                pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
            )

        # IMPORTANT: get actual framebuffer size
        self.width, self.height = pygame.display.get_window_size()

        # Update OpenGL viewport
        self.ctx.viewport = (0, 0, self.width, self.height)
        self.build_inventory_slot_rects()


# -------------------- Entry --------------------
if __name__ == "__main__":
    
    #Renderer(location="New_World", seed = 101).run()
    Renderer(location="my", seed=6, Render_Distance=5).run() #can chose seed; no seed = random seed 
    #Mineclone(5)
