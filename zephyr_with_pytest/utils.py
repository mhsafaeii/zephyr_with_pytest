

def find_folder_id_by_name(folders, folder_name):
    """Search for a folder by name in the folder tree"""

    for folder in folders:
        if folder['name'] == folder_name:
            return folder['id']  # Return folder ID if found

        # If the folder has child elements, continue searching in them
        if folder.get('children'):
            child_id = find_folder_id_by_name(folder['children'], folder_name)
            if child_id:
                return child_id

    return None  # If folder with the required name is not found


def get_or_create_folder(api_client, folders, folder_name):
    """Get or create a new folder"""

    # Folder tree
    folder_tree = folders.get('children', [])

    # Search for folder by name
    folder_id = find_folder_id_by_name(folder_tree, folder_name)

    if folder_id:
        print(f"Folder '{folder_name}' found, ID: {folder_id}")
        return folder_id
    else:
        # If not found, create folder in root (without parent_id)
        print(f"Folder '{folder_name}' not found, creating a new one.")
        folder_id = api_client.create_test_run_folder(folder_name)
        print(f"Created folder '{folder_name}', ID: {folder_id}")
        return folder_id
