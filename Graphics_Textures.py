import numpy as np
from PIL import Image

prefix = ("Block_textures//")
Texs = ["Grass", "Dirt", "Stone", "oak_log", "oak_Leaf", "Wood", "Bedrock", "Glass"]
paths = [ prefix + r + ".png" for r in Texs]
try:
    Image.open(paths[0]).convert("RGBA")
except FileNotFoundError:
    prefix = ("Minecraft//Block_textures//")
    paths.clear()
    paths = [ prefix + r + ".png" for r in Texs]
breaking_animation = [
    "Breaking_ani//breaking_ani_1.png",
    "Breaking_ani//breaking_ani_2.png",
    "Breaking_ani//breaking_ani_3.png",
    "Breaking_ani//breaking_ani_4.png",
]
TARGET_SIZE = (16, 16)


imgs = []
breaking_imgs = []
for p in paths:
    img = Image.open(p).convert("RGBA")
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.NEAREST)
    imgs.append(img)

for p in [prefix + r for r in breaking_animation]:
    img = Image.open(p).convert("RGBA")
    img.putalpha(128)
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.NEAREST)
    
    breaking_imgs.append(img)

w, h = TARGET_SIZE
all_imgs = imgs + breaking_imgs
layers = len(all_imgs)
data = b"".join(img.tobytes() for img in all_imgs)


# -------------------- Cube Mesh --------------------
cube_vertices = np.array([
    # pos              normal        uv     tex_index
    # FRONT (z=-0.5)
    -0.5,-0.5,-0.5,   0,0,-1,   0,0, 1,
     0.5,-0.5,-0.5,   0,0,-1,   1,0, 1,
     0.5, 0.5,-0.5,   0,0,-1,   1,1, 1,
    -0.5,-0.5,-0.5,   0,0,-1,   0,0, 1,
     0.5, 0.5,-0.5,   0,0,-1,   1,1, 1,
    -0.5, 0.5,-0.5,   0,0,-1,   0,1, 1,

    # BACK (z=0.5)
    -0.5,-0.5, 0.5,   0,0,1,    0,0, 1,
     0.5, 0.5, 0.5,   0,0,1,    1,1, 1,
     0.5,-0.5, 0.5,   0,0,1,    1,0, 1,
    -0.5,-0.5, 0.5,   0,0,1,    0,0, 1,
    -0.5, 0.5, 0.5,   0,0,1,    0,1, 1,
     0.5, 0.5, 0.5,   0,0,1,    1,1, 1,

    # LEFT (x=-0.5)
    -0.5,-0.5,-0.5,  -1,0,0,    0,0, 1,
    -0.5, 0.5, 0.5,  -1,0,0,    1,1, 1,
    -0.5,-0.5, 0.5,  -1,0,0,    1,0, 1,
    -0.5,-0.5,-0.5,  -1,0,0,    0,0, 1,
    -0.5, 0.5,-0.5,  -1,0,0,    0,1, 1,
    -0.5, 0.5, 0.5,  -1,0,0,    1,1, 1,

    # RIGHT (x=0.5)
     0.5,-0.5,-0.5,   1,0,0,    0,0, 1,
     0.5,-0.5, 0.5,   1,0,0,    1,0, 1,
     0.5, 0.5, 0.5,   1,0,0,    1,1, 1,
     0.5,-0.5,-0.5,   1,0,0,    0,0, 1,
     0.5, 0.5, 0.5,   1,0,0,    1,1, 1,
     0.5, 0.5,-0.5,   1,0,0,    0,1, 1,

    # TOP (y=0.5, grass)
    -0.5, 0.5,-0.5,   0,1,0,    0,0, 0,
     0.5, 0.5,-0.5,   0,1,0,    1,0, 0,
     0.5, 0.5, 0.5,   0,1,0,    1,1, 0,
    -0.5, 0.5,-0.5,   0,1,0,    0,0, 0,
     0.5, 0.5, 0.5,   0,1,0,    1,1, 0,
    -0.5, 0.5, 0.5,   0,1,0,    0,1, 0,

    # BOTTOM (y=-0.5, stone)
    -0.5,-0.5,-0.5,   0,-1,0,   0,0, 2,
     0.5,-0.5, 0.5,   0,-1,0,   1,1, 2,
     0.5,-0.5,-0.5,   0,-1,0,   1,0, 2,
    -0.5,-0.5,-0.5,   0,-1,0,   0,0, 2,
    -0.5,-0.5, 0.5,   0,-1,0,   0,1, 2,
     0.5,-0.5, 0.5,   0,-1,0,   1,1, 2,
], dtype="f4")

# -------------------- Shaders --------------------
VERTEX_SHADER = """
    #version 330
    in vec3 in_pos;
    in vec3 in_norm;
    in vec2 in_uv;
    in float in_tex;
    
    out vec3 v_norm;
    out vec2 v_uv;
    flat out float v_tex;   // 🔧 FIX
    
    uniform mat4 MVP;
    uniform mat4 Model;
    uniform float overrideTex;
    
    void main() {
        gl_Position = MVP * vec4(in_pos, 1.0);
        v_uv = in_uv;
        v_tex = (overrideTex >= 0.0) ? overrideTex : in_tex;
        v_norm = mat3(transpose(inverse(Model))) * in_norm;
    }

"""

FRAGMENT_SHADER = """
    #version 330
    in vec3 v_norm;
    in vec2 v_uv;
    flat in float v_tex;    // 🔧 FIX
    
    out vec4 fragColor;
    
    uniform sampler2DArray texArray;
    
    void main() {
        vec3 lightDir = normalize(vec3(1.0, 1.0, 1.0));
        float diff = max(dot(normalize(v_norm), lightDir), 0.0);
    
        float ambient = 0.3;
        float light = ambient + diff;
    
        // no interpolation artifacts anymore
        vec4 texColor = texture(texArray, vec3(v_uv, v_tex));
        fragColor = vec4(texColor.rgb * light, texColor.a);
    }

"""
CROSSHAIR_VERT = """
    #version 330
    in vec2 in_pos;
    void main() {
        gl_Position = vec4(in_pos, 0.0, 1.0);
    }
"""

CROSSHAIR_FRAG = """
    #version 330
    out vec4 fragColor;
    void main() {
        fragColor = vec4(1.0, 1.0, 1.0, 1.0);
    }
"""

UI_VERT = """
    #version 330

    in vec2 in_pos;
    in vec2 in_uv;

    uniform mat4 proj;
    uniform mat4 model;

    out vec2 uv;  // pass to fragment shader

    void main() {
        uv = in_uv;
        gl_Position = proj * model * vec4(in_pos, 0.0, 1.0);
    }
"""

UI_FRAG = """
    #version 330
    
    in vec2 uv;
    
    uniform sampler2DArray texArray;
    uniform float texIndex;
    uniform vec4 color;
    
    out vec4 fragColor;
    
    void main() {
        if (texIndex >= 0.0) {
            fragColor = texture(texArray, vec3(uv, texIndex));
        } else {
            fragColor = color;
        }
    }
"""

TEXT_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;

out vec2 v_uv;

uniform mat4 model;
uniform mat4 proj;

void main() {
    v_uv = in_uv;
    gl_Position = proj * model * vec4(in_pos, 0.0, 1.0);
}
"""

TEXT_FRAG = """
#version 330
in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D textTex;  // 👈 2D sampler for fonts
uniform vec4 color;

void main() {
    vec4 tex = texture(textTex, v_uv);
    fragColor = tex * color;
}
"""