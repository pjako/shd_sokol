'''
Code generator for shader libraries.
'''

Version = 1

import os, platform, json
import genutil as util
from util import glslcompiler, shdc
from mod import log
import zlib # only for crc32
DEFAULT_UNIFORM_TYPES_DEFINE = '''
#ifndef SHD_API
#define SHD_API extern
#endif
#ifndef SHD_FLOAT
#define SHD_FLOAT float
#endif
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
'''
if platform.system() == 'Windows' :
    from util import hlslcompiler

if platform.system() == 'Darwin' :
    from util import metalcompiler

slVersions = {
    'GLSL': ['glsl330'],
    'GLES': ['glsl100', 'glsles3'],
    'MSL':  ['metal'],
    'HLSL': ['hlsl']
}

oryolSlangTypes = {
    'glsl100': 'Oryol::ShaderLang::GLSL100',
    'glsl330': 'Oryol::ShaderLang::GLSL330',
    'glsles3': 'Oryol::ShaderLang::GLSLES3',
    'hlsl':    'Oryol::ShaderLang::HLSL5',
    'metal':   'Oryol::ShaderLang::Metal'
}

def isGLSL(sl):
    return sl in ['glsl100', 'glsl330', 'glsles3']

def isHLSL(sl):
    return sl == 'hlsl'

def isMetal(sl):
    return sl == 'metal'

validVsInNames = [
    'position', 'normal', 'texcoord0', 'texcoord1', 'texcoord2', 'texcoord3',
    'tangent', 'binormal', 'weights', 'indices', 'color0', 'color1',
    'instance0', 'instance1', 'instance2', 'instance3'
]
validInOutTypes = [ 'float', 'vec2', 'vec3', 'vec4' ]
validUniformTypes = [ 'mat4', 'mat2', 'vec4', 'vec3', 'vec2', 'float' ]

# size of uniform array types must currently be multiple of 16,
# because of std140 padding rules
validUniformArrayTypes = [ 'mat4', 'mat2', 'vec4' ]

uniformCType = {
    'float': 'SHD_FLOAT',
    'vec2':  'SHD_VEC2',
    'vec3':  'SHD_VEC3',
    'vec4':  'SHD_VEC4',
    'mat2':  'SHD_MAT2',
    'mat3':  'SHD_MAT3',
    'mat4':  'SHD_MAT4',
}

uniformSokolTypes = {
    'float': 'SG_UNIFORMTYPE_FLOAT',
    'vec2':  'SG_UNIFORMTYPE_VEC2',
    'vec3':  'SG_UNIFORMTYPE_VEC3',
    'vec4':  'SG_UNIFORMTYPE_VEC4',
    'mat2':  'SG_UNIFORMTYPE_MAT2',
    'mat3':  'SG_UNIFORMTYPE_MAT3',
    'mat4':  'SG_UNIFORMTYPE_MAT4',

}

uniformCSize = {
    'float': 4,
    'vec2':  8,
    'vec3':  12,
    'vec4':  16,
    'mat2':  16,
    'mat3':  36,
    'mat4':  64,
}

attrOryolType = {
    'float': 'shd_vertex_format_float',
    'vec2':  'shd_vertex_format_float2',
    'vec3':  'shd_vertex_format_float3',
    'vec4':  'shd_vertex_format_float4'
}

attrOryolName = {
    'position':  'Oryol::VertexAttr::Position',
    'normal':    'Oryol::VertexAttr::Normal',
    'texcoord0': 'Oryol::VertexAttr::TexCoord0',
    'texcoord1': 'Oryol::VertexAttr::TexCoord1',
    'texcoord2': 'Oryol::VertexAttr::TexCoord2',
    'texcoord3': 'Oryol::VertexAttr::TexCoord3',
    'tangent':   'Oryol::VertexAttr::Tangent',
    'binormal':  'Oryol::VertexAttr::Binormal',
    'weights':   'Oryol::VertexAttr::Weights',
    'indices':   'Oryol::VertexAttr::Indices',
    'color0':    'Oryol::VertexAttr::Color0',
    'color1':    'Oryol::VertexAttr::Color1',
    'instance0': 'Oryol::VertexAttr::Instance0',
    'instance1': 'Oryol::VertexAttr::Instance1',
    'instance2': 'Oryol::VertexAttr::Instance2',
    'instance3': 'Oryol::VertexAttr::Instance3'
}

validTextureTypes = [
    'sampler2D', 'samplerCube', 'sampler3D', 'sampler2DArray'
]

texOryolType = {
    'sampler2D':      'Oryol::TextureType::Texture2D',
    'samplerCube':    'Oryol::TextureType::TextureCube',
    'sampler3D':      'Oryol::TextureType::Texture3D',
    'sampler2DArray': 'Oryol::TextureType::TextureArray',
}

texSokolType = {
    'sampler2D':      'SG_IMAGETYPE_2D',
    'samplerCube':    'SG_IMAGETYPE_CUBE',
    'sampler3D':      'SG_IMAGETYPE_3D',
    'sampler2DArray': 'SG_IMAGETYPE_ARRAY',
}
#-------------------------------------------------------------------------------
class Line :
    def __init__(self, content, path='', lineNumber=0) :
        self.content = content
        self.include = None         # name of an included block
        self.path = path
        self.lineNumber = lineNumber

#-------------------------------------------------------------------------------
class Snippet :
    def __init__(self) :
        self.name = None
        self.lines = []

#-------------------------------------------------------------------------------
class Block(Snippet) :
    def __init__(self, name) :
        Snippet.__init__(self)
        self.name = name

    def getTag(self) :
        return 'block'

#-------------------------------------------------------------------------------
class Shader(Snippet) :
    def __init__(self, name) :
        Snippet.__init__(self)
        self.name = name
        self.slReflection = {}  # reflection by shader language 
        self.generatedSource = None

#-------------------------------------------------------------------------------
class VertexShader(Shader) :
    def __init__(self, name) :
        Shader.__init__(self, name)

    def getTag(self) :
        return 'vs' 

#-------------------------------------------------------------------------------
class FragmentShader(Shader) :
    def __init__(self, name) :
        Shader.__init__(self, name)

    def getTag(self) :
        return 'fs'

#-------------------------------------------------------------------------------
class Program() :
    def __init__(self, name, vs, fs, filePath, lineNumber) :
        self.name = name
        self.vs = vs
        self.fs = fs
        self.filePath = filePath
        self.lineNumber = lineNumber        

    def getTag(self) :
        return 'program'

#-------------------------------------------------------------------------------
class Parser :
    def __init__(self, shaderLib) :
        self.shaderLib = shaderLib
        self.fileName = None
        self.lineNumber = 0
        self.current = None
        self.stack = []
        self.inComment = False

    def stripComments(self, line) :
        '''
        Remove comments from a single line, can carry
        over to next or from previous line.
        '''
        done = False
        while not done :
            # if currently in comment, look for end-of-comment
            if self.inComment :
                endIndex = line.find('*/')
                if endIndex == -1 :
                    # entire line is comment
                    if '/*' in line or '//' in line :
                        util.fmtError('comment in comment!')
                    else :
                        return ''
                else :
                    comment = line[:endIndex+2]
                    if '/*' in comment or '//' in comment :
                        util.fmtError('comment in comment!')
                    else :
                        line = line[endIndex+2:]
                        self.inComment = False

            # clip off winged comment (if exists)
            wingedIndex = line.find('//')
            if wingedIndex != -1 :
                line = line[:wingedIndex]

            # look for start of comment
            startIndex = line.find('/*')
            if startIndex != -1 :
                # ...and for the matching end...
                endIndex = line.find('*/', startIndex)
                if endIndex != -1 :
                    line = line[:startIndex] + line[endIndex+2:]
                else :
                    # comment carries over to next line
                    self.inComment = True
                    line = line[:startIndex]
                    done = True
            else :
                # no comment until end of line, done
                done = True;
        line = line.strip(' \t\n\r')
        return line

    def push(self, obj) :
        self.stack.append(self.current)
        self.current = obj

    def pop(self) :
        self.current = self.stack.pop();

    def onBlock(self, args) :
        if len(args) != 1 :
            util.fmtError("@block must have 1 arg (name)")
        if self.current is not None :
            util.fmtError("@block must be at top level (missing @end in '{}'?)".format(self.current.name))
        name = args[0]
        if name in self.shaderLib.blocks :
            util.fmtError("@block '{}' already defined".format(name))
        block = Block(name)
        self.shaderLib.blocks[name] = block
        self.push(block)

    def onVertexShader(self, args) :
        if len(args) != 1:
            util.fmtError("@vs must have 1 arg (name)")
        if self.current is not None :
            util.fmtError("cannot nest @vs (missing @end in '{}'?)".format(self.current.name))
        name = args[0]
        if name in self.shaderLib.vertexShaders :
            util.fmtError("@vs {} already defined".format(name))
        vs = VertexShader(name)
        self.shaderLib.shaders.append(vs)
        self.shaderLib.vertexShaders[name] = vs
        self.push(vs)        

    def onFragmentShader(self, args) :
        if len(args) != 1:
            util.fmtError("@fs must have 1 arg (name)")
        if self.current is not None :
            util.fmtError("cannot nest @fs (missing @end in '{}'?)".format(self.current.name))
        name = args[0]
        if name in self.shaderLib.fragmentShaders :
            util.fmtError("@fs {} already defined!".format(name))
        fs = FragmentShader(name)
        self.shaderLib.shaders.append(fs)
        self.shaderLib.fragmentShaders[name] = fs
        self.push(fs)

    def onProgram(self, args) :        
        if len(args) != 3:
            util.fmtError("@program must have 3 args (name vs fs)")
        if self.current is not None :
            util.fmtError("cannot nest @program (missing @end tag in '{}'?)".format(self.current.name))
        name = args[0]
        vs = args[1]
        fs = args[2]
        prog = Program(name, vs, fs, self.fileName, self.lineNumber)
        self.shaderLib.programs[name] = prog

    def onInclude(self, args) :
        if len(args) != 1:
            util.fmtError("@include must have 1 arg (name of included block)")
        if not self.current or not self.current.getTag() in ['vs', 'fs'] :
            util.fmtError("@include must come after @vs or @fs!")
        if self.current:
            l = Line(None, self.fileName, self.lineNumber)
            l.include = args[0]
            self.current.lines.append(l)

    def onEnd(self, args) :
        if not self.current or not self.current.getTag() in ['block', 'vs', 'fs'] :
            util.fmtError("@end must come after @block, @vs or @fs!")
        if len(args) != 0:
            util.fmtError("@end must not have arguments")
        if self.current.getTag() in ['block', 'vs', 'fs'] and len(self.current.lines) == 0 :
            util.fmtError("no source code lines in @block, @vs or @fs section")
        self.pop()

    def parseLine(self, line) :
        line = self.stripComments(line)
        if line != '':
            tagStartIndex = line.find('@')
            if tagStartIndex != -1 :
                if tagStartIndex > 0 :
                    util.fmtError("only whitespace allowed in front of tag")
                if line.find(';') != -1 :
                    util.fmtError("no semicolons allowed in tag lines")
                tagAndArgs = line[tagStartIndex+1 :].split()
                tag = tagAndArgs[0]
                args = tagAndArgs[1:]
                if tag == 'block':
                    self.onBlock(args)
                elif tag == 'vs':
                    self.onVertexShader(args)
                elif tag == 'fs':
                    self.onFragmentShader(args)
                elif tag == 'include':
                    self.onInclude(args)
                elif tag == 'program':
                    self.onProgram(args)
                elif tag == 'end':
                    self.onEnd(args)
                else :
                    util.fmtError("unrecognized @ tag '{}'".format(tag))
            elif self.current is not None:
                self.current.lines.append(Line(line, self.fileName, self.lineNumber))

    def parseSource(self, fileName) :
        f = open(fileName, 'r')
        self.fileName = fileName
        self.lineNumber = 0
        for line in f :
            util.setErrorLocation(self.fileName, self.lineNumber)
            self.parseLine(line)
            self.lineNumber += 1
        f.close()
        if self.current is not None :
            util.fmtError('missing @end at end of file')

#-------------------------------------------------------------------------------
class ShaderLibrary :
    '''
    This represents the entire shader lib.
    '''
    def __init__(self, inputs) :
        self.sources = inputs
        self.blocks = {}
        self.shaders = []
        self.vertexShaders = {}
        self.fragmentShaders = {}
        self.programs = {}
        self.current = None

    def parseSources(self) :
        parser = Parser(self)
        for source in self.sources :            
            parser.parseSource(source)

    def validate(self, slangs) :
        '''
        Runs additional validation check after programs are resolved and before
        shader code is generated:

        - check whether each vs and fs is part of a program
        - check vertex shader inputs for valid types and names
        - check whether vertex shader output matches fragment shader input
        '''
        for shd in self.shaders:
            for prog in self.programs.values():
                prog_shd = prog.vs if shd.getTag()=='vs' else prog.fs
                if shd.name == prog_shd:
                    break
            else:
                util.setErrorLocation(shd.lines[0].path, shd.lines[0].lineNumber)
                util.fmtError("vertex shader '{}' is not part of a program".format(shd.name), False)
                fatalError = True
        for slang in slangs:
            for vs in self.vertexShaders.values():
                refl = vs.slReflection[slang]
                util.setErrorLocation(vs.lines[0].path, vs.lines[0].lineNumber)
                vs_inputs = refl['inputs']
                for vs_input in vs_inputs:
                    # if vs_input['name'] not in validVsInNames:
                    #     util.fmtError("invalid vertex shader input name '{}', must be ({})".format(vs_input['name'], ','.join(validVsInNames)))
                    if vs_input['type'] not in validInOutTypes:
                        util.fmtError("invalid vertex shader input type '{}', must be ({})".format(vs_input['type'], ','.join(validInOutTypes)))
                for ub in refl['uniform_blocks']:
                    for m in ub['members']:
                        validTypes = validUniformTypes if m['num']==1 else validUniformArrayTypes
                        if m['type'] not in validTypes:
                            util.fmtError("invalid uniform block member type '{}', must be ({})".format(m['type'], ','.join(validTypes)))
            for fs in self.fragmentShaders.values():
                refl = fs.slReflection[slang] 
                util.setErrorLocation(fs.lines[0].path, fs.lines[0].lineNumber)
                for ub in refl['uniform_blocks']:
                    for m in ub['members']:
                        validTypes = validUniformTypes if m['num']==1 else validUniformArrayTypes
                        if m['type'] not in validTypes:
                            util.fmtError("invalid uniform block member type '{}', must be ({})".format(m['type'], ','.join(validTypes)))
            for prog in self.programs.values():
                vs = self.vertexShaders[prog.vs]
                fs = self.fragmentShaders[prog.fs]
                vs_outputs = vs.slReflection[slang]['outputs']
                fs_inputs = fs.slReflection[slang]['inputs']
                vs_fs_error = False
                if len(vs_outputs) == len(fs_inputs):
                    for vs_out in vs_outputs:
                        in_out_match = False
                        for fs_in in fs_inputs:
                            if (vs_out['name'] == fs_in['name']) and (vs_out['type'] == fs_in['type']):
                                in_out_match = True
                                break
                        if not in_out_match:
                            vs_fs_error = True
                if vs_fs_error:
                    # number of inputs/outputs don't match
                    vs_fs_error = True
                    util.setErrorLocation(vs.lines[0].path, vs.lines[0].lineNumber)
                    util.fmtError("outputs of vs '{}' don't match inputs of fs '{}' (unused items might have been removed)".format(vs.name, fs.name))

    def generateShaderSources(self):
        for shd in self.shaders:
            lines = []
            for l in shd.lines:
                # @include statement?
                if l.include:
                    if l.include not in self.blocks:
                        util.setErrorLocation(incl.path, incl.lineNumber)
                        util.fmtError("included block '{}' doesn't exist".format(incl.name))
                    for lb in self.blocks[l.include].lines:
                        lines.append(lb)
                else:
                    lines.append(l)
            shd.generatedSource = lines

    def loadReflection(self, shd, base_path, slangs):
        for sl in slangs:
            refl_path = '{}.{}.json'.format(base_path, sl)
            with open(refl_path, 'r') as f:
                shd.slReflection[sl] = json.load(f)

    def compileShader(self, input, shd, base_path, slangs, args):
        shd_type = shd.getTag()
        shd_base_path = base_path + '_' + shd.name
        glslcompiler.compile(shd.generatedSource, shd_type, shd_base_path, slangs[0], args)
        shdc.compile(input, shd_base_path, slangs)
        self.loadReflection(shd, shd_base_path, slangs)
        if 'metal' in slangs:
            c_name = '{}_{}_metallib'.format(shd.name, shd_type)
            metalcompiler.compile(shd.generatedSource, shd_base_path, c_name, args)
        if 'hlsl' in slangs:
            c_name = '{}_{}_hlsl5'.format(shd.name, shd_type)
            hlslcompiler.compile(shd.generatedSource, shd_base_path, shd_type, c_name, args)

    def compile(self, input, out_hdr, slangs, args) :
        log.info('## shader code gen: {}'.format(input)) 
        base_path = os.path.splitext(out_hdr)[0]
        for shd in self.shaders:
            self.compileShader(input, shd, base_path, slangs, args)

#-------------------------------------------------------------------------------
def writeHeaderTop(f, shdLib) :
    f.write('#pragma once\n')
    f.write('//-----------------------------------------------------------------------------\n')
    f.write('/*  #version:{}#\n'.format(Version))
    f.write('    machine generated, do not edit!\n')
    f.write('*/\n')
    f.write('#include <stdint.h>\n')
    f.write('#include "sokol_gfx.h"\n')
    f.write('#ifdef __cpp\n')
    f.write('external "C" {\n')
    f.write('#endif\n')

#-------------------------------------------------------------------------------
def writeHeaderBottom(f, shdLib) :
    f.write('#ifdef __cpp\n')
    f.write('}\n')
    f.write('#endif\n')
    f.write('\n')

#-------------------------------------------------------------------------------
def getUniformBlockTypeHash(ub_refl):
    hashString = ''
    for member in ub_refl['members']:
        hashString += member['type']
        hashString += str(member['num'])
    return zlib.crc32(hashString.encode('ascii')) & 0xFFFFFFFF

#-------------------------------------------------------------------------------
def roundup(val, round_to):
    return (val + (round_to - 1)) & ~(round_to - 1)

#-------------------------------------------------------------------------------
def writeProgramHeader(f, shdLib, prog, slang) :
    f.write(DEFAULT_UNIFORM_TYPES_DEFINE)
    for stage in ['VS', 'FS']:
        shd = shdLib.vertexShaders[prog.vs] if stage == 'VS' else shdLib.fragmentShaders[prog.fs]
        refl = shd.slReflection[slang]
        for ub in refl['uniform_blocks']:
            structName = 'shd_shader_{}_uniform_{}'.format(prog.name.lower(), ub['type'])
            cur_offset = 0
            #f.write('#pragma pack(push,1)\n')
            f.write('typedef struct {\n')
            for m in ub['members']:
                next_offset = m['offset']
                numElements = m['num']
                if next_offset > cur_offset:
                    f.write('   uint8_t _pad_{}[{}];\n'.format(cur_offset, next_offset-cur_offset))
                    cur_offset = next_offset
                if numElements == 1:
                    f.write('   {} {};\n'.format(uniformCType[m['type']], m['name']))
                else:
                    f.write('   {} {}[{}];\n'.format(uniformCType[m['type']], m['name'], numElements))
                cur_offset += uniformCSize[m['type']] * m['num']
            # on GL, add padding bytes until struct size is multiple of vec4 size
            if 'glsl' in slang:
                round16 = roundup(cur_offset, 16)
                if cur_offset != round16:
                    f.write('   uint8_t _pad_{}[{}];\n'.format(cur_offset, round16-cur_offset))
            f.write('{} {};\n'.format('}', structName))
            #f.write('#pragma pack(pop)\n')
            f.write('SHD_API const int {}_slot = {};\n'.format(structName, ub['slot']));
            f.write('SHD_API void shd_apply_myshader_{}_uniform_params({} *uniform) {}\n'.format(stage.lower(), structName, '{'))
            f.write('   sg_apply_uniform_block(SG_SHADERSTAGE_{}, {}_slot, uniform, sizeof({}));\n'.format(stage, structName, structName))
            f.write('}\n')
            f.write('\n')
    f.write('SHD_API const sg_shader_desc shd_shader_{} = {}\n'.format(prog.name.lower(), '{'))
    for stage in ['VS', 'FS']:
        shd = shdLib.vertexShaders[prog.vs] if stage == 'VS' else shdLib.fragmentShaders[prog.fs]
        refl = shd.slReflection[slang]
        slangType = oryolSlangTypes[slang]
        shaderName = prog.vs if stage == 'VS' else prog.fs
        sourceConstant = 'shd_shader_{}_{}_source'.format(stage.lower(), shaderName)
        if isGLSL(slang):
            f.write('   .{}.source = {},\n'.format(stage.lower(), sourceConstant))
        elif isHLSL(slang):
            shd_c_name = '{}_{}_hlsl5'.format(vs.name, stage.lower())
            f.write('   .{}.byte_code = {},\n'.format(stage.lower(), shd_c_name))
            f.write('   .{}.byte_code_size = sizeof({}),\n'.format(stage.lower(), shd_c_name))
        elif isMetal(slang):
            shd_c_name = '{}_{}_metallib'.format(shaderName, stage.lower())
            f.write('   .{}.entry = "{}",\n'.format(stage.lower(), "main0"))
            f.write('   .{}.byte_code = {},\n'.format(stage.lower(), shd_c_name))
            f.write('   .{}.byte_code_size = sizeof({}),\n'.format(stage.lower(), shd_c_name))
        for ub in refl['uniform_blocks']:
            structName = 'shd_shader_{}_uniform_{}'.format(prog.name.lower(), ub['type'])
            f.write('   .{}.uniform_blocks[{}] = {}\n'.format(stage.lower(), ub['slot'], '{'))
            f.write('       .size = sizeof({}),\n'.format(structName))
            
            f.write('       .uniforms = {\n')
            for m in ub['members']:
                f.write('           [{}] = {} .name = "{}", .type = {} {},\n'.format(m['offset'], '{', m['name'], uniformSokolTypes[m['type']], '}'))
            f.write('       },\n')
            f.write('   },\n')
        for tex in refl['textures']:
            f.write('   .fs.images[{}] = {} .name = "{}", .type = {} {},\n'.format(tex['slot'], '{', tex['name'], texSokolType[tex['type']], '}'))
    f.write('};\n')

#-------------------------------------------------------------------------------
def generateHeader(absHeaderPath, shdLib, slangs) :
    f = open(absHeaderPath, 'w')
    writeHeaderTop(f, shdLib)
    #writeSourceTop(f, absSourcePath, shdLib, slangs[0])
    for slang in slangs :
        for vs in shdLib.vertexShaders.values() :
            writeShaderSource(f, absHeaderPath, shdLib, vs, slang)
        for fs in shdLib.fragmentShaders.values() :
            writeShaderSource(f, absHeaderPath, shdLib, fs, slang)
    #for prog in shdLib.programs.values() :
    #    writeProgramSource(f, shdLib, prog, slangs)
    #writeSourceBottom(f, shdLib)
    for prog in shdLib.programs.values() :
        print slangs[0]
        writeProgramHeader(f, shdLib, prog, slangs[0])
    writeHeaderBottom(f, shdLib)
    f.close()

#-------------------------------------------------------------------------------
def writeSourceTop(f, absSourcePath, shdLib, slang) :
    path, hdrFileAndExt = os.path.split(absSourcePath)
    hdrFile, ext = os.path.splitext(hdrFileAndExt)
    f.write('/* -----------------------------------------------------------------------------\n')
    f.write(' * #version:{}# machine generated, do not edit!\n'.format(Version))
    f.write(' * -----------------------------------------------------------------------------*/\n')
    f.write('#include "' + hdrFile + '.h"\n')
    f.write('\n')
    if slang == 'hlsl':
        f.write('typedef unsigned char shd_byte;\n')

#-------------------------------------------------------------------------------
def writeSourceBottom(f, shdLib) :
    f.write('\n')

#-------------------------------------------------------------------------------
def writeShaderSource(f, absPath, shdLib, shd, slVersion) :
    base_path = os.path.splitext(absPath)[0] + '_' + shd.name
    if isGLSL(slVersion):
        # GLSL source code is directly inlined for runtime-compilation
        f.write('static const char* {}_{}_src = \n'.format(shd.name, slVersion))
        glsl_src_path = '{}.{}'.format(base_path, slVersion)
        with open(glsl_src_path, 'r') as rf:
            lines = rf.read().splitlines()
            for line in lines:
                f.write('"{}\\n"\n'.format(line))
        f.write(';\n')
    elif isHLSL(slVersion):
        # for HLSL, the actual shader code has been compiled into a header by FXC
        # also write the generated shader source into a C comment as
        # human-readable version
        f.write('/*\n')
        hlsl_src_path = base_path + '.hlsl'
        hlsl_bin_path = base_path + '.hlsl.h'
        with open(hlsl_src_path, 'r') as rf:
            lines = rf.read().splitlines()
            for line in lines:
                line = line.replace('/*', '__').replace('*/', '__')
                f.write('"{}\\n"\n'.format(line))
        f.write('*/\n')
        f.write('#include "{}"\n'.format(hlsl_bin_path))
    elif isMetal(slVersion):
        # for Metal, the shader has been compiled into a binary shader
        # library file, which needs to be embedded into the C header
        f.write('/*\n')
        metal_src_path = base_path + '.metal'
        metal_bin_path = base_path + '.metallib.h'
        with open(metal_src_path, 'r') as rf:
            lines = rf.read().splitlines()
            for line in lines:
                line = line.replace('/*', '__').replace('*/', '__')
                f.write('"{}\\n"\n'.format(line))
        f.write('*/\n')
        f.write('#include "{}"\n'.format(metal_bin_path))
    else :
        util.fmtError("Invalid shader language id")

#-------------------------------------------------------------------------------
def writeInputVertexLayout(f, vs, slang) :
    # writes a C++ VertexLayout definition into the generated source
    # code, this is used to match mesh vertex layouts with 
    # vertex shader input signatures (e.g. required in D3D11),
    # return the C++ name of the vertex layout
    layoutName = '{}_input'.format(vs.name)
    f.write('    Oryol::VertexLayout {};\n'.format(layoutName))
    for inp in vs.slReflection[slang]['inputs'] :
        f.write('    {}.Add({}, {});\n'.format(layoutName, attrOryolName[inp['name']], attrOryolType[inp['type']]))
    return layoutName

#-------------------------------------------------------------------------------
def writeProgramSource(f, shdLib, prog, slangs) :
    # write the Setup() function
    f.write('Oryol::ShaderSetup ' + prog.name + '::Setup() {\n')
    f.write('    Oryol::ShaderSetup setup("' + prog.name + '");\n')
    vs = shdLib.vertexShaders[prog.vs]
    fs = shdLib.fragmentShaders[prog.fs]
    vsInputLayout = writeInputVertexLayout(f, vs, slangs[0])
    f.write('    setup.SetInputLayout({});\n'.format(vsInputLayout))
    vsName = vs.name
    fsName = fs.name
    for slang in slangs:
        slangType = oryolSlangTypes[slang]
        vsSource = '{}_{}_src'.format(vsName, slang)
        fsSource = '{}_{}_src'.format(fsName, slang)
        if isGLSL(slang):
            f.write('    setup.SetProgramFromSources({}, {}, {});\n'.format(
                slangType, vsSource, fsSource));
        elif isHLSL(slang):
            vs_c_name = '{}_vs_hlsl5'.format(vs.name)
            fs_c_name = '{}_fs_hlsl5'.format(fs.name)
            f.write('    setup.SetProgramFromByteCode({}, {}, sizeof({}), {}, sizeof({}));\n'.format(
                slangType, vs_c_name, vs_c_name, fs_c_name, fs_c_name))
        elif isMetal(slang):
            vs_c_name = '{}_vs_metallib'.format(vs.name)
            fs_c_name = '{}_fs_metallib'.format(fs.name)
            f.write('    setup.SetProgramFromByteCode({}, {}, sizeof({}), {}, sizeof({}), "main0", "main0");\n'.format(
                slangType, vs_c_name, vs_c_name, fs_c_name, fs_c_name))

    # add uniform layouts to setup object
    for stage in ['VS', 'FS']:
        shd = shdLib.vertexShaders[prog.vs] if stage == 'VS' else shdLib.fragmentShaders[prog.fs]
        refl = shd.slReflection[slang]
        # add uniform block layouts
        for ub in refl['uniform_blocks']:
            ub_size = ub['size']
            if 'glsl' in slang:
                ub_size = roundup(ub_size, 16)
            f.write('    setup.AddUniformBlock("{}", "{}", {}, {}, {}::_bindShaderStage, {}::_bindSlotIndex);\n'.format(
                ub['type'], ub['name'], getUniformBlockTypeHash(ub), ub_size, ub['type'], ub['type']))
        # add textures layouts to setup objects
        for tex in refl['textures']:
            f.write('    setup.AddTexture("{}", {}, Oryol::ShaderStage::{}, {});\n'.format(tex['name'], texOryolType[tex['type']], stage, tex['slot']))
    f.write('    return setup;\n')
    f.write('}\n')

#-------------------------------------------------------------------------------
def generateSource(absSourcePath, shdLib, slangs) :
    f = open(absSourcePath, 'w') 
    writeSourceTop(f, absSourcePath, shdLib, slangs[0])
    for slang in slangs :
        for vs in shdLib.vertexShaders.values() :
            writeShaderSource(f, absSourcePath, shdLib, vs, slang)
        for fs in shdLib.fragmentShaders.values() :
            writeShaderSource(f, absSourcePath, shdLib, fs, slang)
    for prog in shdLib.programs.values() :
        writeProgramSource(f, shdLib, prog, slangs)
    writeSourceBottom(f, shdLib)  
    f.close()

#-------------------------------------------------------------------------------
def generate(input, out_src, out_hdr, args) :
    # if util.isDirty(Version, [input], [out_src, out_hdr]) :
    print 'slang:'
    print args['slang']
    slangs = slVersions[args['slang']]
    shaderLibrary = ShaderLibrary([input])
    shaderLibrary.parseSources()
    shaderLibrary.generateShaderSources()
    shaderLibrary.compile(input, out_hdr, slangs, args)
    shaderLibrary.validate(slangs)
    # generateSource(out_src, shaderLibrary, slangs)
    generateHeader(out_hdr, shaderLibrary, slangs)