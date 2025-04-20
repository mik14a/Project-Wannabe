import sys
import asyncio
import sys
import asyncio
import qasync # Import qasync
import re # Import regex module
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QStatusBar,
                               QSplitter, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QScrollArea, QLineEdit, QPushButton, QMessageBox,
                               QPlainTextEdit, QToolBar, QDialog) # Add QDialog
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor, QAction, QActionGroup

# Correctly import custom widgets and other modules
from src.ui.widgets import CollapsibleSection, TagWidget
from src.ui.dialogs import KoboldConfigDialog, GenerationParamsDialog
from src.core.kobold_client import KoboldClient, KoboldClientError
from src.core.prompt_builder import build_prompt
from src.core.settings import load_settings # To get initial settings if needed

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Wannabe (仮称)")
        self.setGeometry(100, 100, 1200, 800)

        self.kobold_client = KoboldClient()
        self.is_generating = False
        self.generation_task = None
        self.output_block_counter = 1
        self.current_mode = "generate" # Initial mode: "generate" or "idea"

        self._create_menu_bar()
        self._create_toolbar() # Add Toolbar creation
        self._create_status_bar()
        self._create_central_widget()

        # Cleanup connection will be handled by qasync loop setup

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        # --- File Menu ---
        file_menu = menu_bar.addMenu("ファイル(&F)") # Japanese
        placeholder_file = file_menu.addAction("(未実装)")
        placeholder_file.setEnabled(False)
        # Add actual actions later

        # --- Edit Menu ---
        edit_menu = menu_bar.addMenu("編集(&E)") # Japanese
        placeholder_edit = edit_menu.addAction("(未実装)")
        placeholder_edit.setEnabled(False)
        # Add actual actions later (or rely on QTextEdit defaults)

        # --- View Menu ---
        view_menu = menu_bar.addMenu("表示(&V)") # Japanese
        placeholder_view = view_menu.addAction("(未実装)")
        placeholder_view.setEnabled(False)
        # Add actual actions later

        # --- Generate Menu ---
        generate_menu = menu_bar.addMenu("生成(&G)") # Use Japanese & Mnemonic
        self.start_stop_action = generate_menu.addAction("生成 開始/停止 (F5)") # Japanese
        self.start_stop_action.setShortcut("F5")
        self.start_stop_action.triggered.connect(self._toggle_generation) # Connect action
        self.start_stop_action.setCheckable(True) # Make it checkable

        # --- Settings Menu ---
        settings_menu = menu_bar.addMenu("設定(&S)") # Japanese & Mnemonic
        kobold_config_action = settings_menu.addAction("KoboldCpp 設定...") # Japanese
        gen_params_action = settings_menu.addAction("生成パラメータ設定...") # Japanese
        kobold_config_action.triggered.connect(self._open_kobold_config_dialog) # Connect action
        gen_params_action.triggered.connect(self._open_gen_params_dialog)     # Connect action

        # --- Help Menu ---
        help_menu = menu_bar.addMenu("ヘルプ(&H)") # Japanese
        placeholder_help = help_menu.addAction("バージョン情報 (未実装)")
        placeholder_help.setEnabled(False)
        # Add actual actions later

    def _create_toolbar(self):
        """Creates the main toolbar for mode switching."""
        toolbar = QToolBar("モード選択")
        toolbar.setMovable(False) # Prevent moving/detaching
        self.addToolBar(toolbar)

        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        # Novel Generation Mode Action
        self.gen_mode_action = QAction("小説生成", self)
        self.gen_mode_action.setCheckable(True)
        self.gen_mode_action.setChecked(True) # Default mode
        self.gen_mode_action.triggered.connect(self._set_mode_generate)
        toolbar.addAction(self.gen_mode_action)
        mode_group.addAction(self.gen_mode_action)

        # Idea Generation Mode Action
        self.idea_mode_action = QAction("アイデア出し", self)
        self.idea_mode_action.setCheckable(True)
        self.idea_mode_action.triggered.connect(self._set_mode_idea)
        toolbar.addAction(self.idea_mode_action)
        mode_group.addAction(self.idea_mode_action)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_central_widget(self):
        # --- Central Splitter (Horizontal) ---
        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        # --- Left Area (Containers for TextEdits + Buttons) ---
        left_widget = QWidget()
        left_main_layout = QVBoxLayout(left_widget)
        left_main_layout.setContentsMargins(0,0,0,0)
        left_main_layout.setSpacing(0) # No space between splitter and buttons

        left_splitter = QSplitter(Qt.Vertical)
        left_main_layout.addWidget(left_splitter) # Splitter takes most space

        # --- Left Top: Main Text Area + Button ---
        main_text_container = QWidget()
        main_text_layout = QVBoxLayout(main_text_container)
        main_text_layout.setContentsMargins(0, 5, 0, 0) # Top margin for button
        main_text_layout.setSpacing(5)
        self.main_text_edit = QPlainTextEdit()
        self.main_text_edit.setPlaceholderText("ここに小説本文を入力・編集します...")
        main_text_layout.addWidget(self.main_text_edit)
        # Remove button from here
        # main_to_memo_button = QPushButton("[ 選択部分をメモへ転記 ]")
        # main_to_memo_button.clicked.connect(self._transfer_main_to_memo)
        # main_text_layout.addWidget(main_to_memo_button, 0, Qt.AlignRight)
        left_splitter.addWidget(main_text_container) # Add container to splitter

        # --- Left Bottom: Output Area + Buttons ---
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 5, 0, 0) # Top margin for buttons
        output_layout.setSpacing(5)
        self.output_text_edit = QPlainTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setPlaceholderText("LLMからの出力がここに表示されます...")
        output_layout.addWidget(self.output_text_edit)
        # Buttons below output area
        output_button_layout = QHBoxLayout()
        output_clear_button = QPushButton("[ 出力物クリア ]")
        output_to_main_button = QPushButton("[ 選択部分を本文へ転記 ]")
        output_to_memo_button = QPushButton("[ 選択部分をメモへ転記 ]") # Add button here
        output_clear_button.clicked.connect(self._clear_output_edit)
        output_to_main_button.clicked.connect(self._transfer_output_to_main)
        output_to_memo_button.clicked.connect(self._transfer_output_to_memo) # Connect new method
        output_button_layout.addWidget(output_clear_button)
        output_button_layout.addWidget(output_to_main_button)
        output_button_layout.addWidget(output_to_memo_button) # Add the new button
        output_button_layout.addStretch() # Push buttons left
        output_layout.addLayout(output_button_layout)
        left_splitter.addWidget(output_container) # Add container to splitter

        # --- Right Area (Tab Widget) ---
        self.right_tab_widget = QTabWidget() # Make it an instance variable
        self._create_details_tab() # Create Details Tab content
        self._create_memo_tab()    # Create Memo Tab content
        self.right_tab_widget.addTab(self.details_tab_widget, "詳細情報")
        self.right_tab_widget.addTab(self.memo_tab_widget, "メモ")

        # --- Add Left and Right to Central Splitter ---
        central_splitter.addWidget(left_widget) # Add left area first
        central_splitter.addWidget(self.right_tab_widget) # Use instance variable

        # --- Adjust initial sizes ---
        central_splitter.setSizes([700, 500]) # Initial width ratio for central splitter
        left_splitter.setSizes([600, 200]) # Initial height ratio for left splitter

    def _create_details_tab(self):
        self.details_tab_widget = QWidget()
        details_main_layout = QVBoxLayout(self.details_tab_widget)
        details_main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }") # Optional: remove border
        details_main_layout.addWidget(scroll_area)

        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)

        details_layout = QVBoxLayout(scroll_content_widget)
        details_layout.setSpacing(5) # Spacing between sections

        # --- Title Section ---
        title_section = CollapsibleSection("タイトル") # Use the imported class
        title_layout = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_transfer_button = QPushButton("← 転記")
        self.title_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("title"))
        title_layout.addWidget(self.title_edit)
        title_layout.addWidget(self.title_transfer_button)
        title_section.content_layout.addLayout(title_layout)
        details_layout.addWidget(title_section)

        # --- Keywords Section ---
        keywords_section = CollapsibleSection("キーワード") # Use the imported class
        self.keywords_widget = TagWidget() # Use the imported class
        self.keywords_widget.transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("keywords"))
        keywords_section.addWidget(self.keywords_widget)
        details_layout.addWidget(keywords_section)

        # --- Genre Section ---
        genre_section = CollapsibleSection("ジャンル") # Use the imported class
        self.genre_widget = TagWidget() # Use the imported class
        self.genre_widget.transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("genres"))
        genre_section.addWidget(self.genre_widget)
        details_layout.addWidget(genre_section)

        # --- Synopsis Section ---
        synopsis_section = CollapsibleSection("あらすじ") # Use the imported class
        synopsis_layout = QHBoxLayout()
        self.synopsis_edit = QPlainTextEdit()
        self.synopsis_edit.setPlaceholderText("小説のあらすじを入力...")
        self.synopsis_transfer_button = QPushButton("← 転記")
        self.synopsis_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("synopsis"))
        synopsis_layout.addWidget(self.synopsis_edit)
        synopsis_layout.addWidget(self.synopsis_transfer_button, 0, Qt.AlignTop)
        synopsis_section.content_layout.addLayout(synopsis_layout)
        details_layout.addWidget(synopsis_section)

        # --- Setting Section ---
        setting_section = CollapsibleSection("設定") # Use the imported class
        setting_layout = QHBoxLayout()
        self.setting_edit = QPlainTextEdit()
        self.setting_edit.setPlaceholderText("世界観、キャラクター設定などを入力...")
        self.setting_transfer_button = QPushButton("← 転記")
        self.setting_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("setting"))
        setting_layout.addWidget(self.setting_edit)
        setting_layout.addWidget(self.setting_transfer_button, 0, Qt.AlignTop)
        setting_section.content_layout.addLayout(setting_layout)
        details_layout.addWidget(setting_section)

        # --- Plot Section ---
        plot_section = CollapsibleSection("プロット") # Use the imported class
        plot_layout = QHBoxLayout()
        self.plot_edit = QPlainTextEdit()
        self.plot_edit.setPlaceholderText("物語の展開、構成などを入力...")
        self.plot_transfer_button = QPushButton("← 転記")
        self.plot_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("plot"))
        plot_layout.addWidget(self.plot_edit)
        plot_layout.addWidget(self.plot_transfer_button, 0, Qt.AlignTop)
        plot_section.content_layout.addLayout(plot_layout)
        details_layout.addWidget(plot_section)

        details_layout.addStretch() # Push sections to the top

    def _create_memo_tab(self):
        self.memo_tab_widget = QWidget()
        memo_layout = QVBoxLayout(self.memo_tab_widget)
        self.memo_edit = QPlainTextEdit()
        self.memo_edit.setPlaceholderText("自由にメモを記入できます...")
        memo_clear_button = QPushButton("メモクリア")
        memo_clear_button.clicked.connect(self._clear_memo_edit)

        memo_layout.addWidget(self.memo_edit)
        memo_layout.addWidget(memo_clear_button, 0, Qt.AlignRight)

    def _clear_memo_edit(self):
        """Clears the content of the memo text edit."""
        self.memo_edit.clear()

    def _open_kobold_config_dialog(self):
        """Opens the KoboldCpp configuration dialog."""
        # Check if dialog was accepted before reloading settings
        dialog = KoboldConfigDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_bar.showMessage("KoboldCpp 設定が更新されました。", 3000)
            self.kobold_client.reload_settings() # Reload only if accepted
        else:
            self.status_bar.showMessage("KoboldCpp 設定の変更はキャンセルされました。", 3000)

    def _open_gen_params_dialog(self):
        """Opens the generation parameters configuration dialog."""
        # Check if dialog was accepted before reloading settings
        dialog = GenerationParamsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_bar.showMessage("生成パラメータが更新されました。", 3000)
            self.kobold_client.reload_settings() # Reload only if accepted
        else:
            self.status_bar.showMessage("生成パラメータの変更はキャンセルされました。", 3000)


    @Slot()
    def _toggle_generation(self):
        """Starts or stops the text generation process."""
        if self.is_generating:
            self._stop_generation()
        else:
            self._start_generation()

    def _start_generation(self):
        """Starts the asynchronous generation task."""
        if self.is_generating:
            return

        self.is_generating = True
        self.start_stop_action.setChecked(True)
        self.status_bar.showMessage("生成中...")
        # Disable relevant UI elements if needed (e.g., settings menu)

        main_text = self.main_text_edit.toPlainText()
        metadata = self._get_metadata_from_ui()
        prompt = build_prompt(self.current_mode, main_text, metadata)

        separator = f"\n--- 生成ブロック {self.output_block_counter} ---\n"
        self._append_to_output(separator)

        self.generation_task = asyncio.ensure_future(self._run_generation(prompt))

    def _stop_generation(self):
        """Stops the currently running generation task."""
        if not self.is_generating or self.generation_task is None:
            return

        self.is_generating = False
        self.start_stop_action.setChecked(False)
        self.status_bar.showMessage("生成停止中...", 2000)

        if self.generation_task and not self.generation_task.done():
            self.generation_task.cancel()

        self.generation_task = None
        self.status_bar.showMessage("停止中", 3000)
        # Re-enable UI elements if they were disabled

    async def _run_generation(self, prompt: str):
        """The async function that calls the client and updates UI directly (using qasync)."""
        try:
            async for token in self.kobold_client.generate_stream(prompt):
                self._append_to_output(token)
                await asyncio.sleep(0.001)

            if self.is_generating:
                self.is_generating = False
                self.start_stop_action.setChecked(False)
                self.status_bar.showMessage("生成完了", 3000)
                self.output_block_counter += 1

        except KoboldClientError as e:
            error_msg = f"\n--- エラー: {e} ---\n"
            self._append_to_output(error_msg)
            if self.is_generating:
                self.is_generating = False
                self.start_stop_action.setChecked(False)
                self.status_bar.showMessage("生成エラー", 3000)
        except asyncio.CancelledError:
            print("Generation task cancelled.")
            self._append_to_output("\n--- 生成がキャンセルされました ---\n")
        except Exception as e:
             error_msg = f"\n--- 予期せぬエラーが発生しました: {e} ---\n"
             print(error_msg)
             self._append_to_output(error_msg)
             if self.is_generating:
                self.is_generating = False
                self.start_stop_action.setChecked(False)
                self.status_bar.showMessage("予期せぬエラー", 3000)
        finally:
             if self.is_generating: # Ensure state is reset if error occurred mid-stream
                 self.is_generating = False
                 self.start_stop_action.setChecked(False)
                 self.status_bar.showMessage("停止中 (エラー発生)", 3000)


    def _append_to_output(self, text: str):
        """Safely appends text to the output area and handles scrolling."""
        cursor = self.output_text_edit.textCursor()
        v_bar = self.output_text_edit.verticalScrollBar()
        is_at_bottom = v_bar.value() >= v_bar.maximum() - 5 # Check if near bottom

        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)

        if is_at_bottom:
            v_bar.setValue(v_bar.maximum()) # Scroll to bottom

    def _get_metadata_from_ui(self) -> dict:
        """Retrieves metadata values from the UI widgets."""
        return {
            "title": self.title_edit.text(),
            "keywords": self.keywords_widget.get_tags(),
            "genres": self.genre_widget.get_tags(),
            "synopsis": self.synopsis_edit.toPlainText(),
            "setting": self.setting_edit.toPlainText(),
            "plot": self.plot_edit.toPlainText(),
        }

    async def _cleanup(self): # Make cleanup async
        """Closes the Kobold client when the application is about to quit."""
        print("Cleaning up...")
        if self.is_generating:
            self._stop_generation() # Attempt to stop gracefully
        print("Requesting Kobold client close...")
        try:
            await self.kobold_client.close() # Await the async close
            print("Kobold client closed.")
        except Exception as e:
            print(f"Error during client close: {e}")

    @Slot()
    def _clear_output_edit(self):
        """Clears the output text edit and resets the block counter."""
        self.output_text_edit.clear()
        self.output_block_counter = 1
        self.status_bar.showMessage("出力エリアをクリアしました。", 2000)

    @Slot()
    def _transfer_output_to_main(self):
        """Transfers selected text from output area to main text area."""
        selected_text = self.output_text_edit.textCursor().selectedText()
        if selected_text:
            self.main_text_edit.textCursor().insertText(selected_text)
            self.status_bar.showMessage("選択範囲を本文エリアに転記しました。", 2000)
        else:
            self.status_bar.showMessage("出力エリアでテキストが選択されていません。", 2000)

    @Slot()
    def _transfer_main_to_memo(self):
        """Transfers selected text from main text area to memo area."""
        selected_text = self.main_text_edit.textCursor().selectedText()
        if selected_text:
            self.memo_edit.appendPlainText(selected_text) # Append to memo
            self.status_bar.showMessage("選択範囲をメモエリアに転記しました。", 2000)
        else:
            self.status_bar.showMessage("本文エリアでテキストが選択されていません。", 2000)

    @Slot()
    def _transfer_output_to_memo(self): # Renamed from _transfer_main_to_memo
        """Transfers selected text from output area to memo area."""
        selected_text = self.output_text_edit.textCursor().selectedText() # Source is output_text_edit
        if selected_text:
            self.memo_edit.appendPlainText(selected_text) # Append to memo
            self.status_bar.showMessage("選択範囲をメモエリアに転記しました。", 2000)
        else:
            self.status_bar.showMessage("出力エリアでテキストが選択されていません。", 2000) # Message updated

    @Slot()
    def _transfer_idea_to_details(self, metadata_key: str):
        """
        Parses selected text in the output area and transfers the value
        corresponding to the metadata_key to the appropriate details widget.
        """
        selected_text = self.output_text_edit.textCursor().selectedText()
        if not selected_text:
            self.status_bar.showMessage("出力エリアで転記したいテキストを選択してください。", 3000)
            return

        japanese_name_map = {
            "title": "タイトル", "keywords": "キーワード", "genres": "ジャンル",
            "synopsis": "あらすじ", "setting": "設定", "plot": "プロット",
        }
        target_name = japanese_name_map.get(metadata_key)
        if not target_name:
            print(f"Error: Unknown metadata key '{metadata_key}' for transfer.")
            return

        pattern = re.compile(rf"^# {re.escape(target_name)}:\s*(.*?)(?=(?:^# |\Z))", re.MULTILINE | re.DOTALL)
        match = pattern.search(selected_text)

        if not match:
            self.status_bar.showMessage(f"選択範囲から「{target_name}」セクションが見つかりませんでした。", 3000)
            return

        extracted_value = match.group(1).strip()

        try:
            if metadata_key == "title":
                self.title_edit.setText(extracted_value)
            elif metadata_key == "keywords":
                tags = [line.strip().lstrip('-').strip() for line in extracted_value.splitlines() if line.strip()]
                self.keywords_widget.set_tags(tags)
            elif metadata_key == "genres":
                tags = [line.strip().lstrip('-').strip() for line in extracted_value.splitlines() if line.strip()]
                self.genre_widget.set_tags(tags)
            elif metadata_key == "synopsis":
                self.synopsis_edit.setPlainText(extracted_value)
            elif metadata_key == "setting":
                self.setting_edit.setPlainText(extracted_value)
            elif metadata_key == "plot":
                self.plot_edit.setPlainText(extracted_value)
            else:
                 print(f"Error: No widget defined for key '{metadata_key}'.")
                 return

            self.status_bar.showMessage(f"「{target_name}」を詳細情報に転記しました。", 2000)

        except Exception as e:
            print(f"Error transferring data for '{metadata_key}': {e}")
            self.status_bar.showMessage(f"「{target_name}」の転記中にエラーが発生しました。", 3000)


    @Slot()
    def _set_mode_generate(self):
        """Sets the application mode to 'generate'."""
        self.current_mode = "generate"
        self.status_bar.showMessage("モード: 小説生成", 2000)

    @Slot()
    def _set_mode_idea(self):
        """Sets the application mode to 'idea'."""
        self.current_mode = "idea"
        self.status_bar.showMessage("モード: アイデア出し", 2000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    # Make _cleanup an async function and connect it properly
    async def async_cleanup():
        await window._cleanup()
    app.aboutToQuit.connect(lambda: asyncio.ensure_future(async_cleanup()))
    window.show()

    with loop:
        loop.run_forever()
