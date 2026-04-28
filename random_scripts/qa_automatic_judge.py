"""
Automated QA Judge Script.
Objective: Automatically validate each converted file.
Flow:
1. Converts JSON -> UAsset (using UI Automation in UAssetGUI).
2. Packages into a .pak file (via batch script).
3. Installs the mod in the game.
4. Opens the game and monitors for 'Crash' or 'Not Responding' states.
"""

import os
import subprocess
import shutil
import time
import pyautogui
import pyperclip
import psutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    UASSET_GUI_PATH, UE_VERSION, ORIGINAL_JSON_DIR, 
    FINAL_MOD_DIR
)

GAME_MODS_DIR = r"D:\JOGOS\threeoutof10Ep1\ThreeTen\Content\Paks\~mods"
GAME_EXECUTABLE = r"D:\JOGOS\threeoutof10Ep1\ThreeTen.exe"
UNREAL_PAK_BATCH_SCRIPT = r"D:\Ferramentas\Engine\Binaries\Win64\UnrealPak-Batch-With-Compression.bat"
TEST_DURATION_SECONDS = 5

CRASH_BLACKLIST_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blacklist_crashes.txt")
SUCCESS_TESTS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testes_concluidos.txt")

def wait_for_window(titles: list[str], timeout=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        for t in titles:
            windows = pyautogui.getWindowsWithTitle(t)
            if windows and windows[0].visible: return windows[0]
        time.sleep(0.1)
    return None

def convert_with_ui_automation(uasset_output_path: str, json_input_path: str) -> bool:
    proc = subprocess.Popen([UASSET_GUI_PATH, json_input_path, UE_VERSION])
    start_time = time.time()
    automation_steps = {"SAVE_INITIATED": False}
    
    while proc.poll() is None:
        for title in ["Notice", "Uh oh!", "Error", "Warning"]:
            error_window = wait_for_window([title], 0.2)
            if error_window:
                try: error_window.activate(); pyautogui.press('enter'); time.sleep(0.4)
                except: pass

        if time.time() - start_time > 1 and not automation_steps["SAVE_INITIATED"]:
            main_window = wait_for_window(["UAssetGUI"], 1)
            if main_window:
                try:
                    main_window.activate(); pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(0.4)
                    automation_steps["SAVE_INITIATED"] = True
                except: pass
        
        if automation_steps["SAVE_INITIATED"]:
            save_as_window = wait_for_window(["Save As", "Salvar como"], 0.4)
            if save_as_window:
                try:
                    save_as_window.activate(); pyperclip.copy(uasset_output_path); pyautogui.hotkey('ctrl', 'v'); time.sleep(0.4); pyautogui.press('enter'); time.sleep(0.4); pyautogui.press('enter')
                except: pass

        if os.path.exists(uasset_output_path) and os.path.getsize(uasset_output_path) > 10:
            proc.terminate(); os.system("taskkill /f /im UAssetGUI.exe >nul 2>&1"); return True
            
        if time.time() - start_time > 35: break
        time.sleep(0.5)
    
    proc.terminate(); os.system("taskkill /f /im UAssetGUI.exe >nul 2>&1")
    return os.path.exists(uasset_output_path) and os.path.getsize(uasset_output_path) > 10

def process_single_file_for_qa(json_file_path: str, relative_path: str, file_name: str) -> tuple[bool, str]:
    test_root_folder = os.path.join(FINAL_MOD_DIR, "Traducao_PTBR_P")
    
    if os.path.exists(test_root_folder):
        shutil.rmtree(test_root_folder)
    
    destination_folder = os.path.join(test_root_folder, relative_path)
    os.makedirs(destination_folder, exist_ok=True)
    final_uasset_output = os.path.join(destination_folder, f"{file_name}.uasset")

    if not convert_with_ui_automation(json_input_path=json_file_path, uasset_output_path=final_uasset_output):
        return False, "Conversion"

    subprocess.run(["cmd", "/c", UNREAL_PAK_BATCH_SCRIPT, test_root_folder], stdout=subprocess.DEVNULL)
    
    generated_pak = os.path.join(FINAL_MOD_DIR, f"{os.path.basename(test_root_folder)}.pak")
    destination_pak = os.path.join(GAME_MODS_DIR, "Single_Test_P.pak")
    
    if not os.path.exists(generated_pak): return False, "Pak not generated"
    if os.path.exists(destination_pak): os.remove(destination_pak)
    shutil.move(generated_pak, destination_pak)

    game_process = subprocess.Popen(GAME_EXECUTABLE, cwd=os.path.dirname(GAME_EXECUTABLE))
    
    try:
        process = psutil.Process(game_process.pid)
    except psutil.NoSuchProcess:
        return False, "Game did not open"
    
    start_test_time = time.time() # Renamed start_time
    while time.time() - start_test_time < TEST_DURATION_SECONDS:
        if game_process.poll() is not None:
            os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
            game_process.terminate()
            return False, "Crash (Closed)"

        game_windows = pyautogui.getWindowsWithTitle("ThreeTen")
        if game_windows:
            if "Not Responding" in game_windows[0].title:
                os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
                game_process.terminate()
                return False, "Crash (Not Responding)"
        
        for title in ["Error", "Crash", "Fatal Error!"]:
            error_window = wait_for_window([title], 0.1)
            if error_window:
                os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
                game_process.terminate()
                return False, f"Crash (Window: {title})"
        
        time.sleep(0.5)
    
    os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
    game_process.terminate()
    shutil.rmtree(test_root_folder)

    return True, "Ok"

if __name__ == "__main__":
    print("--- STARTING AUTOMATED JUDGE ---")
    
    crashed_blacklist = []; successful_tests = []
    if os.path.exists(CRASH_BLACKLIST_LOG):
        with open(CRASH_BLACKLIST_LOG, "r") as f: crashed_blacklist = f.read().splitlines()
    if os.path.exists(SUCCESS_TESTS_LOG):
        with open(SUCCESS_TESTS_LOG, "r") as f: successful_tests = f.read().splitlines()

    files_to_test = []
    for root, _, files in os.walk(ORIGINAL_JSON_DIR):
        for f in files:
            if f.endswith(".json"):
                file_basename = f.replace(".json", "")
                if file_basename not in crashed_blacklist and file_basename not in successful_tests:
                    files_to_test.append((os.path.join(root, f), os.path.relpath(root, ORIGINAL_JSON_DIR), file_basename))
    
    for json_file_full_path, relative_subpath, file_basename in files_to_test:
        print(f"\n📦 Testing: {file_basename}...", end=" ", flush=True)
        is_successful, status_message = process_single_file_for_qa(json_file_full_path, relative_subpath, file_basename)
        
        if status_message == "Ok":
            print(f"✅ HEALTHY")
            with open(SUCCESS_TESTS_LOG, "a") as f_log: f_log.write(f"{file_basename}\n")
        elif "Crash" in status_message:
            print(f"💀 {status_message} - Blacklist!")
            with open(CRASH_BLACKLIST_LOG, "a") as f_log: f_log.write(f"{file_basename}\n")
        else:
            print(f"⚠️ TECHNICAL FAILURE: {status_message}. Will be attempted again next time.")

    print("\n🏁 TEST COMPLETED!")