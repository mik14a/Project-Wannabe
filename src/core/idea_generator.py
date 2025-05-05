# src/core/idea_generator.py
from typing import Dict, Optional, List, Tuple, Literal
import re

# メタデータの順序と日本語名の定義 (prompt_builder.py と共有または一元管理を検討)
# Note: prompt_builder.py からも参照される可能性があるため、
#       将来的には settings.py などで一元管理するのが望ましい。
METADATA_ORDER = ["title", "keywords", "genres", "synopsis", "setting", "plot"]
METADATA_MAP_JA = {
    "title": "タイトル", "keywords": "キーワード", "genres": "ジャンル",
    "synopsis": "あらすじ", "setting": "設定", "plot": "プロット",
}
# 逆引きマップも用意
KEY_MAP_FROM_JA = {v: k for k, v in METADATA_MAP_JA.items()}

GenerationMethod = Literal["safe", "fast"]

class IdeaGenerator:
    """IDEAタスクのロジックを管理するクラス"""

    def __init__(self,
                 selected_item_key: str, # "all", "title", "keywords", etc.
                 generation_method: GenerationMethod,
                 current_metadata: Dict[str, str | List[str]]):
        """
        Args:
            selected_item_key: UIで選択された生成対象項目のキー ("all", "title", etc.)
            generation_method: UIで選択された生成手法 ("safe" or "fast")
            current_metadata: UIから取得した現在のメタデータ辞書
        """
        self.selected_item_key = selected_item_key
        self.generation_method = generation_method
        # Ensure metadata values are appropriate types (e.g., lists for tags)
        self.current_metadata = self._normalize_metadata(current_metadata)


    def _normalize_metadata(self, metadata: Dict) -> Dict[str, str | List[str]]:
        """Ensure metadata values have expected types, especially lists for tags."""
        normalized = {}
        for key in METADATA_ORDER:
            value = metadata.get(key)
            if key in ["keywords", "genres"]:
                if isinstance(value, list):
                    normalized[key] = [str(tag).strip() for tag in value if str(tag).strip()]
                elif isinstance(value, str): # Handle case where tags might be a single string initially
                    normalized[key] = [tag.strip() for tag in value.split() if tag.strip()]
                else:
                    normalized[key] = []
            elif isinstance(value, str):
                normalized[key] = value.strip()
            else:
                 normalized[key] = "" # Default to empty string if missing or wrong type
        return normalized

    def _get_next_item_header(self) -> Optional[str]:
        """選択された項目の次の項目のヘッダー文字列 (# 日本語名:\n) を返す"""
        if self.selected_item_key == "all" or self.selected_item_key not in METADATA_ORDER:
            return None # 全選択または不正キー

        try:
            current_index = METADATA_ORDER.index(self.selected_item_key)
            if current_index >= len(METADATA_ORDER) - 1:
                return None # 最後の項目なら次はない

            next_item_key = METADATA_ORDER[current_index + 1]
            next_item_ja = METADATA_MAP_JA.get(next_item_key)
            # KoboldCppのStop Sequenceは改行を含む必要がある場合が多い
            return f"# {next_item_ja}:\n" if next_item_ja else None
        except (ValueError, IndexError):
            print(f"Error finding next item header for: {self.selected_item_key}")
            return None

    def _build_fast_suffix(self) -> Optional[str]:
        """高速手法用のプロンプト接尾辞（先行項目の内容）を構築"""
        if self.selected_item_key == "all" or self.selected_item_key not in METADATA_ORDER:
            return None # 全選択時や不正キーは接尾辞不要

        suffix_parts = []
        try:
            target_index = METADATA_ORDER.index(self.selected_item_key)
            if target_index == 0: # 最初の項目は先行項目がない
                return "" # 空文字列を返す

            for i in range(target_index):
                key = METADATA_ORDER[i]
                value = self.current_metadata.get(key) # Use normalized metadata
                ja_name = METADATA_MAP_JA.get(key)
                if value and ja_name:
                    if key in ["keywords", "genres"] and isinstance(value, list):
                        # Use normalized tags
                        formatted_tags = "\n".join(item for item in value) # No `- ` prefix
                        if formatted_tags:
                             suffix_parts.append(f"# {ja_name}:\n{formatted_tags}")
                    elif isinstance(value, str) and value: # Check if string is not empty
                        suffix_parts.append(f"# {ja_name}:\n{value}") # Use normalized value

            # 結合して返す (項目間は空行2つ、末尾にも空行2つ追加してAIに次のヘッダー生成を促す)
            return "\n\n".join(suffix_parts) + "\n\n" if suffix_parts else ""
        except ValueError:
            print(f"Error building fast suffix for: {self.selected_item_key}")
            return None # エラー時はNone

    def check_fast_method_prerequisites(self) -> bool:
        """高速手法の前提条件（特定項目選択 + 先行項目入力）をチェック"""
        if self.selected_item_key == "all" or self.selected_item_key not in METADATA_ORDER:
            return False # 全選択や不正キーは前提外
        try:
            target_index = METADATA_ORDER.index(self.selected_item_key)
            if target_index == 0: # 最初の項目(title)は先行項目がないので不可
                return False
            # 最初の項目から選択された項目の *直前* までに、一つでも入力があるかチェック
            for i in range(target_index):
                key = METADATA_ORDER[i]
                value = self.current_metadata.get(key) # Use normalized metadata
                if value: # Check if list/string is not empty
                    return True
            return False # 先行項目が全て空
        except ValueError:
            return False # 不正な項目キー

    def prepare_generation(self) -> Dict:
        """
        IDEAタスクの生成準備を行い、必要なパラメータを返す。
        Returns:
            dict: {
                "stop_sequence": Optional[List[str]],
                "prompt_suffix": Optional[str],
                "requires_filtering": bool,
                "use_streaming": bool,
                "prerequisites_met": Optional[bool] # None if not applicable
            }
        """
        stop_header = self._get_next_item_header()
        # Koboldはリスト形式。Noneでない場合のみリストに入れる
        stop_sequence = [stop_header] if stop_header else []

        prompt_suffix = None
        requires_filtering = False
        use_streaming = True
        prerequisites_met = None # Applicable only for fast method

        if self.generation_method == "safe":
            use_streaming = False
            if self.selected_item_key != "all":
                requires_filtering = True
            # Stop Sequence は次のヘッダー (stop_sequence はそのまま)
        elif self.generation_method == "fast":
            prerequisites_met = self.check_fast_method_prerequisites()
            if prerequisites_met:
                prompt_suffix = self._build_fast_suffix()
                # Stop Sequence は次のヘッダー (stop_sequence はそのまま)
            # else: prerequisites_met is False, main.py handles warning

        return {
            "stop_sequence": stop_sequence,
            "prompt_suffix": prompt_suffix,
            "requires_filtering": requires_filtering,
            "use_streaming": use_streaming,
            "prerequisites_met": prerequisites_met
        }

    def filter_output(self, full_output: str) -> str:
        """安全な手法で生成された全出力から、選択された項目の内容を抽出"""
        if self.selected_item_key == "all" or self.selected_item_key not in METADATA_MAP_JA:
            return full_output.strip() # 全選択または不正キーなら全体を返す

        target_ja_name = METADATA_MAP_JA[self.selected_item_key]

        # 抽出ロジック:
        # 1. ターゲットヘッダーを探す
        # 2. 次のヘッダーを探す (または文字列終端)
        # 3. その間の内容を抽出

        # 正規表現でターゲットヘッダーとそれに続く内容を取得
        # (?s) は DOTALL フラグ、.*? は非貪欲マッチ
        # (?:^\s*#|\\Z) は次のヘッダーまたは文字列終端（非キャプチャグループ）
        pattern_str = rf"^\s*#\s*{re.escape(target_ja_name)}\s*:\s*\n(.*?)(?=\s*^\s*#|\Z)"
        match = re.search(pattern_str, full_output, re.MULTILINE | re.DOTALL | re.IGNORECASE)

        if match:
            extracted_content = match.group(1).strip()
            # 元のヘッダーを付けて返す
            return f"# {target_ja_name}:\n{extracted_content}"
        else:
            # マッチしない場合、空文字列を返すか、エラーを示すか
            print(f"Warning: Could not extract '{target_ja_name}' section from output.")
            return "" # 空文字列を返す
