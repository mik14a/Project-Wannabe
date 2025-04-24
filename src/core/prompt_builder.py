from typing import Dict, Optional, Tuple

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
}

def format_metadata(metadata: Dict[str, str | list[str]]) -> str:
    """Formats the metadata dictionary into a string for the prompt."""
    output = []
    for key, japanese_name in METADATA_MAP.items():
        value = metadata.get(key) # データセット側のキーで値を取得
        if value:
            if key in ["keywords", "genres"] and isinstance(value, list): # UI側のキー名で判定 (METADATA_MAPのキー)
                if value: # Only add if list is not empty
                    # `- ` を付けずに改行で結合 (データセット側に合わせる)
                    output.append(f"# {japanese_name}:\n" + "\n".join(item for item in value))
            elif isinstance(value, str) and value.strip(): # Handle text fields
                 output.append(f"# {japanese_name}:\n{value.strip()}")
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
    # Check if any metadata value is non-empty (list or string)
    has_metadata = any(
        (isinstance(v, list) and v) or (isinstance(v, str) and v.strip())
        for v in metadata.values()
    )

    if current_mode == "generate": # Check mode directly
        if not has_main_text:
            if has_metadata:
                task_type = "GEN_INFO" # Generate new story with info
            else:
                task_type = "GEN_ZERO" # Generate new story without info
        else: # has_main_text
            if has_metadata:
                task_type = "CONT_INFO" # Continue story with info
            else:
                task_type = "CONT_ZERO" # Continue story without info
    elif current_mode == "idea": # Check idea mode
        if has_metadata:
            task_type = "IDEA_INFO" # Generate ideas with info
        else:
            task_type = "IDEA_ZERO" # Generate ideas without info
    else:
        # Fallback or error handling for unknown mode
        print(f"Warning: Unknown mode '{current_mode}'. Defaulting to GEN_ZERO.")
        task_type = "GEN_ZERO"

    instruction_text = INSTRUCTION_TEMPLATES.get(task_type, "指示が見つかりません。") # Fallback
    return task_type, instruction_text


def build_prompt(
    current_mode: str, # Changed from is_details_tab_selected
    main_text: str,
    metadata: Dict[str, str | list[str]]
) -> str:
    """
    Builds the final prompt string to be sent to KoboldCpp based on UI state.
    """
    task_type, instruction_text = determine_task_and_instruction(
        current_mode, main_text, metadata # Pass current_mode
    )

    metadata_input_string = format_metadata(metadata)
    internal_input = ""

    if task_type.startswith("GEN"):
        internal_input = metadata_input_string
    elif task_type.startswith("CONT"):
        # Prepare context for continuation
        # Consider limiting main_text length if it's very long
        context = f"【本文】\n```\n{main_text.strip()}\n```"
        if metadata_input_string:
            context += f"\n\n【参考情報】\n```\n{metadata_input_string}\n```"
        internal_input = context
    elif task_type.startswith("IDEA"):
        internal_input = metadata_input_string # Already formatted

    # --- Final Prompt Formatting (Mistral Instruct style) ---
    if internal_input:
        prompt = f"<s>[INST] {instruction_text}\n\n{internal_input} [/INST]"
    else:
        prompt = f"<s>[INST] {instruction_text} [/INST]" # No input section if empty

    return prompt

# --- Example Usage ---
if __name__ == "__main__":
    # Scenario 1: Generate new story with metadata
    meta1 = {"title": "星降る夜の冒険", "keywords": ["ファンタジー", "魔法"], "synopsis": "見習い魔法使いのリナが、失われた星のかけらを探す旅に出る。"}
    prompt1 = build_prompt(current_mode="generate", main_text="", metadata=meta1)
    print("--- Scenario 1: GEN_INFO ---")
    print(prompt1)
    print("-" * 20)

    # Scenario 2: Continue story with no metadata
    text2 = "リナは杖を握りしめ、暗い森へと足を踏み入れた。"
    prompt2 = build_prompt(current_mode="generate", main_text=text2, metadata={})
    print("--- Scenario 2: CONT_ZERO ---")
    print(prompt2)
    print("-" * 20)

    # Scenario 3: Generate ideas with some metadata
    meta3 = {"genres": ["SF", "学園"], "setting": "近未来の日本。特殊能力を持つ生徒が集まる高校。"}
    prompt3 = build_prompt(current_mode="idea", main_text="", metadata=meta3)
    print("--- Scenario 3: IDEA_INFO ---")
    print(prompt3)
    print("-" * 20)

    # Scenario 4: Generate new story with no metadata
    prompt4 = build_prompt(current_mode="generate", main_text="", metadata={})
    print("--- Scenario 4: GEN_ZERO ---")
    print(prompt4)
    print("-" * 20)
