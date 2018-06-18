'''
Code generator for shader libraries.
'''

Version = 1

import os, platform, json
import genutil as util
from util import glslcompiler, shdc
from mod import log
import zlib # only for crc32

DEFAULT_HEADER = '''
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
#endif
#define SHD_MAT4 shd_mat4
enum SHD_INPUT_TYPE {
    SHD_SAMPLER_TYPE_INVALID = 0,
    SHD_INPUT_TYPE_FLOAT,
    SHD_INPUT_TYPE_VEC2,
    SHD_INPUT_TYPE_VEC3,
    SHD_INPUT_TYPE_VEC4,
};

enum SHD_SAMPLER_TYPE {
    SHD_SAMPLER_TYPE_INVALID = 0,
    SHD_SAMPLER_TYPE_2D,
    SHD_SAMPLER_TYPE_ARRAY,
    SHD_SAMPLER_TYPE_CUBE,
    SHD_SAMPLER_TYPE_3D,
};
enum SHD_UNIFORM_TYPE {
    SHD_UNIFORM_TYPE_INVALID = 0,
    SHD_UNIFORM_TYPE_FLOAT,
    SHD_UNIFORM_TYPE_VEC2,
    SHD_UNIFORM_TYPE_VEC3,
    SHD_UNIFORM_TYPE_VEC4,
    SHD_UNIFORM_TYPE_MAT2,
    SHD_UNIFORM_TYPE_MAT3,
    SHD_UNIFORM_TYPE_MAT4,
};
enum SHD_SHADER_TYPE {
    SHD_Shader_TYPE_INVALID = 0,
    SHD_SHADER_TYPE_VERTEX,
    SHD_SHADER_TYPE_FRAGMENT,
    SHD_SHADER_TYPE_COMPUTE,
};
enum SHD_SHADER_TARGET_TYPE {
    SHD_SHADER_TARGET_TYPE_DEFAULT,
    SHD_SHADER_TARGET_TYPE_GLSL100,
    SHD_SHADER_TARGET_TYPE_GLSLES3,
    SHD_SHADER_TARGET_TYPE_GLSL330,
    SHD_SHADER_TARGET_TYPE_METAL,
    SHD_SHADER_TARGET_TYPE_HLSL5,
};

typedef struct {
    enum SHD_SAMPLER_TYPE type;
    int slot;
    char *name;
} shd_texture;


typedef struct {
    enum SHD_INPUT_TYPE type;
    int slot;
    char *name;
} shd_input;

typedef struct {
    char *name;
    enum SHD_UNIFORM_TYPE type;
    int offset;
    int size;
    int count;
} shd_uniform;

typedef struct {
    char *name;
    int byteSize;
    int slot;
    int count;
    shd_uniform *uniforms;
} shd_uniform_block;

typedef struct {
    enum SHD_SHADER_TARGET_TYPE targetType;
    enum SHD_SHADER_TYPE type;
    char *name;
    char *entry;
    int size;
    unsigned char *binary;
    char *source;
    int inputCount;
    shd_input *inputs;
    int uniformBlockCount;
    shd_uniform_block *uniformBlocks;
    int textureCount;
    shd_texture *textures;
} shd_shader;


typedef struct {
    union {
        struct {
            shd_shader compute;
            shd_shader _empty;
        };
        shd_shader vs;
        shd_shader fs;
    };
    enum SHD_PROGRAMS id;
    char *name;
} shd_program;

typedef struct {
    int count;
    shd_program *programs;
} shd_program_collection;

SHD_API const shd_program_collection shd_get_programs(enum SHD_SHADER_TARGET_TYPE);
SHD_API const enum SHD_SHADER_TARGET_TYPE *shd_get_slangs(int *count);
SHD_API enum SHD_SHADER_TARGET_TYPE shd_get_default_slang();
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

shdShaderTypes = {
    'vs' : 'SHD_SHADER_TYPE_VERTEX',
    'fs' : 'SHD_SHADER_TYPE_FRAGMENT',
    'compute' : 'SHD_SHADER_TYPE_COMPUTE',
}

shdSlangTypes = {
    'glsl100': 'SHD_SHADER_TARGET_TYPE_GLSL100',
    'glsl330': 'SHD_SHADER_TARGET_TYPE_GLSL330',
    'glsles3': 'SHD_SHADER_TARGET_TYPE_GLSLES3',
    'hlsl':    'SHD_SHADER_TARGET_TYPE_HLSL5',
    'metal':   'SHD_SHADER_TARGET_TYPE_METAL'
}
def isGLSL(sl):
    return sl in ['glsl100', 'glsl330', 'glsles3']

def isHLSL(sl):
    return sl == 'hlsl'

def isMetal(sl):
    return sl == 'metal'

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

uniformEnumType = {
    'float': 'SHD_UNIFORM_TYPE_FLOAT',
    'vec2':  'SHD_UNIFORM_TYPE_VEC2',
    'vec3':  'SHD_UNIFORM_TYPE_VEC3',
    'vec4':  'SHD_UNIFORM_TYPE_VEC4',
    'mat2':  'SHD_UNIFORM_TYPE_MAT2',
    'mat3':  'SHD_UNIFORM_TYPE_MAT3',
    'mat4':  'SHD_UNIFORM_TYPE_MAT4',
}

inputShdTypes = {
    'float': 'SHD_INPUT_TYPE_FLOAT',
    'vec2': 'SHD_INPUT_TYPE_VEC2',
    'vec3': 'SHD_INPUT_TYPE_VEC3',
    'vec4': 'SHD_INPUT_TYPE_VEC4',
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

texShdType = {
    'sampler2D':      'SHD_SAMPLER_TYPE_2D',
    'samplerCube':    'SHD_SAMPLER_TYPE_CUBE',
    'sampler3D':      'SHD_SAMPLER_TYPE_3D',
    'sampler2DArray': 'SHD_SAMPLER_TYPE_ARRAY',
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
    f.write('#ifdef __cpp\n')
    f.write('external "C" {\n')
    f.write('#endif\n')
    f.write(DEFAULT_HEADER)

#-------------------------------------------------------------------------------
def writeHeaderBottom(f, shdLib) :
    f.write('\n')
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


def generateShaderHader(shd, slang) :
    refl = shd.slReflection[slang]
    # add uniform block layouts
    for ub in refl['uniform_blocks']:
        ub_size = ub['size']
        f.write('')
        if 'glsl' in slang:
            ub_size = roundup(ub_size, 16)
        f.write('    setup.AddUniformBlock("{}", "{}", {}, {}, {}::_bindShaderStage, {}::_bindSlotIndex);\n'.format(
            ub['type'], ub['name'], getUniformBlockTypeHash(ub), ub_size, ub['type'], ub['type']))
    # add textures layouts to setup objects
    for tex in refl['textures']:
        f.write('    setup.AddTexture("{}", {}, Oryol::ShaderStage::{}, {});\n'.format(tex['name'], texOryolType[tex['type']], stage, tex['slot']))
#-------------------------------------------------------------------------------
def writeShaderUniformStructs(f, shd) :
    for slangName in shd.slReflection :
        slang = shd.slReflection[slangName]
        for uniformBlock in slang['uniform_blocks'] :
            cur_offset = 0
            next_offset = 0
            f.write('typedef struct {\n')
            for member in uniformBlock['members'] : 
                next_offset = member['offset']
                numElements = member['num']
                if next_offset > cur_offset:
                    f.write('   uint8_t _pad_{}[{}];\n'.format(cur_offset, next_offset - cur_offset))
                    cur_offset = next_offset
                if numElements == 1:
                    f.write('   {} {};\n'.format(uniformCType[member['type']], member['name']))
                else:
                    f.write('   {} {}[{}];\n'.format(uniformCType[member['type']], member['name'], numElements))
                cur_offset += uniformCSize[member['type']] * member['num']
            f.write('{} shd_{}_{}_params_{}_{};\n'.format('}', shd.getTag(), slangName, shd.name, uniformBlock['type']))
#-------------------------------------------------------------------------------
def writeVertexShaderInputStructs(f, shd) :
    for slangName in shd.slReflection :
        slang = shd.slReflection[slangName]
        inputs = slang['inputs']
        inputsLeng = len(inputs)
        if inputsLeng > 0:
            f.write('typedef struct {\n')
            for input in inputs:
                f.write('   {} {};\n'.format(uniformCType[input['type']], input['name']))
            f.write('{} shd_inputs_{};\n'.format('}', shd.name))
        return # Note(pjako): shader inputs should look the same for all shading language, if not we need to generate it per api
#-------------------------------------------------------------------------------
def generateHeader(absHeaderPath, shdLib, slangs) :
    f = open(absHeaderPath, 'w')
    writeHeaderTop(f, shdLib)
    f.write('enum SHD_PROGRAMS {\n')
    f.write('   SHD_PROGRAM_INVALID = 0,\n')
    for programName in shdLib.programs :
        f.write('   SHD_PROGRAM_{},\n'.format(programName.upper()))
    f.write('}\n')
    for shdName in shdLib.vertexShaders :
        writeVertexShaderInputStructs(f, shdLib.vertexShaders[shdName])
        writeShaderUniformStructs(f, shdLib.vertexShaders[shdName])
    for shdName in shdLib.fragmentShaders :
        writeShaderUniformStructs(f, shdLib.fragmentShaders[shdName])

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
def writeProgramDefinition(shd) :
    f.write('typedef struct {')
    refl = shd.slReflection[slang]
    
    for ub in refl['uniform_blocks']:
        for m in ub['members']:
            next_offset = m['offset']
            numElements = m['num']
            if next_offset > cur_offset:
                f.write('   uint8_t _pad_{}[{}];\n'.format(cur_offset, next_offset - cur_offset))
                cur_offset = next_offset
            if numElements == 1:
                f.write('   {} {};\n'.format(uniformCType[m['type']], m['name']))
            else:
                f.write('   {} {}[{}];\n'.format(uniformCType[m['type']], m['name'], numElements))
            cur_offset += uniformCSize[m['type']] * m['num']
    f.write('   ')
    f.write('} shd_vs_params_{};\n'.format(shd.name))
    f.write('SHD_API shd_program shd_get_program_{}();\n'.format(shd.name))
#-------------------------------------------------------------------------------

def writeShaderDetails(f, refl) :
    blockIndex = 0
    textures = refl['textures']
    numTextures = len(textures)
    if numTextures > 0:
        f.write('           static shd_input textures[{}];\n'.format(numTextures))
        idx = 0
        for texture in textures:
            slot = 0
            if texture.get('slot'):
                slot = texture['slot']
            f.write('           textures[{}].name = "{}";\n'.format(idx, texture['name']))
            f.write('           textures[{}].slot = {};\n'.format(idx, slot))
            f.write('           textures[{}].type = {};\n'.format(idx, textureShdTypes[texture['type']]))
            idx += 1
        f.write('           shader.textureCount = {};\n'.format(numTextures))
        f.write('           shader.textures = &textures[0];\n')
    inputs = refl['inputs']
    inputsLeng = len(inputs)
    if inputsLeng > 0:
        f.write('           static shd_input inputs[{}];\n'.format(inputsLeng))
        idx = 0
        for input in inputs:
            slot = 0
            if input.get('slot'):
                slot = input['slot']
            f.write('           inputs[{}].name = "{}";\n'.format(idx, input['name']))
            f.write('           inputs[{}].slot = {};\n'.format(idx, slot))
            f.write('           inputs[{}].type = {};\n'.format(idx, inputShdTypes[input['type']]))
            idx += 1
        f.write('           shader.inputCount = {};\n'.format(inputsLeng))
        f.write('           shader.inputs = &inputs[0];\n')

    blocks = refl['uniform_blocks']
    if len(blocks) == 0:
        return
    f.write('           static shd_uniform_block blocks[{}];\n'.format(len(blocks)))
    for ub in blocks:
        members = ub['members']
        f.write('           blocks[{}].name = "{}";\n'.format(blockIndex, ub['type']))
        f.write('           blocks[{}].slot = {};\n'.format(blockIndex, ub['slot']))
        f.write('           blocks[{}].count = {};\n'.format(blockIndex, len(members)))
        f.write('           {\n')
        f.write('               static shd_uniform uniforms[{}];\n'.format(len(members)))
        f.write('               blocks[{}].uniforms = &uniforms[0];\n'.format(blockIndex))
        idx = 0
        cur_offset = 0
        for m in members:
            next_offset = m['offset']
            numElements = m['num']#uniformCSize
            f.write('               uniforms[{}].name = "{}";\n'.format(idx, m['name']))
            f.write('               uniforms[{}].type = {};\n'.format(idx, uniformEnumType[m['type']]))
            f.write('               uniforms[{}].size = {};\n'.format(idx, uniformCSize[m['type']]))
            f.write('               uniforms[{}].offset = {};\n'.format(idx, next_offset))
            f.write('               uniforms[{}].count = {};\n'.format(idx, numElements))
            cur_offset = next_offset
            cur_offset += uniformCSize[m['type']] * m['num']
            idx += 1
        blockIndex += 1
        f.write('           }\n')
    f.write('           shader.uniformBlockCount = {};\n'.format(len(blocks)))
    f.write('           shader.uniformBlocks = &blocks[0];\n')
#-------------------------------------------------------------------------------


def writeShaderSource(f, absPath, shd, slangs) :
    base_path = os.path.splitext(absPath)[0] + '_' + shd.name
    metal_src_path = base_path + '.metal'
    metal_bin_path = base_path + '.metallib.h'
    for slVersion in shd.slReflection:
        if isMetal(slVersion):
            f.write('#include "{}"\n'.format(metal_bin_path))
            metal_bin_path = base_path + '.metallib.h'
        if isHLSL(slVersion):
            hlsl_src_path = base_path + '.hlsl'
            f.write('#include "{}"\n'.format(hlsl_bin_path))

    #todo: put includes to the start!

    f.write('const shd_shader shd_{}_{}(enum SHD_SHADER_TARGET_TYPE type) {}\n'.format(shd.getTag(), shd.name, '{'))
    f.write('   shd_shader shader;\n')
    f.write('   shader.type = {};\n'.format(shdShaderTypes[shd.getTag()]))
    f.write('   shader.name = "{}";\n'.format(shd.name))
    idx = 0
    f.write('   switch(type) {\n')
    for slVersion in shd.slReflection:
        slang = shd.slReflection[slVersion]
        f.write('       case {}: {}\n'.format(shdSlangTypes[slVersion.lower()], '{'))
        if isGLSL(slVersion):
            # GLSL source code is directly inlined for runtime-compilation
            f.write('       shader.source = \n'.format(idx))
            glsl_src_path = '{}.{}'.format(base_path, slVersion)
            with open(glsl_src_path, 'r') as rf:
                lines = rf.read().splitlines()
                for line in lines:
                    f.write('               "{}\\n"\n'.format(line))
            f.write('           ;\n')
        elif isHLSL(slVersion):
            # for HLSL, the actual shader code has been compiled into a header by FXC
            # also write the generated shader source into a C comment as
            # human-readable version
            hlsl5CName = '{}_{}_hlsl5'.format(shd.name, shd.getTag())
            f.write('           shader.binary = (unsigned char *) {};\n'.format(hlsl5CName))
            f.write('           shader.size =  sizeof({});\n'.format(hlsl5CName))
        elif isMetal(slVersion):
            # for Metal, the shader has been compiled into a binary shader
            # library file, which needs to be embedded into the C header
            mtlCName = '{}_{}_metallib'.format(shd.name, shd.getTag())
            # this is the default entry created by cross SPIRV
            f.write('           shader.entry = "main0";\n')
            f.write('           shader.binary = (unsigned char *) {};\n'.format(mtlCName))
            f.write('           shader.size =  sizeof({});\n'.format(mtlCName))
        writeShaderDetails(f, slang)
        f.write('           break;\n')
        f.write('       }\n')
        idx += 1
    f.write('   }\n')
    # f.write('   shader.slangs = &slangs[0];\n')
    f.write('   return shader;\n')
    f.write('}\n')
#-------------------------------------------------------------------------------
def writeProgramSource(f, program) :
    f.write('const shd_program shd_get_program_{}(enum SHD_SHADER_TARGET_TYPE type) {}\n'.format(program.name, '{'))
    f.write('   shd_program program;\n')
    f.write('   program.name = "{}";\n'.format(program.name))
    f.write('   program.id = SHD_PROGRAM_{},\n'.format(program.name.upper()))
    f.write('   program.vs = (shd_shader) shd_vs_{}(type);\n'.format(program.vs))
    f.write('   program.fs = (shd_shader) shd_fs_{}(type);\n'.format(program.fs))
    f.write('   return program;\n')
    f.write('}\n')
def writeProgramCollectionSource(f, programs) :
    f.write('const shd_program_collection shd_get_programs(enum SHD_SHADER_TARGET_TYPE type) {\n')
    numPrograms = len(programs)
    f.write('   static shd_program programs[{}];\n'.format(numPrograms))
    idx = 0
    for programName in programs:
        f.write('   programs[{}] = (shd_program) shd_get_program_{}(type);\n'.format(idx, programName))
        idx += 1
    f.write('   return {\n')
    f.write('       {}, &programs[0]\n'.format(numPrograms))
    f.write('   };\n')
    f.write('}\n')
#-------------------------------------------------------------------------------
def generateSource(absSourcePath, shdLib, slangs) :
    f = open(absSourcePath, 'w') 
    writeSourceTop(f, absSourcePath, shdLib, slangs[0])

    for shader in shdLib.shaders:
        writeShaderSource(f, absSourcePath, shader, slangs)

    for programName in shdLib.programs:
        writeProgramSource(f, shdLib.programs[programName])

    writeProgramCollectionSource(f, shdLib.programs)
    f.write('SHD_API enum SHD_SHADER_TARGET_TYPE shd_get_default_slang() {\n')
    f.write('   return {};\n'.format(shdSlangTypes[slangs[0]]))
    f.write('}\n')

    f.write('const enum SHD_SHADER_TARGET_TYPE *shd_get_slangs(int *count) {\n')
    f.write('   static const enum SHD_SHADER_TARGET_TYPE slangs[{}] = {}\n'.format(len(slangs), '{'))
    for slang in slangs:
        f.write('       {},\n'.format(shdSlangTypes[slangs[0]]))
    f.write('   };\n')
    f.write('   *count = {};\n'.format(len(slangs)))
    f.write('   return &slangs[0];\n')
    f.write('}\n')
        

    writeSourceBottom(f, shdLib)
    f.close()

#-------------------------------------------------------------------------------
def generate(input, out_src, out_hdr, args) :
    if util.isDirty(Version, [input], [out_src, out_hdr]) :
        slangs = slVersions[args['slang']]
        shaderLibrary = ShaderLibrary([input])
        shaderLibrary.parseSources()
        shaderLibrary.generateShaderSources()
        shaderLibrary.compile(input, out_hdr, slangs, args)
        shaderLibrary.validate(slangs)
        generateSource(out_src, shaderLibrary, slangs)
        generateHeader(out_hdr, shaderLibrary, slangs)