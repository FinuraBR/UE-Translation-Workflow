import json
import os
import glob
import re
import sys
from config import *

def register_blacklist_suggestion(text: str) -> bool:
    log_path = os.path.join(BASE_DIR, "suggestions_blacklist.txt")
    cleaned_text = text.strip().replace('"', '').lower()
    
    if not cleaned_text or len(cleaned_text) > 25:
        return False

    existing_terms = set()
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            existing_terms = set(re.findall(r'"(.*?)"', content.lower()))

    if cleaned_text not in existing_terms:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f'"{cleaned_text}", ')
        return True
    return False

def navigate_and_inject(json_object: dict, path: str, translated_text: str) -> tuple[bool, bool]:
    try:
        if translated_text is None:
            return False, False

        path_parts = re.findall(r'([^.\[\]]+)', path)
        parent_path_parts = path_parts[:-1]
        target_original_key = path_parts[-1]
        
        current_node = json_object
        for part in parent_path_parts:
            if part.isdigit():
                current_node = current_node[int(part)]
            else:
                current_node = current_node[part]

        original_reference_value = current_node.get("SourceString") or current_node.get("CultureInvariantString") or current_node.get(target_original_key)
        
        new_blacklist_item_detected = False
        if str(original_reference_value).strip() == translated_text.strip():
            new_blacklist_item_detected = register_blacklist_suggestion(translated_text)

        something_changed = False
        for key_to_inject in TEXT_INJECTION_KEYS:
            if key_to_inject in current_node:
                old_value = current_node.get(key_to_inject)
                if old_value != translated_text:
                    current_node[key_to_inject] = translated_text
                    something_changed = True
        
        if target_original_key not in current_node:
            current_node[target_original_key] = translated_text
            something_changed = True

        return something_changed, new_blacklist_item_detected

    except Exception:
        return False, False

def main():
    if not os.path.exists(PROJECT_STATUS_FILE):
        sys.exit(1)
    
    with open(PROJECT_STATUS_FILE, 'r', encoding='utf-8') as f:
        status_info = json.load(f)

    file_name = status_info['name']
    template_path = os.path.join(ORIGINAL_JSON_DIR, status_info['subpath'], status_info['name'] + ".json")
    
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}")
        sys.exit(1)

    with open(template_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    translated_parts_files = sorted(glob.glob(os.path.join(CHUNK_DIR_2_TRANSLATED, 'part_*.json')))
    if not translated_parts_files:
        print("⚠️ No translated parts found.")
        sys.exit(1)

    total_injected_items = 0
    new_technical_terms_detected = False

    for part_file in translated_parts_files:
        with open(part_file, 'r', encoding='utf-8') as f:
            try:
                translation_list = json.load(f)
            except json.JSONDecodeError:
                continue

            for item in translation_list:
                path = item.get('p')
                translated_value = item.get('t')
                
                if path and translated_value is not None:
                    changed, new_term = navigate_and_inject(original_data, path, translated_value)
                    if changed:
                        total_injected_items += 1
                    if new_term:
                        new_technical_terms_detected = True

    os.makedirs(os.path.dirname(TRANSLATED_JSON_FILE), exist_ok=True)
    with open(TRANSLATED_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(original_data, f, indent=2, ensure_ascii=False)
    
    if total_injected_items == 0:
        print(f"ℹ️ {status_info['name']}: No changes necessary.")
        files_to_clean = [
            os.path.join(BASE_DIR, f"{file_name}_SAFE.json"),
            TRANSLATED_JSON_FILE
        ]
        for file_path_to_remove in files_to_clean:
            if os.path.exists(file_path_to_remove):
                try:
                    os.remove(file_path_to_remove)
                except: pass
        
        if new_technical_terms_detected:
            print("📢 New technical items detected even without translation applied.")
            sys.exit(11)
        
        sys.exit(10)
    
    print(f"✅ Success: {total_injected_items} blocks synchronized in {status_info['name']}.")
    
    sys.exit(0)

if __name__ == '__main__': 
    main()
