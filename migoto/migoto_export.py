from .migoto_format import *

import json
import os.path
import bpy

from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, StringProperty


# from export_obj:
def mesh_triangulate(me):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()


def blender_vertex_to_3dmigoto_vertex(mesh, obj, blender_loop_vertex, layout, texcoords):

    # Get the corresponding vertex from the total vertices based on the vertex index in the loop vertex
    blender_vertex = mesh.vertices[blender_loop_vertex.vertex_index]
    vertex = {}
    seen_offsets = set()

    # TODO: Warn if vertex is in too many vertex groups for this layout,
    # ignoring groups with weight=0.0
    vertex_groups = sorted(blender_vertex.groups, key=lambda x: x.weight, reverse=True)

    for elem in layout:
        # Only process per-vertex
        if elem.InputSlotClass != 'per-vertex':
            continue

        # Used to skip processing of duplicate elements on the same vertex, will this code really be executed? It seems it will never trigger.
        if (elem.InputSlot, elem.AlignedByteOffset) in seen_offsets:
            continue
        seen_offsets.add((elem.InputSlot, elem.AlignedByteOffset))

        if elem.name == 'POSITION':
            vertex[elem.name] = elem.pad(list(blender_vertex.undeformed_co), 1.0)
        elif elem.name.startswith('COLOR'):
            if elem.name in mesh.vertex_colors:
                vertex[elem.name] = elem.clip(list(mesh.vertex_colors[elem.name].data[blender_loop_vertex.index].color))
            else:
                vertex[elem.name] = list(mesh.vertex_colors[elem.name + '.RGB'].data[blender_loop_vertex.index].color)[
                                    :3] + \
                                    [mesh.vertex_colors[elem.name + '.A'].data[blender_loop_vertex.index].color[0]]
        elif elem.name == 'NORMAL':
            vertex[elem.name] = elem.pad(list(blender_loop_vertex.normal), 0.0)
        elif elem.name.startswith('TANGENT'):
            # DOAXVV has +1/-1 in the 4th component. Not positive what this is,
            # but guessing maybe the bitangent sign? Not even sure it is used...
            # FIXME: Other games
            vertex[elem.name] = elem.pad(list(blender_loop_vertex.tangent), blender_loop_vertex.bitangent_sign)
        elif elem.name.startswith('BLENDINDICES'):
            i = elem.SemanticIndex * 4
            vertex[elem.name] = elem.pad([x.group for x in vertex_groups[i:i + 4]], 0)
        elif elem.name.startswith('BLENDWEIGHT'):
            # TODO: Warn if vertex is in too many vertex groups for this layout
            i = elem.SemanticIndex * 4
            vertex[elem.name] = elem.pad([x.weight for x in vertex_groups[i:i + 4]], 0.0)
        elif elem.name.startswith('TEXCOORD') and elem.is_float():
            # FIXME: Handle texcoords of other dimensions
            uvs = []
            for uv_name in ('%s.xy' % elem.name, '%s.zw' % elem.name):
                if uv_name in texcoords:
                    uvs += list(texcoords[uv_name][blender_loop_vertex.index])
            vertex[elem.name] = uvs

        # Nico: No need to consider BINORMAL, modern game rendering basically does not use the outdated rendering scheme of BINORMAL
        # elif elem.name.startswith('BINORMAL'):
            # Some DOA6 meshes (skirts) use BINORMAL, but I'm not certain it is
            # actually the binormal. These meshes are weird though, since they
            # use 4 dimensional positions and normals, so they aren't something
            # we can really deal with at all. Therefore, the below is untested,
            # FIXME: So find a mesh where this is actually the binormal,
            # uncomment the below code and test.
            # normal = blender_loop_vertex.normal
            # tangent = blender_loop_vertex.tangent
            # binormal = numpy.cross(normal, tangent)
            # XXX: Does the binormal need to be normalised to a unit vector?
            # binormal = binormal / numpy.linalg.norm(binormal)
            # vertex[elem.name] = elem.pad(list(binormal), 0.0)
            # pass

        else:
            # Unhandled semantics are saved in vertex layers
            data = []
            for component in 'xyzw':
                layer_name = '%s.%s' % (elem.name, component)
                if layer_name in mesh.vertex_layers_int:
                    data.append(mesh.vertex_layers_int[layer_name].data[blender_loop_vertex.vertex_index].value)
                elif layer_name in mesh.vertex_layers_float:
                    data.append(mesh.vertex_layers_float[layer_name].data[blender_loop_vertex.vertex_index].value)
            if data:
                # print('Retrieved unhandled semantic %s %s from vertex layer' % (elem.name, elem.Format), data)
                vertex[elem.name] = data

        if elem.name not in vertex:
            print('NOTICE: Unhandled vertex element: %s' % elem.name)
        # else:
        #    print('%s: %s' % (elem.name, repr(vertex[elem.name])))

    return vertex


def write_fmt_file(f, vb, ib):
    f.write('stride: %i\n' % vb.layout.stride)
    f.write('topology: %s\n' % vb.topology)
    if ib is not None:
        f.write('format: %s\n' % ib.format)
    f.write(vb.layout.to_string())


def export_3dmigoto(operator, context, vb_path, ib_path, fmt_path):

    operator.report({'INFO'}, "Export whether to keep the same number of vertices: " + str(bpy.context.scene.mmt_props.export_same_number))
    # Get the obj object in the current scene
    obj = context.object

    # Do not export if empty
    if obj is None:
        raise Fatal('No object selected')

    stride = obj['3DMigoto:VBStride']
    layout = InputLayout(obj['3DMigoto:VBLayout'], stride=stride)

    # Get Mesh
    if hasattr(context, "evaluated_depsgraph_get"):  # 2.80
        mesh = obj.evaluated_get(context.evaluated_depsgraph_get()).to_mesh()
    else:  # 2.79
        mesh = obj.to_mesh(context.scene, True, 'PREVIEW', calc_tessface=False)

    # Use bmesh to copy a new mesh and triangulate
    mesh_triangulate(mesh)

    try:
        if obj['3DMigoto:IBFormat'] == "DXGI_FORMAT_R16_UINT":
            ib_format = "DXGI_FORMAT_R32_UINT"
        else:
            ib_format = obj['3DMigoto:IBFormat']
    except KeyError:
        ib = None
        raise Fatal('FIXME: Add capability to export without an index buffer')
    else:
        ib = IndexBuffer(ib_format)

    # Calculates tangents and makes loop normals valid (still with our
    # custom normal data from import time):
    # This step will increase the number of vertices if there is a TANGENT attribute
    mesh.calc_tangents()

    # Assemble texcoord layers, assemble as many UVMaps as there are
    texcoord_layers = {}
    for uv_layer in mesh.uv_layers:
        texcoords = {}

        try:
            flip_texcoord_v = obj['3DMigoto:' + uv_layer.name]['flip_v']
            if flip_texcoord_v:
                flip_uv = lambda uv: (uv[0], 1.0 - uv[1])
            else:
                flip_uv = lambda uv: uv
        except KeyError:
            flip_uv = lambda uv: uv

        for l in mesh.loops:
            uv = flip_uv(uv_layer.data[l.index].uv)
            texcoords[l.index] = uv
        texcoord_layers[uv_layer.name] = texcoords

    # Blender's vertices have unique positions, but may have multiple
    # normals, tangents, UV coordinates, etc - these are stored in the
    # loops. To export back to DX we need these combined together such that
    # a vertex is a unique set of all attributes, but we don't want to
    # completely blow this out - we still want to reuse identical vertices
    # via the index buffer. There might be a convenience function in
    # Blender to do this, but it's easy enough to do this ourselves
    indexed_vertices = collections.OrderedDict()

    unique_position_vertices = {}
    '''
    Nico:
        Converting vertices to 3dmigoto type vertices and then hashing them, if there is TANGENT, the number will increase, if not, the number will not increase.
        Nico: The initial Vertex, even after TANGENT calculation, the number is the same as before
        But using blender_lvertex here results in different HashableVertex being generated, because everything else is fixed, only this blender_lvertex will change
        Note that if TANGENT is not calculated or there is no TANGENT attribute, no additional vertices will be generated
    '''
    for poly in mesh.polygons:
        face = []
        for blender_lvertex in mesh.loops[poly.loop_start:poly.loop_start + poly.loop_total]:
            #
            vertex = blender_vertex_to_3dmigoto_vertex(mesh, obj, blender_lvertex, layout, texcoord_layers)

            '''
            Nico:
                First, calculate the current vertex into a hashed vertex, and if the calculated hashed vertex does not exist, insert it into indexed_vertices
                Then add the vertex to face[], the index is the index of the vertex in the dictionary
                Here we add the tangent of the obtained vertex to a dictionary of vertex:tangent values
                If the vertex appears in the dictionary, return the average value of the corresponding list in the dictionary and the current value, otherwise do not update
                This way, the average tangent for each Position can be obtained, and if the tangent values are the same, no additional redundant vertices will be generated.
                Here I choose to simply use the TANGENT of this vertex the first time it appears as its TANGENT to avoid the problem of generating extra redundant vertices, and it can be optimized later to use the average value as TANGENT
            '''
            if bpy.context.scene.mmt_props.export_same_number:
                if "POSITION" in vertex and "NORMAL" in vertex and "TANGENT" in vertex :
                    if tuple(vertex["POSITION"] + vertex["NORMAL"]  ) in unique_position_vertices:
                        tangent_var = unique_position_vertices[tuple(vertex["POSITION"] + vertex["NORMAL"])]
                        vertex["TANGENT"] = tangent_var
                    else:
                        tangent_var = vertex["TANGENT"]
                        unique_position_vertices[tuple(vertex["POSITION"] + vertex["NORMAL"])] = tangent_var
                        vertex["TANGENT"] = tangent_var

            indexed_vertex = indexed_vertices.setdefault(HashableVertex(vertex), len(indexed_vertices))
            face.append(indexed_vertex)
        if ib is not None:
            ib.append(face)

    # operator.report({'INFO'}, "Export Vertex Number: " + str(len(indexed_vertices)))
    vb = VertexBuffer(layout=layout)
    for vertex in indexed_vertices:
        vb.append(vertex)

    vgmaps = {k[15:]: keys_to_ints(v) for k, v in obj.items() if k.startswith('3DMigoto:VGMap:')}
    # operator.report({'INFO'}, "vgmap length " + str(len(vgmaps)))

    if '' not in vgmaps:
        vb.write(open(vb_path, 'wb'), operator=operator)

    base, ext = os.path.splitext(vb_path)
    for (suffix, vgmap) in vgmaps.items():
        path = vb_path
        if suffix:
            path = '%s-%s%s' % (base, suffix, ext)
        vgmap_path = os.path.splitext(path)[0] + '.vgmap'
        operator.report({'INFO'}, "vgmap_path " + vgmap_path)
        print('Exporting %s...' % path)
        vb.remap_blendindices(obj, vgmap)
        vb.write(open(path, 'wb'), operator=operator)
        vb.revert_blendindices_remap()
        sorted_vgmap = collections.OrderedDict(sorted(vgmap.items(), key=lambda x: x[1]))
        json.dump(sorted_vgmap, open(vgmap_path, 'w'), indent=2)

    if ib is not None:
        ib.write(open(ib_path, 'wb'), operator=operator)

    # Write format reference file
    write_fmt_file(open(fmt_path, 'w'), vb, ib)


class Export3DMigoto(bpy.types.Operator, ExportHelper):
    """Export a mesh for re-injection into a game with 3DMigoto"""
    bl_idname = "export_mesh.migoto_mmt"
    bl_label = "Export 3DMigoto Vertex & Index Buffers (MMT)"

    # file extension
    filename_ext = '.vb'

    # file type filter
    filter_glob: StringProperty(
        default='*.vb',
        options={'HIDDEN'},
    ) # type: ignore

    # Default file path
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for exporting",
        subtype='FILE_PATH',
        default="",
    ) # type: ignore

    # where you do export logic
    def execute(self, context):
        try:
            vb_path = self.filepath
            ib_path = os.path.splitext(vb_path)[0] + '.ib'
            fmt_path = os.path.splitext(vb_path)[0] + '.fmt'

            # FIXME: ExportHelper will check for overwriting vb_path, but not ib_path

            export_3dmigoto(self, context, vb_path, ib_path, fmt_path)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}
