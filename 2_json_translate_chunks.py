import os
import json
import time
import re
import threading
import sys 
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    CHUNK_DIR_1_TO_TRANSLATE,
    CHUNK_DIR_2_TRANSLATED,
    AI_MODEL_NAME,
    AI_TIMEOUT_SECONDS,
    AI_MAX_RETRIES,
    API_KEY,
    AI_TEMPERATURE,
    MAX_WORKERS
)

try:
    from openai import OpenAI  
except ImportError:
    print("❌ Error: The 'openai' library is not installed.")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

input_folder = CHUNK_DIR_1_TO_TRANSLATE
output_folder = CHUNK_DIR_2_TRANSLATED

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

SYSTEM_PROMPT = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'p' verbatim. NEVER alter paths.
2. Translate 't' values only."""

def validate_tag_integrity(original_text: str, translated_text: str) -> bool:
    pattern = re.compile(r'\{.*?\}|<.*?>|%[sd]')
    original_tags = pattern.findall(original_text)
    translated_tags = pattern.findall(translated_text)
    return len(original_tags) == len(translated_tags)

def clean_ai_response(raw_text_response: str):
    try:
        raw_data = json.loads(raw_text_response)
        if isinstance(raw_data, dict) and "data" in raw_data:
            translated_list = raw_data["data"]
        elif isinstance(raw_data, list):
            translated_list = raw_data
        else:
            return None
        return json.dumps(translated_list, ensure_ascii=False, indent=2)
    except Exception as e:
        # print(f"Error cleaning AI response: {e}")
        return None

def check_final_status() -> bool:
    input_files = set([f for f in os.listdir(input_folder) if f.endswith('.json')])
    output_files = set([f for f in os.listdir(output_folder) if f.endswith('.json')])
    
    missing_files = input_files - output_files
    if missing_files:
        print(f"\n❌ ERROR: {len(missing_files)} files are missing from output.")
        return False
    
    for f in output_files:
        path = os.path.join(output_folder, f)
        if os.path.getsize(path) < 10:
            print(f"❌ ERROR: Output file {f} is incomplete or empty.")
            return False
    return True

def ai_call_thread(text_to_translate: str, result_container: dict):
    try:
        response = client.chat.completions.create(
            model=AI_MODEL_NAME,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text_to_translate}
            ],
            temperature=AI_TEMPERATURE,
            extra_body={
                'extra_body': {
                    "google": {
                    "thinking_config": {
                        "thinking_level": "high"
                    }
                    }
                }
            }
        )
        extracted_text = response.choices[0].message.content
        if extracted_text:
            result_container['result'] = clean_ai_response(extracted_text)
        else:
            result_container['error'] = "AI returned an empty response."
    except Exception as e:
        result_container['error'] = str(e)

def get_safe_translation(original_text_json: str, file_name: str) -> str | None:
    for attempt in range(1, AI_MAX_RETRIES + 1):
        
        container = {'result': None, 'error': None}
        thread = threading.Thread(target=ai_call_thread, args=(original_text_json, container))
        thread.daemon = True
        thread.start()
        
        thread.join(timeout=AI_TIMEOUT_SECONDS)
        
        if thread.is_alive():
            print(f"⏳ [{file_name}] Timeout (Attempt {attempt})")
            continue
            
        if container['error']:
            error_message = str(container['error'])
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                print(f"⚠️ [{file_name}] Rate limit hit. Waiting 60s...")
                time.sleep(60)
            else:
                print(f"❌ [{file_name}] Error: {error_message}")
            continue
            
        if container['result']:
            return container['result']
            
    return None

def process_single_file(file_name: str) -> str:
    input_path = os.path.join(input_folder, file_name)
    output_path = os.path.join(output_folder, file_name)
    
    if os.path.exists(output_path):
        return f"⏭️ {file_name} already exists."

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        expected_item_count = len(original_data)
        print(f"🚀 Starting: {file_name} ({expected_item_count} items)")
        
        raw_ai_response = get_safe_translation(json.dumps(original_data, ensure_ascii=False), file_name)
        
        if not raw_ai_response: 
            return f"❌ Critical failure in {file_name}: AI returned no data after multiple attempts."

        translated_data = json.loads(raw_ai_response)
        
        if isinstance(translated_data, dict):
            for key in translated_data:
                if isinstance(translated_data[key], list):
                    translated_data = translated_data[key]
                    break

        if not isinstance(translated_data, list) or len(translated_data) != expected_item_count:
            return f"❌ {file_name}: Incorrect item count ({len(translated_data)}/{expected_item_count})"

        for i in range(expected_item_count):
            if not validate_tag_integrity(original_data[i]['t'], translated_data[i]['t']):
                return f"❌ {file_name}: Corrupted tags at index {i}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_data, f, indent=2, ensure_ascii=False)

        return f"✅ Finished: {file_name}"
    
    except Exception as e:
        return f"❌ Unexpected error in {file_name}: {e}"

def execute_parallel_translation():
    all_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    files_to_process = [f for f in all_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if not files_to_process: 
        print("✅ All files have already been processed.")
        return
    
    total_to_process = len(files_to_process)
    print(f"🤖 [STARTING PARALLEL TRANSLATION: {total_to_process} FILES WITH {MAX_WORKERS} WORKERS]\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for filename in files_to_process:
            future = executor.submit(process_single_file, filename)
            futures[future] = filename
            time.sleep(1)

        for future in as_completed(futures):
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"❌ Critical error in thread: {e}")

def main():
    execute_parallel_translation()
    
    if check_final_status():
        print(f"\n🏁 Workflow successfully completed.")
    else:
        print("\n⚠️ The workflow finished with pending issues.")
        sys.exit(1)

if __name__ == '__main__':
    main()