# Game Translation Workflow Overview

This workflow is a Python-based automation pipeline designed to translate game assets, specifically Unreal Engine's `.uasset` (game content) and `.locres` (localization resource) files, from English to Brazilian Portuguese. It orchestrates external tools like UAssetGUI and leverages an AI model (Google AI Studio's Gemini) to streamline the entire localization process.

## How the Workflow Works: The Big Picture

The core idea is to:
1.  **Extract**: Get translatable text out of complex game files into a simple JSON format.
2.  **Translate**: Use an AI to translate this JSON text.
3.  **Inject**: Put the translated text back into the game files.
4.  **Validate**: (Optionally) test the translated files to ensure they don't break the game.

This process is split into two main paths, one for `.uasset` files and another for `.locres` files, with additional utility and quality assurance steps.

## Core Workflow: `.uasset` Files (Game Content)

This is the main automated pipeline for translating game logic and UI elements.

1.  **Find & Convert (`0_uasset_to_json.py`)**:
    *   The workflow starts by scanning your raw Unreal Engine asset folder (`1_RAW`).
    *   It uses a quick binary search to identify `.uasset` files that likely contain actual text (ignoring purely binary assets).
    *   These text-containing `.uasset` files are then converted into editable JSON format using the `UAssetGUI` tool. These JSONs serve as the "template."

2.  **Extract & Chunk (`1_json_divide.py`)**:
    *   From the converted JSONs, the script intelligently extracts *only* the strings that are meant for translation, filtering out technical code, IDs, or other non-translatable data based on predefined rules (`config.py`).
    *   To make translation manageable for the AI, this extracted text is then divided into smaller JSON "chunks."

3.  **AI Translation (`2_json_translate_all.py`)**:
    *   Each JSON chunk is sent to a powerful AI model (Google AI Studio's Gemini).
    *   The AI translates the English text to Brazilian Portuguese, focusing on preserving game-specific tags and formatting.
    *   The translated chunks are saved.

4.  **Inject Translation (`4_json_join.py`)**:
    *   The translated text from the chunks is carefully merged back into the original JSON template for each asset, ensuring that each translated string goes into its correct place.
    *   During this step, the script also "learns" by noting if the AI returned the exact same text for an entry. This suggests a technical term that might need to be added to a "blacklist" for future runs, improving accuracy and reducing unnecessary AI calls.

5.  **Recompile & Clean (`5_json_fix_corruption.py`)**:
    *   The fully translated JSON is converted back into its original `.uasset` format using `UAssetGUI`.
    *   A backup of the original `.uasset` is created for safety.
    *   Finally, all temporary files and folders generated during the process for that specific asset are cleaned up.

6.  **Orchestration (`main.py`)**:
    *   A central script (`main.py`) manages this entire flow, processing one `.uasset` file at a time. It handles error checks, skips already-translated files, and ensures a smooth transition between each step. If a potential blacklist term is found, it can pause the entire workflow for your review.

## Secondary Workflow: `.locres` Files (Localization Resources)

This workflow handles `.locres` files, which are often simpler key-value pairs for localized strings, typically found in CSV-like structures.

1.  **Preparation (External Tool)**:
    *   You'll first need an external tool (not part of this repository) to convert your `.locres` file into a single, structured JSON file (e.g., `csvjson.json`) that this workflow can understand.

2.  **Split (`csv_scripts/1_split_locres_json.py`)**:
    *   This script takes the master `csvjson.json` and divides it into smaller, manageable chunks for AI translation, similar to the `.uasset` workflow.

3.  **Translate (`csv_scripts/2_translate_locres_json.py`)**:
    *   The AI model translates these chunks from English to Brazilian Portuguese in parallel, optimizing speed.

4.  **Join (`csv_scripts/3_join_locres_json.py`)**:
    *   All the translated chunks are recombined into a single, comprehensive `traducao_PTBR.json` file.
    *   If any translation is missing or malformed (which can happen with AI), a special `[FALTOU_TRADUCAO]` tag is inserted to flag it.

5.  **Repair (`csv_scripts/4_repair_locres_json.py`)**:
    *   This is a dynamic tool. If `[FALTOU_TRADUCAO]` tags are found, this script can extract *only* those missing entries into new repair chunks. You can then manually translate these or re-feed them to the AI. Once translated, running the script again injects these fixes back into the main `traducao_PTBR.json`.

6.  **Finalization (External Tool)**:
    *   After `traducao_PTBR.json` is complete and verified, you use your external tool again to convert it back into the `.locres` file format ready for the game.

## Utility & Quality Assurance Scripts

Beyond the main translation pipelines, several scripts help manage and validate the process:

*   **`pre_verification_cleaner.py`**:
    *   **Purpose**: A "smart filter" that runs *before* the main `.uasset` workflow. It quickly scans all original JSONs and marks those that definitively contain no translatable text as `.json.bak`. This prevents the AI from wasting time and API credits on irrelevant files.

*   **`restore_bak.py`**:
    *   **Purpose**: A simple tool to undo the `.json.bak` renaming, bringing files back into the processing queue if needed.

*   **`automatic_judge_qa.py`**:
    *   **Purpose**: This is an advanced automated game tester for `.uasset` files. It performs a "real-world" test for each translated asset:
        1.  It automatically converts the translated JSON back to `.uasset` (even simulating mouse clicks and keyboard shortcuts in UAssetGUI if necessary!).
        2.  Packages the `.uasset` into a game mod (`.pak` file).
        3.  Installs the mod into the game directory.
        4.  Launches the game and monitors it for crashes, freezes ("Not Responding"), or critical error pop-ups for a set duration.
        5.  Logs which assets caused problems (a "blacklist" of crashing mods) and which passed the test, providing crucial confidence in the translation's stability.

## Key Components

*   **`config.py`**: Your central control panel. This file holds all paths, AI settings (API key, model, temperature), and crucial rules (whitelists, blacklists, regex) that define what text gets extracted and how it's treated. **You must customize this file for your specific game and environment.**
*   **UAssetGUI**: An essential external tool that converts Unreal Engine `.uasset` files to/from human-readable JSON.
*   **Google AI Studio (Gemini)**: The large language model (LLM) that performs the actual translation. Configurable for different levels of creativity or literalness.
*   **Blacklists & Whitelists**: Carefully curated lists (in `config.py`) that tell the workflow *what to translate* and *what to absolutely ignore* (e.g., game code, internal IDs, specific character names). The workflow even helps you expand these blacklists over time.

This workflow is a powerful tool for large-scale game localization, combining automation with intelligent AI to produce translated assets efficiently and with built-in quality checks.

---

### 📜 License and Credits

This project is open-source. Should these scripts provided here be utilized for other projects, **credit to the original creator is kindly requested**.

**Credits:** ツFinuraBR

---
