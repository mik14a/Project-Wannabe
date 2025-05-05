from typing import Dict, List, Optional, Tuple, Literal

# 定数を定義 (prompt_builder.py との重複を避けるため、ここで定義)
METADATA_MAP = {
    "title": "タイトル", "keywords": "キーワード", "genres": "ジャンル",
    "synopsis": "あらすじ", "setting": "設定", "plot": "プロット",
}
# IDEAモードで考慮する項目の順序
IDEA_ITEM_ORDER = ["title", "keywords", "genres", "synopsis", "setting", "plot"]
IDEA_ITEM_ORDER_JA = [METADATA_MAP[key] for key in IDEA_ITEM_ORDER]

class IdeaProcessor:
    """
    Handles IDEA task specific logic: prerequisite checks, stop sequence determination,
    prompt suffix generation (fast mode), and output filtering (safe mode).
    """

    def __init__(self, ui_inputs: Dict[str, str | List[str]]):
        """
        Args:
            ui_inputs: Dictionary containing current values from UI detail fields
                       (e.g., {'title': '...', 'keywords': ['tag1'], ...}).
        """
        self.ui_inputs = ui_inputs

    def check_fast_mode_prerequisites(self, selected_item_key: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if prerequisites for fast mode are met for the selected item.

        Args:
            selected_item_key: The internal key of the selected item (e.g., 'synopsis').

        Returns:
            Tuple[bool, Optional[str]]: (prerequisites_met, warning_message)
            warning_message is None if prerequisites are met.
        """
        if selected_item_key not in IDEA_ITEM_ORDER:
            # This case should ideally be prevented by UI validation, but handle defensively.
            return False, f"無効な項目が選択されました: {selected_item_key}"

        selected_index = IDEA_ITEM_ORDER.index(selected_item_key)
        if selected_index == 0: # First item (title) cannot use fast mode based on prior items
             # This case should also be prevented by UI logic disabling the checkbox.
             return False, "最初の項目「タイトル」では高速な手法は使用できません。"

        # Check if all preceding items have input
        missing_items = []
        for i in range(selected_index):
            preceding_key = IDEA_ITEM_ORDER[i]
            preceding_value = self.ui_inputs.get(preceding_key)
            # Check if value is missing, empty string, or empty list
            if not preceding_value or (isinstance(preceding_value, str) and not preceding_value.strip()) or \
               (isinstance(preceding_value, list) and not preceding_value):
                preceding_name_ja = METADATA_MAP.get(preceding_key, preceding_key)
                missing_items.append(preceding_name_ja)

        if missing_items:
            warning_msg = f"高速な手法の前提条件を満たしていません。\n以下の先行項目を入力してください:\n- {', '.join(missing_items)}\n\n警告: このまま続行しますが、期待通りの結果にならない可能性があります。"
            # Prerequisites are NOT met, but we return True to allow continuation with warning.
            # The caller (main.py) should check the warning message.
            return False, warning_msg # Return False for met status, but provide warning
        else:
            return True, None # Prerequisites met, no warning

    def determine_stop_sequence(self, selected_item_key: str) -> Optional[List[str]]:
        """
        Determines the stop sequence (header of the next item) based on the selected item.
        Returns None if '全部' or the last item is selected.

        Args:
            selected_item_key: The internal key of the selected item, or 'all'.
        """
        if selected_item_key == 'all' or selected_item_key not in IDEA_ITEM_ORDER:
            return None # No specific stop sequence needed for 'all' or invalid key

        try:
            current_index = IDEA_ITEM_ORDER.index(selected_item_key)
            if current_index == len(IDEA_ITEM_ORDER) - 1:
                return None # Last item selected, no next header to stop at
            else:
                next_item_key = IDEA_ITEM_ORDER[current_index + 1]
                # Stop sequence should match the exact format AI might generate
                next_item_header = f"\n# {METADATA_MAP[next_item_key]}:"
                return [next_item_header]
        except ValueError:
             print(f"Warning: Invalid key '{selected_item_key}' encountered in determine_stop_sequence.")
             return None

    def generate_prompt_suffix(self, selected_item_key: str) -> str:
        """
        Generates the prompt suffix for fast mode, containing formatted preceding items.
        Should only be called if prerequisites are met (or warning is accepted).

        Args:
            selected_item_key: The internal key of the selected item to generate.
        """
        suffix_parts = []
        # selected_item_key が IDEA_ITEM_ORDER に存在するか確認
        if selected_item_key not in IDEA_ITEM_ORDER:
             print(f"Warning: Invalid key '{selected_item_key}' passed to generate_prompt_suffix.")
             return ""

        selected_index = IDEA_ITEM_ORDER.index(selected_item_key)

        for i in range(selected_index):
            key = IDEA_ITEM_ORDER[i]
            value = self.ui_inputs.get(key)
            japanese_name = METADATA_MAP[key]

            if value:
                formatted_value = ""
                if isinstance(value, list): # Keywords, Genres
                    # AI出力風フォーマット: 各タグを改行で区切る
                    # Filter out empty strings that might be in the list
                    valid_tags = [item.strip() for item in value if item.strip()]
                    if valid_tags:
                        formatted_value = "\n".join(valid_tags)
                elif isinstance(value, str): # Title, Synopsis, Setting, Plot
                    formatted_value = value.strip()

                if formatted_value: # Add section only if value exists after formatting
                    suffix_parts.append(f"# {japanese_name}:\n{formatted_value}")

        # Join parts with double newline, mimicking AI output structure
        # Ensure trailing newlines before AI starts generating the selected item's header
        if suffix_parts:
            return "\n\n".join(suffix_parts) + "\n\n"
        else:
            # If no preceding items had content, return empty string.
            # The AI will start generating from the beginning of the selected item's header.
            return ""

    def filter_output(self, full_output: str, selected_item_key: str) -> str:
        """
        Filters the full AI output (safe mode or potentially incomplete fast mode)
        to extract only the selected item's content.

        Args:
            full_output: The complete text generated by the AI.
            selected_item_key: The internal key of the item to extract.
        """
        if selected_item_key == 'all' or selected_item_key not in IDEA_ITEM_ORDER:
            return full_output # Return everything if 'all' or invalid key

        selected_name_ja = METADATA_MAP[selected_item_key]
        start_header = f"# {selected_name_ja}:"
        # Find the header, allowing for potential leading newline added by AI
        start_index = full_output.find(start_header)
        if start_index == -1:
             # Try finding without leading newline just in case
             start_header_no_nl = f"# {selected_name_ja}:"
             start_index = full_output.find(start_header_no_nl)
             if start_index == -1:
                  print(f"Filter Warning: Header '{start_header}' not found in output.")
                  return "" # Selected header not found at all

        # Determine where the content actually starts (after the header and potential newline)
        content_start_index = start_index + len(start_header)
        if content_start_index < len(full_output) and full_output[content_start_index] == '\n':
            content_start_index += 1

        # Find the start of the *next* header to determine the end of the current section
        end_index = len(full_output) # Default to end of string
        current_item_order_index = IDEA_ITEM_ORDER.index(selected_item_key)

        for i in range(current_item_order_index + 1, len(IDEA_ITEM_ORDER)):
            next_key = IDEA_ITEM_ORDER[i]
            next_name_ja = METADATA_MAP[next_key]
            # Look for the next header after the start of the current content
            # Check with and without leading newline for robustness
            next_header_nl = f"\n# {next_name_ja}:"
            next_header_no_nl = f"# {next_name_ja}:"

            # Search starting from content_start_index
            found_next_header_index_nl = full_output.find(next_header_nl, content_start_index)
            found_next_header_index_no_nl = full_output.find(next_header_no_nl, content_start_index)

            # Find the earliest occurrence of the next header
            found_next_header_index = -1
            indices = [idx for idx in [found_next_header_index_nl, found_next_header_index_no_nl] if idx != -1]
            if indices:
                found_next_header_index = min(indices)

            if found_next_header_index != -1:
                end_index = found_next_header_index
                break # Stop at the first subsequent header found

        # Extract the content including the header itself
        extracted_content = full_output[start_index:end_index].strip()
        return extracted_content
