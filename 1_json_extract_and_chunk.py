import json
import os
import sys

from config import (
    REQUIRED_HISTORY_TYPE,
    FORBIDDEN_FLAG,
    WHITELIST_TYPES,
    CONTENT_BLACKLIST,
    VARIABLE_NAME_BLACKLIST,
    TEXT_FILTER_REGEX,
    ORIGINAL_JSON_DIR,
    CHUNK_DIR_1_TO_TRANSLATE,
    PROJECT_STATUS_FILE,
    MAX_CHARS_PER_CHUNK,
    TEXT_INJECTION_KEYS
)

def is_valid_text(obj: dict, text: str) -> bool:

    if not text or not isinstance(text, str) or not text.strip():
        return False
    
    cleaned_text = text.strip()
    lower_text = cleaned_text.lower()

    if lower_text in CONTENT_BLACKLIST:
        return False

    variable_name = str(obj.get("Name", "")).lower()
    if variable_name in VARIABLE_NAME_BLACKLIST:
        return False
    
    if TEXT_FILTER_REGEX.match(cleaned_text):
        return False
    
    # if " " not in cleaned_text and "_" in cleaned_text:
    #    return False

    return True

def extract_recursively(obj: dict | list, extracted_list: list, current_path: str = ""):
    if isinstance(obj, dict):

        history_type = obj.get("HistoryType", "")
        flags = str(obj.get("Flags", ""))

        if history_type in REQUIRED_HISTORY_TYPE and FORBIDDEN_FLAG not in flags:
            
            obj_type = obj.get("Type", obj.get("$type", ""))
            if any(t in obj_type for t in WHITELIST_TYPES):
                
                for key_name in TEXT_INJECTION_KEYS:
                    if key_name in obj:
                        value = obj.get(key_name)

                        if is_valid_text(obj, value):
                            extracted_list.append({
                                "p": f"{current_path}.{key_name}" if current_path else key_name,
                                "t": value
                            })
                            return

        for k, v in obj.items():
            if k in ["Namespace", "Key", "Guid", "Type", "$type", "Flags", "Class", "Outer"]:
                continue
            extract_recursively(v, extracted_list, f"{current_path}.{k}" if current_path else k)
                
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            extract_recursively(item, extracted_list, f"{current_path}[{i}]")

def main():

    if len(sys.argv) >= 3:
        file_name = sys.argv[1]
        file_subpath = sys.argv[2]
        target_file_info = {"name": file_name, "subpath": file_subpath}
    else:

        target_file_info = None
        for root, _, files in os.walk(ORIGINAL_JSON_DIR):
            for f in files:
                if f.endswith(".json") and not f.endswith(".bak"):
                    target_file_info = {
                        "name": f.replace(".json", ""),
                        "subpath": os.path.relpath(root, ORIGINAL_JSON_DIR)
                    }
                    break
            if target_file_info: break
    
    if not target_file_info:
        print(f"ℹ️ No .json files found in '{ORIGINAL_JSON_DIR}' (or all are .bak) to process. Exiting.")
        return

    json_file_path = os.path.join(ORIGINAL_JSON_DIR, target_file_info['subpath'], target_file_info['name'] + ".json")
    
    if not os.path.exists(json_file_path):
        print(f"❌ Error: File not found at {json_file_path}")
        sys.exit(1)

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON from {json_file_path}: {e}")
        sys.exit(1)
    
    with open(PROJECT_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(target_file_info, f, indent=2)

    final_extracted_list = []
    extract_recursively(json_data, final_extracted_list)
    
    if not final_extracted_list:
        sys.exit(10)

    os.makedirs(CHUNK_DIR_1_TO_TRANSLATE, exist_ok=True)
    
    for f in os.listdir(CHUNK_DIR_1_TO_TRANSLATE):
        try:
            os.remove(os.path.join(CHUNK_DIR_1_TO_TRANSLATE, f))
        except OSError as e:
            print(f"⚠️ Could not remove old chunk file {f}: {e}")

    chunks, current_block, current_block_size = [], [], 0
    for item in final_extracted_list:
        item_size = len(json.dumps(item, ensure_ascii=False))

        if (current_block_size + item_size) > MAX_CHARS_PER_CHUNK and current_block:
            chunks.append(current_block)
            current_block, current_block_size = [], 0
        current_block.append(item)
        current_block_size += item_size
    if current_block: chunks.append(current_block)

    for idx, content in enumerate(chunks):
        with open(os.path.join(CHUNK_DIR_1_TO_TRANSLATE, f'part_{idx+1:03d}.json'), 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(final_extracted_list)} items into {len(chunks)} parts for {target_file_info['name']}.")
    sys.exit(0)

if __name__ == '__main__':
    main()