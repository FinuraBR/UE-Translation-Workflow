import json
import os
import subprocess
import shutil
import traceback
import sys

from config import (
    UASSET_GUI_PATH, UE_VERSION,
    FILTERED_ASSETS_PATH,
    ORIGINAL_JSON_DIR,
    FINAL_MOD_DIR,
    PROJECT_STATUS_FILE,
    TRANSLATED_JSON_FILE,
    CHUNK_DIR_1_TO_TRANSLATE,
    CHUNK_DIR_2_TRANSLATED
)

def check_prerequisites(status_info: dict) -> bool:
    issues = []
    
    if not os.path.exists(PROJECT_STATUS_FILE):
        issues.append("❌ Status file (project_status.json) not found.")
    
    if not os.path.exists(TRANSLATED_JSON_FILE):
        issues.append("❌ Translated JSON file (json_PTBR.json) not found. Run Step 4 first.")
    
    if not os.path.exists(UASSET_GUI_PATH):
        issues.append(f"❌ UAssetGUI (CLI) not found at: {UASSET_GUI_PATH}")
    
    original_json_source = os.path.join(ORIGINAL_JSON_DIR, status_info['subpath'], f'{status_info["name"]}.json')
    if not os.path.exists(original_json_source):
        issues.append(f"❌ Original JSON file not found: {original_json_source}")
    
    if issues:
        print("\n❌ CRITICAL ISSUES FOUND:")
        for p in issues: print(f"   {p}")
        return False
    return True

def execute_safe_backup(status_info: dict) -> bool:
    try:
        file_name = status_info['name']
        subpath = status_info['subpath']
        
        original_uasset_source = os.path.join(FILTERED_ASSETS_PATH, subpath, f'{file_name}.uasset')
        original_uexp_source = original_uasset_source.replace(".uasset", ".uexp")
        
        backup_uasset_path = original_uasset_source + ".bak"
        if os.path.exists(original_uasset_source):
            shutil.copy2(original_uasset_source, backup_uasset_path)
        else:
            print(f"⚠️ Original UAsset not found at '{original_uasset_source}' for backup.")
        
        backup_uexp_path = original_uexp_source + ".bak"
        if os.path.exists(original_uexp_source):
            shutil.copy2(original_uexp_source, backup_uexp_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during backup: {e}")
        return False

def clean_temporary_files() -> bool:
    try:
        files_to_remove = [TRANSLATED_JSON_FILE, PROJECT_STATUS_FILE]
        
        folders_to_clear = [CHUNK_DIR_1_TO_TRANSLATE, CHUNK_DIR_2_TRANSLATED]
        
        for folder in folders_to_clear:
            if os.path.exists(folder):
                for file_in_folder in os.listdir(folder):
                    file_path_full = os.path.join(folder, file_in_folder)
                    try:
                        if os.path.isfile(file_path_full):
                            os.remove(file_path_full)
                    except Exception: 
                        pass
        
        for file_path_to_remove in files_to_remove:
            if os.path.exists(file_path_to_remove):
                try:
                    os.remove(file_path_to_remove)
                except Exception: 
                    pass
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def execute_json_to_uasset_conversion_cli(status_info: dict) -> bool:
    file_name = status_info['name']
    subpath = status_info['subpath']
    
    input_json_path = os.path.abspath(TRANSLATED_JSON_FILE)
    destination_folder = os.path.join(FINAL_MOD_DIR, subpath)
    os.makedirs(destination_folder, exist_ok=True)
    output_uasset_path = os.path.abspath(os.path.join(destination_folder, f'{file_name}.uasset'))
    print(f"📍 Output UAsset: {output_uasset_path}\n")
    
    try:
        command = [
            str(UASSET_GUI_PATH),
            "fromjson",
            str(input_json_path),
            str(output_uasset_path),
            str(UE_VERSION)
        ]
        
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            creationflags=creation_flags
        )

        if result.returncode == 0:
            if os.path.exists(output_uasset_path) and os.path.getsize(output_uasset_path) > 100:
                return True
            else:
                print("❌ CLI conversion failed: output file not generated or empty.")
                print(f"Output: {result.stdout}")
                return False
        else:
            print(f"❌ UAssetGUI CLI returned error {result.returncode}.")
            print(f"Errors: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error executing UAssetGUI CLI: {e}")
        traceback.print_exc()
        return False

def main() -> bool:
    try:
        if not os.path.exists(PROJECT_STATUS_FILE):
            print("❌ Status file (project_status.json) not found. Run the Manager.")
            return False
        
        with open(PROJECT_STATUS_FILE, 'r', encoding='utf-8') as f:
            status_info = json.load(f)
        
        print(f"📦 Processing: {status_info['name']}\n")
        
        if not check_prerequisites(status_info):
            return False
        
        conversion_successful = execute_json_to_uasset_conversion_cli(status_info)
        
        if conversion_successful:
            execute_safe_backup(status_info)
            clean_temporary_files()
            return True
        else:
            print(f"\n❌ Failed to convert file {status_info['name']} to UAsset.")
            return False
            
    except Exception as e:
        print(f"💥 Critical error in script: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    workflow_success_result = main()
    
    if not workflow_success_result:
        sys.exit(1)