import os
import sys
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AI_TIMEOUT_SECONDS,
    AI_MAX_RETRIES,
    API_KEY,
    AI_MODEL_NAME,
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

DEFAULT_SYSTEM_PROMPT = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'key' and 'source 'verbatim. NEVER alter paths.
2. Translate 'Translation' values only.""" 

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

def get_translation_with_timeout(json_content: str) -> str | None:
    for attempt in range(1, AI_MAX_RETRIES + 1):
        container = {'res': None, 'erro': None}
        thread = threading.Thread(target=execute_ai_call_in_thread, args=(DEFAULT_SYSTEM_PROMPT, json_content, container))
        thread.daemon = True
        thread.start()
        
        thread.join(timeout=AI_TIMEOUT_SECONDS)
        
        if thread.is_alive():
            print(f"⏳ Timeout on attempt {attempt}")
            continue

        if container['erro']:
            print(f"❌ API Error: {container['erro']}")
            time.sleep(1)
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

        translation = get_translation_with_timeout(content)

        if translation:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            return f"✅ Saved: {filename}"
        else:
            return f"❌ Failed: {filename} after all attempts."

    except Exception as e:
        return f"💥 Error in {filename}: {e}"

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "1_partes_para_traduzir")
    output_folder = os.path.join(script_dir, "2_partes_traduzidas")

    if not os.path.exists(output_folder): os.makedirs(output_folder)

    all_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    pending_files = [f for f in all_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if not pending_files:
        print("✨ All files are already processed!")
        return

    print(f"\n🚀 Starting Parallel Translation | {len(pending_files)} files | Threads: {MAX_WORKERS}\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_file, f, input_folder, output_folder) for f in pending_files]
        
        for future in futures:
            print(future.result())

    print("\n🏁 Translation workflow ended.")

if __name__ == '__main__':
    main()