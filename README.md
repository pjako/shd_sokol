**Warning: The currently generated code is broken, will fix it in the next days**

# Shader cross compiler

Shd is the shader generator from oryol but it just generates the shaders and the reflection informations stored in structs.

## How to write a shader program
- Create a file (choose_a_name).glsl
- Add it to your fips cmake file via 
```CMAKE
glsl_shader(shaders.glsl)
````
- Write a shader
```GLSL
@vs myVS
uniform vsParams {
    mat4 mvp;
};
in vec4 position;
in vec2 texcoord0;
in vec4 color0;
out vec2 uv;
out vec4 color;

void main() {
    gl_Position = mvp * position;
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

## Create sokol shaders from shd shaders

```C
#include "myshaders.h"
#include "sokol_gfx.h"

sg_shader_stage_desc generateSokolShaderDesc(const shd_shader shd) {
    sg_shader_stage_desc shdDesc = {};
    shdDesc.source = shd.source;
    shdDesc.byte_code = shd.binary;
    shdDesc.byte_code_size = shd.size;
    shdDesc.entry = shd.entry;
    for (int i = 0; i < shd.textureCount; ++i) {
        shdDesc.images[i].name = shd.textures[i].name;
        switch (shd.textures[i].type) {
            case (SHD_SAMPLER_TYPE_2D): {
                shdDesc.images[i].type = SG_IMAGETYPE_2D;
                break;
            }
            case (SHD_SAMPLER_TYPE_CUBE): {
                shdDesc.images[i].type = SG_IMAGETYPE_CUBE;
                break;
            }
            case (SHD_SAMPLER_TYPE_ARRAY): {
                shdDesc.images[i].type = SG_IMAGETYPE_ARRAY;
                break;
            }
            case (SHD_SAMPLER_TYPE_3D): {
                shdDesc.images[i].type = SG_IMAGETYPE_3D;
                break;
            }
            default: {
                DF_ASSERT(!"Unknown sampler type");
            }
        }
    }
    
    for (int i = 0; i < shd.uniformBlockCount; ++i) {
        shdDesc.uniform_blocks[i].size = shd.uniformBlocks[i].size;
        for (int j = 0; j < shd.uniformBlocks[i].count; ++j) {
            shdDesc.uniform_blocks[i].uniforms[j].name = shd.uniformBlocks[i].uniforms[j].name;
            shdDesc.uniform_blocks[i].size = shd.uniformBlocks[i].uniforms[j].size;
            switch (shd.uniformBlocks[i].uniforms[j].type) {
                case(SHD_UNIFORM_TYPE_FLOAT): {
                    shdDesc.uniform_blocks[i].uniforms[j].type = SG_UNIFORMTYPE_FLOAT;
                    break;
                }
                case(SHD_UNIFORM_TYPE_VEC2): {
                    shdDesc.uniform_blocks[i].uniforms[j].type = SG_UNIFORMTYPE_FLOAT2;
                    break;
                }
                case(SHD_UNIFORM_TYPE_VEC3): {
                    shdDesc.uniform_blocks[i].uniforms[j].type = SG_UNIFORMTYPE_FLOAT3;
                    break;
                }
                case(SHD_UNIFORM_TYPE_VEC4): {
                    shdDesc.uniform_blocks[i].uniforms[j].type = SG_UNIFORMTYPE_FLOAT4;
                    break;
                }
                case(SHD_UNIFORM_TYPE_MAT4): {
                    shdDesc.uniform_blocks[i].uniforms[j].type = SG_UNIFORMTYPE_MAT4;
                    break;
                }
                default: {
                    assert(!"Unknown Uniform Type");
                }
            }
        }
    }
    return shdDesc;
}

sg_shader_desc generateSokolProgramDesc(const shd_program program) {
    sg_shader_desc programDesc = {};
    programDesc.vs = generateSokolShaderDesc(program.vs);
    programDesc.fs = generateSokolShaderDesc(program.fs);
    return programDesc;
}

void init_program() {
    /* ... */
    const shd_program_collection programCollection = shd_get_programs(SHD_SHADER_TARGET_TYPE_METAL);
    sg_shader_desc shdDsc = generateSokolProgramDesc(*programCollection.programs[0]);
    sg_shader shd = sg_make_shader(&shdDsc);
    /* ... */
}
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
    sg_apply_uniform_block(SG_SHADERSTAGE_VS, 0, &uniformBlock, sizeof(shd_shader_myshader_uniform_vsParams));
}
```

## Define your own Uniform types
```C
#define SHD_MAT4 my_mat4_type
#define SHD_VEC3 my_vec3_type
#include "generated_shader_file_name.h"
```

## Uniform & Input (Attribute) types
Input uses: float, SHD_VEC2, SHD_VEC3, SHD_VEC4
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
