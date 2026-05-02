import os
import sys
import time
import json
import threading
import random 
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *

try:
    from openai import OpenAI  
except ImportError:
    print("❌ Error: The 'openai' library is not installed.")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

script_dir = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(script_dir, "1_partes_para_traduzir")
output_folder = os.path.join(script_dir, "2_partes_traduzidas")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

DEFAULT_SYSTEM_PROMPT = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'p' verbatim. NEVER alter paths.
2. Translate 't' values only.""" 

def get_dynamic_workers(total_files):
    return min(os.cpu_count() or 4, total_files or 1)

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
        return None

def execute_ai_call_in_thread(system_prompt: str, user_prompt: str, result_container: dict):
    try:
        response = client.chat.completions.create(
            model=AI_MODEL_NAME, 
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
        result_container['res'] = response.choices[0].message.content
    except Exception as e:
        result_container['error'] = e

def get_translation_with_timeout(json_content: str, file_name: str) -> str | None:
    for attempt in range(1, AI_MAX_RETRIES + 1):
        container = {'res': None, 'erro': None}
        thread = threading.Thread(target=execute_ai_call_in_thread, args=(DEFAULT_SYSTEM_PROMPT, json_content, container))
        thread.daemon = True
        thread.start()
        
        thread.join(timeout=AI_TIMEOUT_SECONDS)
        
        if thread.is_alive():
            print(f"⏳ [{file_name}] Timeout (Attempt {attempt})")
            continue

        if container['erro']:
            error_message = str(container['erro'])
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                wait_time = 60 + random.uniform(0, 1)
                print(f"⚠️ [{file_name}] Rate limit hit. Waiting {wait_time:.2f}s... (Attempt {attempt})")
                time.sleep(wait_time)
            else:
                print(f"❌ [{file_name}] Error: {error_message} (Attempt {attempt})")
            continue

        final_text = container['res']
        result = clean_ai_response(final_text)
        
        if result:
            return result
    return None

def process_single_file(filename: str, input_dir: str, output_dir: str) -> str:
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, filename)

    print(f"🔄 Starting: {filename}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            return f"⚠️ {filename} is empty."

        translation = get_translation_with_timeout(content, filename)

        if translation:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            return f"✅ Saved: {filename}"
        else:
            return f"❌ Failed: {filename} after all attempts."

    except Exception as e:
        return f"💥 Error in {filename}: {e}"

def check_final_status() -> bool:
    """
    Checks if all input files have corresponding, valid output files after translation.
    """
    global input_folder, output_folder
    
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

def execute_parallel_translation():
    global input_folder, output_folder
    
    all_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    total_to_process = len(all_files)
    
    if not all_files:
        print("✨ No JSON chunks found to translate. Exiting.")
        return
        
    workers = get_dynamic_workers(total_to_process)
    pending_files = [f for f in all_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if not pending_files:
        print("✨ All files are already processed!")
        return

    print(f"\n🚀 Starting Parallel Translation | {len(pending_files)} files | Threads: {workers}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_single_file, f, input_folder, output_folder) for f in pending_files]
        
        for future in as_completed(futures):
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"❌ Critical error in thread: {e}")

    print("\n🏁 Translation workflow ended.")

def main():
    execute_parallel_translation()
    
    if check_final_status():
        print(f"\n🏁 Workflow successfully completed.")
    else:
        print("\n⚠️ The workflow finished with pending issues.")
        sys.exit(1)

if __name__ == '__main__':
    main()
