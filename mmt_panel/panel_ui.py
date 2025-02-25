import os
import bpy
import json

from .panel_functions import *

from ..migoto.migoto_export import *
from ..migoto.migoto_import import *


# -----------------------------------The following two do not belong to the right-click menu, they belong to the MMT panel, so put them at the bottom---------------------------------------
class MMTImportAllTextModel(bpy.types.Operator):
    bl_idname = "mmt.import_all"
    bl_label = "Import all .ib .vb models from current OutputFolder"

    def execute(self, context):
        # First, get the MMT path
        mmt_path = bpy.context.scene.mmt_props.path
        current_game = ""
        main_setting_path = os.path.join(context.scene.mmt_props.path, "Configs\\Main.json")
        if os.path.exists(main_setting_path):
            main_setting_file = open(main_setting_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            current_game = main_setting_json["GameName"]

        game_config_path = os.path.join(context.scene.mmt_props.path, "Games\\" + current_game + "\\Config.json")
        game_config_file = open(game_config_path)
        game_config_json = json.load(game_config_file)
        game_config_file.close()

        output_folder_path = mmt_path + "Games\\" + current_game + "\\3Dmigoto\\Mods\\output\\"

        # Determine which IB to import based on DrawIB in Config.json
        import_folder_path_list = []
        for ib_config in game_config_json:
            draw_ib = ib_config["DrawIB"]
            import_folder_path_list.append(os.path.join(output_folder_path, draw_ib))

        for import_folder_path in import_folder_path_list:
            # TODO Import all ib and vb files in the current folder
            # 1. We need to add to a new collection for subsequent operations
            folder_draw_ib_name = os.path.basename(import_folder_path)
            collection = bpy.data.collections.new(folder_draw_ib_name)
            bpy.context.scene.collection.children.link(collection)

            # Each import_folder_path is a drawIB
            # Here we need to get the folder name

            # Read all vb and ib file prefixes in the folder
            prefix_set = set()
            # (1) Get all ib file prefix list
            file_pattern = os.path.join(import_folder_path, "*.ib")
            txt_file_list = glob(file_pattern)
            for txt_file_path in txt_file_list:
                # If the file name does not contain "-", it belongs to our automatically exported file name and is not counted
                if os.path.basename(txt_file_path).find("-") == -1:
                    continue

                txt_file_splits = os.path.basename(txt_file_path).split("-")
                ib_file_name = txt_file_splits[0] + "-" + txt_file_splits[1]
                ib_file_name = ib_file_name[0:len(ib_file_name) - 3]
                prefix_set.add(ib_file_name)
            # Iterate and import each ib and vb file
            for prefix in prefix_set:
                vb_bin_path = import_folder_path + "\\" + prefix + '.vb'
                ib_bin_path = import_folder_path + "\\" + prefix + '.ib'
                fmt_path = import_folder_path + "\\" + prefix + '.fmt'
                if not os.path.exists(vb_bin_path):
                    raise Fatal('Unable to find matching .vb file for %s' % import_folder_path + "\\" + prefix)
                if not os.path.exists(ib_bin_path):
                    raise Fatal('Unable to find matching .ib file for %s' % import_folder_path + "\\" + prefix)
                if not os.path.exists(fmt_path):
                    fmt_path = None

                # Some parameters need to be passed, anyway, passing empty ones here can be used
                migoto_raw_import_options = {}

                # Use a done set to record the processed file paths, if processed, it will trigger continue
                done = set()
                try:
                    if os.path.normcase(vb_bin_path) in done:
                        continue
                    done.add(os.path.normcase(vb_bin_path))
                    if fmt_path is not None:
                        obj_results = import_3dmigoto_raw_buffers(self, context, fmt_path, fmt_path, vb_path=vb_bin_path,
                                                                  ib_path=ib_bin_path, **migoto_raw_import_options)
                        # Although the name will have 001 002 after copying, it does not affect normal use, as long as it achieves the effect
                        for obj in obj_results:
                            new_object = obj.copy()
                            new_object.data = obj.data.copy()

                            collection.objects.link(new_object)
                            bpy.data.objects.remove(obj)
                    else:
                        self.report({'ERROR'}, "Can't find .fmt file!")
                except Fatal as e:
                    self.report({'ERROR'}, str(e))

        return {'FINISHED'}


class MMTExportAllIBVBModel(bpy.types.Operator):
    bl_idname = "mmt.export_all"
    bl_label = "Export all .ib and .vb models to current OutputFolder"

    def execute(self, context):
        # First, get the MMT path
        mmt_path = bpy.context.scene.mmt_props.path
        current_game = ""
        main_setting_path = os.path.join(context.scene.mmt_props.path, "Configs\\Main.json")
        if os.path.exists(main_setting_path):
            main_setting_file = open(main_setting_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            current_game = main_setting_json["GameName"]

        output_folder_path = mmt_path + "Games\\" + current_game + "\\3Dmigoto\\Mods\\output\\"
        # Create an instance of the Export3DMigoto class

        # Iterate through all meshes in the current selection list and export them to the corresponding folder based on the name
        # Get the list of currently selected objects
        selected_collection = bpy.context.collection

        # Iterate through the selected objects
        export_time = 0
        for obj in selected_collection.objects:
            # Check if the object is a mesh object
            if obj.type == 'MESH':
                export_time = export_time + 1
                bpy.context.view_layer.objects.active = obj
                mesh = obj.data  # Get mesh data

                self.report({'INFO'}, "export name: " + mesh.name)

                # Process the current mesh object
                # For example, print the mesh name

                name_splits = str(mesh.name).split("-")
                draw_ib = name_splits[0]
                draw_index = name_splits[1]
                draw_index = draw_index[0:len(draw_index) - 3]
                if draw_index.endswith(".vb."):
                    draw_index = draw_index[0:len(draw_index) - 4]

                # Set the class attribute values
                vb_path = output_folder_path + draw_ib + "\\" + draw_index + ".vb"
                self.report({'INFO'}, "export path: " + vb_path)

                ib_path = os.path.splitext(vb_path)[0] + '.ib'
                fmt_path = os.path.splitext(vb_path)[0] + '.fmt'

                # FIXME: ExportHelper will check for overwriting vb_path, but not ib_path

                export_3dmigoto(self, context, vb_path, ib_path, fmt_path)
        if export_time == 0:
            self.report({'ERROR'}, "Export failed! Please select a collection before clicking one-click export!")
        else:
            self.report({'INFO'}, "One-click export successful! Number of parts successfully exported: " + str(export_time))
        return {'FINISHED'}


class MMTPathProperties(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name="Main Path",
        description="Select a folder path of MMT",
        default=load_path(),
        subtype='DIR_PATH'
    ) # type: ignore

    export_same_number: bpy.props.BoolProperty(
        name="My Checkbox",
        description="This is a checkbox in the sidebar",
        default=False
    ) # type: ignore

    def __init__(self) -> None:
        super().__init__()
        self.subtype = 'DIR_PATH'
        self.path = load_path()


class MMTPathOperator(bpy.types.Operator):
    bl_idname = "mmt.select_folder"
    bl_label = "Select Folder"

    def execute(self, context):
        # Handle folder selection logic here
        bpy.ops.ui.directory_dialog('INVOKE_DEFAULT', directory=context.scene.mmt_props.path)
        return {'FINISHED'}


# MMT Sidebar
class MMTPanel(bpy.types.Panel):
    bl_label = "MMT Plugin" 
    bl_idname = "VIEW3D_PT_MMT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMT'
    # bl_region_width = 600 # TODO Remember to set the width after opening

    def draw(self, context):

        layout = self.layout

        row = layout.row()
        # Add your sidebar content here
        # row.label(text="Version: " + mmt_version)

        # row.operator("wm.url_open", text="Check for updates", icon='URL').url = "https://github.com/StarBobis/MMT-Blender-Plugin"
        props = context.scene.mmt_props
        layout.prop(props, "path")

        # Get the path of MMT.exe
        mmt_path = os.path.join(context.scene.mmt_props.path, "MMT-GUI.exe")
        mmt_location = os.path.dirname(mmt_path)
        if os.path.exists(mmt_path):
            pass
            # layout.label(text="MMT Main Program: " + mmt_path)
        else:
            layout.label(text="Error: Please select the main path of MMT", icon='ERROR')

        # Read the current game name from MainSetting.json
        current_game = ""
        main_setting_path = os.path.join(context.scene.mmt_props.path, "Configs\\Main.json")
        if os.path.exists(main_setting_path):
            main_setting_file = open(main_setting_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            current_game = main_setting_json["GameName"]
            layout.label(text="Current Game: " + current_game)
        else:
            layout.label(text="Error: Please select the main path of MMT", icon='ERROR')

        # Set the OutputFolder path based on the current game name in GameSetting
        output_folder_path = mmt_location + "\\Games\\" + current_game + "\\3Dmigoto\\Mods\\output\\"

        # Draw a CheckBox to store whether to export the same number of vertices
        layout.separator()
        layout.prop(context.scene.mmt_props, "export_same_number", text="Export without changing vertex count")

        layout.separator()
        layout.label(text="Import or export in OutputFolder")

        # Quick import, after clicking this, the default path is OutputFolder, so you can directly import without searching for the path
        operator_import_txt = self.layout.operator("import_mesh.migoto_frame_analysis_mmt", text="Import .txt model files")
        operator_import_txt.directory = output_folder_path

        # Add quick import buf files
        operator_import_ib_vb = self.layout.operator("import_mesh.migoto_raw_buffers_mmt", text="Import .ib & .vb model files")
        operator_import_ib_vb.filepath = output_folder_path

        # Quick export, after clicking this, the default path is OutputFolder, so you can directly export without searching for the path
        operator_export_ibvb = self.layout.operator("export_mesh.migoto_mmt", text="Export .ib & .vb model files")
        operator_export_ibvb.filepath = output_folder_path + "1.vb"

        # Add separator
        layout.separator()

        # One-click quick import of all .txt models in OutputFolder
        layout.label(text="One-click import and export in OutputFolder")
        operator_fast_import = self.layout.operator("mmt.import_all", text="One-click import all .ib & .vb model files")

        # One-click quick export of all models in the selected Collection to the corresponding hash value folder, and directly call MMT.exe's Mod generation method, so that you can refresh and see the effect in the game after exporting.
        operator_export_ibvb = self.layout.operator("mmt.export_all", text="One-click export selected MMT collection")

        # Add separator
        layout.separator()

        # Export MMD's Bone Matrix, continuous bone transformation matrix, and generate ini file
        layout.label(text="Bone Skin Animation Mod")
        layout.prop(context.scene, "mmt_mmd_animation_mod_start_frame")
        layout.prop(context.scene, "mmt_mmd_animation_mod_end_frame")
        layout.prop(context.scene, "mmt_mmd_animation_mod_play_speed")
        operator_export_mmd_bone_matrix = layout.operator("mmt.export_mmd_animation_mod", text="Export Animation Mod")
        operator_export_mmd_bone_matrix.output_folder = output_folder_path

        # # Add separator
        # layout.separator()
        #
        # # Convert each frame of the current animation to a Position.buf and export, and generate frame-by-frame ini file
        # row = layout.row()
        # row.label(text="FrameBased Animation Mod")
        # operator_export_mmd_bone_matrix = row.operator("export_mesh.migoto", text="Export Position Files")
        # row = layout.row()
        # row.prop(context.scene, "mmt_mmd_animation_mod_start_frame")
        # row.prop(context.scene, "mmt_mmd_animation_mod_end_frame")
        # row.prop(context.scene, "mmt_mmd_animation_mod_play_speed")
        # # Add separator
        # layout.separator()
        #
        # # One-click quick import of all .txt models in OutputFolder
        # layout.label(text="ShapeKey Mod")

