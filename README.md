# Shader cross compiler

Shd is the shader generator from oryol but it targets sokol_gfx directly.

## How to write a shader program
- Create a file (choose_a_name).glsl
- Add it to your fips cmake file via 
```CMAKE
glsl_shader(shader.glsl)
````
- Write a shader
```GLSL
@vs myVS
uniform vsParams {
    mat4 proj;
};
in vec4 position;
in vec2 texcoord0;
in vec4 color0;
out vec2 uv;
out vec4 color;

void main() {
    gl_Position = proj * position;
    uv = texcoord0;
    color = color0;
}
@end

@fs myFS
uniform sampler2D tex;
in vec2 uv;
in vec4 color;
out vec4 fragColor;
void main() {
    fragColor = texture(tex, uv) * color;
}
@end

@program MyShader myVS myFS
```
## Use a shader program
```C
void init_program() {
    /* ... */
    sg_shader shd = sg_make_shader(&shd_shader_myshader);
    /* ... */
}
/* ... */
void main_loop() {
    shd_shader_myshader_uniform_vsParams uniformBlock;
    uniformBlock.m01 = 22.0f;
    shd_apply_myshader_vs_uniform_params(&uniformBlock);
}
```
## Uniform Types
This are all uniform types
```C
#ifndef SHD_VEC2
typedef struct {
    SHD_FLOAT x;
    SHD_FLOAT y;
} shd_vec2;
#define SHD_VEC2 shd_vec2
#endif
#ifndef SHD_VEC3
typedef struct {
    SHD_FLOAT x;
    SHD_FLOAT y;
    SHD_FLOAT z;
} shd_vec3;
#define SHD_VEC3 shd_vec3
#endif
#ifndef SHD_VEC4
typedef struct {
    SHD_FLOAT x;
    SHD_FLOAT y;
    SHD_FLOAT z;
    SHD_FLOAT w;
} shd_vec4;
#define SHD_VEC4 shd_vec4
#endif
#ifndef SHD_MAT2
typedef struct {
    SHD_FLOAT m00;
    SHD_FLOAT m01;
    SHD_FLOAT m10;
    SHD_FLOAT m11;
} shd_mat2;
#define SHD_MAT2 shd_mat2
#endif
#ifndef SHD_MAT3
typedef struct {
    SHD_FLOAT m00;
    SHD_FLOAT m01;
    SHD_FLOAT m02;
    SHD_FLOAT m10;
    SHD_FLOAT m11;
    SHD_FLOAT m12;
    SHD_FLOAT m20;
    SHD_FLOAT m21;
    SHD_FLOAT m22;
} shd_mat3;
#define SHD_MAT3 shd_mat3
#endif
#ifndef SHD_MAT4
typedef struct {
    SHD_FLOAT m00;
    SHD_FLOAT m01;
    SHD_FLOAT m02;
    SHD_FLOAT m03;
    SHD_FLOAT m10;
    SHD_FLOAT m11;
    SHD_FLOAT m12;
    SHD_FLOAT m13;
    SHD_FLOAT m20;
    SHD_FLOAT m21;
    SHD_FLOAT m22;
    SHD_FLOAT m23;
    SHD_FLOAT m30;
    SHD_FLOAT m31;
    SHD_FLOAT m32;
    SHD_FLOAT m33;
} shd_mat4;
#define SHD_MAT4 shd_mat4
#endif
```

## Define your own Uniform types
```C
#define SHD_MAT4 my_mat4_type
#define SHD_VEC3 my_mat3_type
#include "generated_shader_file_name.h"
```