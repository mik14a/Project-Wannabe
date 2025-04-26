from typing import Dict, Optional, Tuple
from .settings import load_settings, DEFAULT_SETTINGS # Import settings functions

# --- Instruction Templates (Adjust based on the fine-tuned model's needs) ---
# These are examples and should match the expected format of your LLM.
INSTRUCTION_TEMPLATES = {
    "GEN_INFO": "以下の情報に基づいて小説本文を生成してください。",
    "GEN_ZERO": "自由に小説を生成してください。",
    "CONT_INFO": "参考情報を基に以下の文章の続きを生成してください。",
    "CONT_ZERO": "以下の文章の続きを生成してください。",
    "IDEA_INFO": "以下の情報に基づいて、完全な小説のアイデア（タイトル、キーワード、ジャンル、あらすじ、設定、プロット）を生成してください。",
    "IDEA_ZERO": "自由に小説のアイデア（タイトル、キーワード、ジャンル、あらすじ、設定、プロット）を生成してください。",
}

# INSTRUCTION_TEMPLATES = {
#     "GEN_INFO": "以下の情報を元に、新しい小説の冒頭部分を執筆してください。",
#     "GEN_ZERO": "新しい小説の冒頭部分を執筆してください。",
#     "CONT_INFO": "以下の本文の続きを、参考情報に基づいて執筆してください。",
#     "CONT_ZERO": "以下の本文の続きを執筆してください。",
#     "IDEA_INFO": "以下の情報を元に、小説のアイデア（タイトル、キーワード、ジャンル、あらすじ、設定、プロット）を提案してください。各項目は `# 日本語名:` の形式で記述してください。",
#     "IDEA_ZERO": "新しい小説のアイデア（タイトル、キーワード、ジャンル、あらすじ、設定、プロット）を提案してください。各項目は `# 日本語名:` の形式で記述してください。",
# }

# --- Metadata Formatting ---
METADATA_MAP = {
    "title": "タイトル",
    "keywords": "キーワード",
    "genres": "ジャンル",
    "synopsis": "あらすじ",
    "setting": "設定",
    "plot": "プロット",
    "dialogue_level": "セリフ量", # Add dialogue level
}

# Define the order for metadata in the prompt
INPUT_METADATA_ORDER_JA = [
    "タイトル", "キーワード", "ジャンル", "あらすじ", "設定", "プロット", "セリフ量"
]
# Create a reverse map for easier lookup
KEY_MAP_FROM_JA = {v: k for k, v in METADATA_MAP.items()}


def format_metadata(metadata: Dict[str, str | list[str]], mode: str = "generate") -> str:
    """
    Formats the metadata dictionary into a string for the prompt, respecting order.
    Excludes 'dialogue_level' if mode is 'idea'.
    """
    output = []
    # Iterate based on the defined Japanese name order
    for japanese_name in INPUT_METADATA_ORDER_JA:
        key = KEY_MAP_FROM_JA.get(japanese_name)
        if not key:
            continue # Skip if the Japanese name isn't in our map

        # --- Skip dialogue_level if in idea mode ---
        if mode == "idea" and key == "dialogue_level":
            continue

        value = metadata.get(key) # Get value using the internal key ('title', 'dialogue_level', etc.)
        if value:
            # Handle list types (keywords, genres)
            if key in ["keywords", "genres"] and isinstance(value, list):
                    if value: # Only add if list is not empty
                        # `- ` を付けずに改行で結合 (データセット側に合わせる)
                        output.append(f"# {japanese_name}:\n" + "\n".join(item for item in value))
            # Handle string types (title, synopsis, setting, plot, dialogue_level)
            elif isinstance(value, str) and value.strip():
                 output.append(f"# {japanese_name}:\n{value.strip()}")
            # Add other type handling here if necessary

    return "\n\n".join(output)

def determine_task_and_instruction(
    current_mode: str, # Changed from is_details_tab_selected
    main_text: str,
    metadata: Dict[str, str | list[str]]
) -> Tuple[str, str]:
    """
    Determines the task type (GEN, CONT, IDEA) and corresponding instruction
    based on the UI state.

    Returns:
        Tuple[str, str]: (task_type, instruction_text)
    """
    has_main_text = bool(main_text.strip())

    # --- Determine Metadata Presence Explicitly ---
    has_title = bool(metadata.get("title", "").strip())
    has_keywords = bool(metadata.get("keywords", []))
    has_genres = bool(metadata.get("genres", []))
    has_synopsis = bool(metadata.get("synopsis", "").strip())
    has_setting = bool(metadata.get("setting", "").strip())
    has_plot = bool(metadata.get("plot", "").strip())
    # dialogue_level key only exists in metadata if it's not "指定なし"
    has_dialogue_level = "dialogue_level" in metadata

    # Combine checks based on mode
    # For generate/continue mode, any metadata counts
    has_any_metadata_for_gen_cont = (
        has_title or has_keywords or has_genres or has_synopsis or
        has_setting or has_plot or has_dialogue_level
    )
    # For idea mode, exclude dialogue_level
    has_any_metadata_for_idea = (
        has_title or has_keywords or has_genres or has_synopsis or
        has_setting or has_plot
    )

    # --- Determine Task Type ---
    task_type = "GEN_ZERO" # Default

    if current_mode == "generate":
        if not has_main_text:
            task_type = "GEN_INFO" if has_any_metadata_for_gen_cont else "GEN_ZERO"
        else: # has_main_text
            task_type = "CONT_INFO" if has_any_metadata_for_gen_cont else "CONT_ZERO"
    elif current_mode == "idea":
        task_type = "IDEA_INFO" if has_any_metadata_for_idea else "IDEA_ZERO"
    else:
        # Fallback or error handling for unknown mode
        print(f"Warning: Unknown mode '{current_mode}'. Defaulting to GEN_ZERO.")
        task_type = "GEN_ZERO"

    instruction_text = INSTRUCTION_TEMPLATES.get(task_type, "指示が見つかりません。") # Fallback
    return task_type, instruction_text


def build_prompt(
    current_mode: str,
    main_text: str,
    metadata: Dict[str, str | list[str]],
    cont_prompt_order: str = "reference_first", # Add setting for CONT order, default to reference first
    rating_override: Optional[str] = None # Add optional rating override from UI
) -> str:
    """
    Builds the final prompt string to be sent to KoboldCpp based on UI state and settings.

    Args:
        current_mode: The current operation mode ('generate' or 'idea').
        main_text: The main text input from the UI.
        metadata: The detailed information (title, keywords, etc.) from the UI.
        cont_prompt_order: The desired order for continuation prompts ('text_first' or 'reference_first').
        rating_override: The rating selected in the UI, if any. Overrides the default setting.
    """
    # --- Determine rating to use ---
    if rating_override:
        current_rating = rating_override
    else:
        # Load default rating from settings if no override is provided
        settings = load_settings()
        current_rating = settings.get("default_rating", DEFAULT_SETTINGS["default_rating"])

    # --- Determine base instruction ---
    task_type, instruction_text = determine_task_and_instruction(
        current_mode, main_text, metadata # Pass current_mode
    )

    # --- Append rating to instruction ---
    rating_suffix = f" レーティング: {current_rating}" # Note the leading space
    instruction_text += rating_suffix

    # Pass current_mode to format_metadata to handle exclusion logic
    metadata_input_string = format_metadata(metadata, mode=current_mode)
    internal_input = ""

    if task_type.startswith("GEN"):
        internal_input = metadata_input_string
    elif task_type.startswith("CONT"):
        # Prepare context for continuation based on the selected order
        main_text_block = f"【本文】\n```\n{main_text.strip()}\n```"
        reference_block = f"【参考情報】\n```\n{metadata_input_string}\n```" if metadata_input_string else ""

        if reference_block:
            if cont_prompt_order == "text_first":
                # Order: Text -> Reference
                context = f"{main_text_block}\n\n{reference_block}"
            else: # Default to reference_first (Reference -> Text)
                context = f"{reference_block}\n\n{main_text_block}"
        else:
            # If no reference info, just use the main text block
            context = main_text_block

        internal_input = context
    elif task_type.startswith("IDEA"):
        internal_input = metadata_input_string # Already formatted for IDEA task

    # --- Final Prompt Formatting (Mistral Instruct style) ---
    if internal_input:
        prompt = f"<s>[INST] {instruction_text}\n\n{internal_input} [/INST]"
    else:
        prompt = f"<s>[INST] {instruction_text} [/INST]" # No input section if empty

    return prompt

# --- Example Usage (Updated) ---
if __name__ == "__main__":
    # Scenario 1: Generate new story with metadata (cont_prompt_order doesn't apply)
    meta1 = {"title": "星降る夜の冒険", "keywords": ["ファンタジー", "魔法"], "synopsis": "見習い魔法使いのリナが、失われた星のかけらを探す旅に出る。"}
    prompt1 = build_prompt(current_mode="generate", main_text="", metadata=meta1)
    print("--- Scenario 1: GEN_INFO ---")
    print(prompt1)
    print("-" * 20)

    # Scenario 2: Continue story with no metadata (cont_prompt_order doesn't apply)
    text2 = "リナは杖を握りしめ、暗い森へと足を踏み入れた。"
    prompt2 = build_prompt(current_mode="generate", main_text=text2, metadata={})
    print("--- Scenario 2: CONT_ZERO ---")
    print(prompt2)
    print("-" * 20)

    # Scenario 3: Generate ideas with some metadata (cont_prompt_order doesn't apply)
    meta3 = {"genres": ["SF", "学園"], "setting": "近未来の日本。特殊能力を持つ生徒が集まる高校。"}
    prompt3 = build_prompt(current_mode="idea", main_text="", metadata=meta3)
    print("--- Scenario 3: IDEA_INFO ---")
    print(prompt3)
    print("-" * 20)

    # Scenario 4: Generate new story with no metadata (cont_prompt_order doesn't apply)
    prompt4 = build_prompt(current_mode="generate", main_text="", metadata={})
    print("--- Scenario 4: GEN_ZERO ---")
    print(prompt4)
    print("-" * 20)

    # Scenario 5: Continue story WITH metadata, order: text_first
    text5 = "古い地図を広げると、そこには見たこともない島が描かれていた。"
    meta5 = {"keywords": ["冒険", "宝探し"], "setting": "南海の孤島"}
    prompt5 = build_prompt(current_mode="generate", main_text=text5, metadata=meta5, cont_prompt_order="text_first")
    print("--- Scenario 5: CONT_INFO (text_first) ---")
    print(prompt5)
    print("-" * 20)

    # Scenario 6: Continue story WITH metadata, order: reference_first (Default)
    text6 = "古い地図を広げると、そこには見たこともない島が描かれていた。"
    meta6 = {"keywords": ["冒険", "宝探し"], "setting": "南海の孤島"}
    prompt6 = build_prompt(current_mode="generate", main_text=text6, metadata=meta6, cont_prompt_order="reference_first")
    print("--- Scenario 6: CONT_INFO (reference_first) ---")
    print(prompt6)
    print("-" * 20)
