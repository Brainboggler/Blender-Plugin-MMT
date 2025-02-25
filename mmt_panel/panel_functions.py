import os
import bpy
import json


def save_mmt_path(path):
    # Get the path of the current script file
    script_path = os.path.abspath(__file__)

    # Get the working directory of the current plugin
    plugin_directory = os.path.dirname(script_path)

    # Construct the path to the save file
    config_path = os.path.join(plugin_directory, 'Config.json')

    # Create a dictionary object
    config = {'mmt_path': bpy.context.scene.mmt_props.path}

    # Convert the dictionary object to a JSON formatted string
    json_data = json.dumps(config)

    # Save to file
    with open(config_path, 'w') as file:
        file.write(json_data)


def load_path():
    # Get the path of the current script file
    script_path = os.path.abspath(__file__)

    # Get the working directory of the current plugin
    plugin_directory = os.path.dirname(script_path)

    # Construct the path to the config file
    config_path = os.path.join(plugin_directory, 'Config.json')

    # Read the file
    with open(config_path, 'r') as file:
        json_data = file.read()

    # Parse the JSON formatted string into a dictionary object
    config = json.loads(json_data)

    # Read the saved path
    return config['mmt_path']


