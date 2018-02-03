# OpenGL defines
if (SHD_OPENGL)
    if (SHD_OPENGLES2)
        set(SHD_SLANG GLES)
    endif()
    if (SHD_OPENGLES3)
        set(SHD_SLANG GLES)
    endif()
    if (SHD_OPENGL_CORE_PROFILE)
        set(SHD_SLANG GLSL)
    endif()
endif()

# D3D11 defines
if (SHD_D3D11)
    set(SHD_SLANG HLSL)
endif()

# Metal defines
if (SHD_METAL)
    set(SHD_SLANG MSL)
endif()

#-------------------------------------------------------------------------------
#   Wrap shader code generation
#
macro(glsl_shader shd)
    if (DEBUG_SHADERS)
        set(args "{type: 'glsl', debug: 'true', slang: '${SHD_SLANG}'}")
    else()
        set(args "{type: 'glsl', debug: 'false', slang: '${SHD_SLANG}'}")
    endif()
    fips_generate(FROM ${shd} TYPE Shader ARGS ${args})
endmacro()