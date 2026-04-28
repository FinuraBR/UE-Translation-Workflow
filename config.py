import os
import re
from typing import List

# === BASIC CONFIGURATION ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_ASSETS_PATH = r"D:\EP1\1_RAW" # Path to your raw game assets
FILTERED_ASSETS_PATH = r"D:\EP1\2_FILTRADO" # Destination for filtered assets
MISSING_TRANSLATION_TAG = "[FALTOU_TRADUCAO]"

# === STRICT RULES CONFIGURATION (Extraction Filters) ===

# Regex to filter out "junk" that doesn't need translation (numbers, IDs, URLs, code)
TEXT_FILTER_REGEX = re.compile(
    r'^[\d\s\W_]+$|'              # Only numbers, spaces, and symbols (e.g., "10/10", ":", "100")
    r'^[a-zA-Z]$|'                # Only a single letter (e.g., "L", "R", "X")
    r'^www\..*|^https?://.*|'     # URLs
    r'^#\d+$'                     # Color or number IDs (e.g., #15)
)

# 1. REQUIRED: Defines which 'History' types are valid for translation
REQUIRED_HISTORY_TYPE = { "Base", "None", "NamedFormat" }

# 2. PROHIBITED: If the object has this flag, it's considered "immutable" (cannot be translated)
FORBIDDEN_FLAG = "Immutable"

# 3. WHITELIST: Defines which JSON object types can contain translatable text
WHITELIST_TYPES = {
    "TextProperty", 
    "TextPropertyData", 
    "FStringTable", 
    "StringTableExport",
    "StrProperty"
}

# 4. TECHNICAL BLACKLIST: Words that the AI might confuse but should NOT be translated
CONTENT_BLACKLIST = {
    "cutscene"
}

# 5. PROPERTY NAMES: System variables that should not be altered
VARIABLE_NAME_BLACKLIST = {
    "internalname", "classname", "tagname"
}

# --- RETRY SETTINGS (Resilience) ---
AI_TIMEOUT_SECONDS = 180  # Maximum time (seconds) the script waits for an AI response
AI_MAX_RETRIES = 5    # Number of retries if the AI fails due to instability

# === EXTERNAL TOOLS CONFIGURATION (Unreal Engine) ===
# Path to the UAssetGUI executable (used for JSON <-> UAsset conversion)
UASSET_GUI_PATH = r"D:\Ferramentas\UAssetGUI.exe"
UE_VERSION = "VER_UE4_26"    # Unreal Engine version used in the 'fromjson' process

# Defines the maximum character limit per part file (prevents AI context window errors)
MAX_CHARS_PER_CHUNK = 8000

# === AI CONFIGURATION ===
# Recommended free models (from most to least recommended): "gemini-2.5-flash-lite" | "gemini-2.5-flash" | "gemini-3-flash-preview" | "gemini-3.1-flash-lite-preview"
AI_MODEL_NAME = "gemini-3.1-flash-lite-preview"
AI_TEMPERATURE = 1.0 # Recommended 0.6. Higher values for more creative translations, lower for more literal.
MAX_WORKERS = 5 # Number of files translated simultaneously

API_KEY = "" # Your Google AI Studio API Key

# === FOLDER STRUCTURE (Workflow) ===
ORIGINAL_JSON_DIR = os.path.join(BASE_DIR, "3_JSON_ORIGINAL") # Where extracted JSONs are stored
FINAL_MOD_DIR = os.path.join(BASE_DIR, "Traducao_PTBR_P")     # Where ready UAssets are saved

# Intermediate processing folders (Pipeline)
CHUNK_DIR_1_TO_TRANSLATE = os.path.join(BASE_DIR, "4_partes_para_traduzir")      # JSON divided into chunks
CHUNK_DIR_2_TRANSLATED = os.path.join(BASE_DIR, "6_partes_verificadas")       # Validated and ready for injection

# === CONTROL FILES ===
TRANSLATED_JSON_FILE = os.path.join(BASE_DIR, "json_PTBR.json")      # Final injection file
PROJECT_STATUS_FILE = os.path.join(BASE_DIR, "projeto_status.json")        # Stores loop progress

# === BINARY FILTER KEYWORDS (Step 0) ===
# These keywords are used to quickly scan .uasset files before conversion.
# They help discard files that do not contain text.
BINARY_KEYWORDS: List[bytes] = {
    # UTF-8 versions (plain text)
    b"LocalizedString",
    b"CultureInvariantString",
    b"TextPropertyData", 
    b"TextProperty",
    b"SourceString",
    b"FStringTable",
    b"StringTableExport",
    b"StrProperty",
    b"DisplayString",

    # UTF-16 versions (as Unreal Engine saves internally in binaries)
    b'L\x00o\x00c\x00a\x00l\x00i\x00z\x00e\x00d\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'C\x00u\x00l\x00t\x00u\x00r\x00e\x00I\x00n\x00v\x00a\x00r\x00i\x00a\x00n\x00t\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'T\x00e\x00x\x00t\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00D\x00a\x00t\x00a\x00',
    b'T\x00e\x00x\x00t\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00',
    b'S\x00o\x00u\x00r\x00c\x00e\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'F\x00S\x00t\x00r\x00i\x00n\x00g\x00T\x00a\x00b\x00l\x00e\x00',
    b'S\x00t\x00r\x00i\x00n\x00g\x00T\x00a\x00b\x00l\x00e\x00E\x00x\x00p\x00o\x00r\x00t\x00',
    b'S\x00t\x00r\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00',
    b'D\x00i\x00s\x00p\x00l\x00a\x00y\x00S\x00t\x00r\x00i\x00n\x00g\x00',
}

# Real keys in the JSON that contain translatable text for the injection script
TEXT_INJECTION_KEYS = {
    "SourceString",
    "LocalizedString",
    "CultureInvariantString",
    "DisplayString"
}