import bpy.props

# Nico: The __init__.py only designed to register and unregister ,so as a simple control for the whole plugin,
# keep it clean and don't add too many code,code should be in other files and import it here.
# we use .utils instead of utils because blender can't locate where utils is
# Blender can only locate panel.py only when you add a . before it.

from .mmt_panel.panel_ui import *
from .mmt_rightclick_menu.mesh_operator import *
from .mmt_animation.animation_operator import *


bl_info = {
    "name": "MMT",
    "description": "MMT-Community's Blender Plugin",
    "blender": (3, 6, 0),
    "version": (1, 0, 5, 8),
    "location": "View3D",
    "warning": "Only support Blender 3.6 LTS",
    "category": "Generic"
}


register_classes = (
    # migoto
    MMTPathProperties,
    MMTPathOperator,
    MMTPanel,

    Import3DMigotoFrameAnalysis,
    Import3DMigotoRaw,
    Import3DMigotoReferenceInputFormat,
    Export3DMigoto,

    # mesh_operator right-click menu
    RemoveUnusedVertexGroupOperator,
    MergeVertexGroupsWithSameNumber,
    FillVertexGroupGaps,
    AddBoneFromVertexGroup,
    RemoveNotNumberVertexGroup,
    ConvertToFragmentOperator,
    MMTDeleteLoose,
    MMTResetRotation,
    MigotoRightClickMenu,
    MMTCancelAutoSmooth,
    MMTShowIndexedVertices,
    MMTSetAutoSmooth89,
    SplitMeshByCommonVertexGroup,

    # MMT one-click import/export
    MMTImportAllTextModel,
    MMTExportAllIBVBModel,

    # MMD type animation Mod support
    MMDModIniGenerator
)


def register():
    for cls in register_classes:
        # make_annotations(cls)
        bpy.utils.register_class(cls)

    # Create a new property specifically for storing MMT paths
    bpy.types.Scene.mmt_props = bpy.props.PointerProperty(type=MMTPathProperties)
    # mesh_operator
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_migoto_right_click)

    # Save the selected MMT path before Blender exits
    bpy.app.handlers.depsgraph_update_post.append(save_mmt_path)

    # Variables for saving MMT values
    bpy.types.Scene.mmt_mmd_animation_mod_start_frame = bpy.props.IntProperty(name="Start Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_end_frame = bpy.props.IntProperty(name="End Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_play_speed = bpy.props.FloatProperty(name="Play Speed")

    
def unregister():
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mmt_props

    # mesh_operator
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_migoto_right_click)

    # Delete MMT's MMD variables upon unregistering
    del bpy.types.Scene.mmt_mmd_animation_mod_start_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_end_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_play_speed


