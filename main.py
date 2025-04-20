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
        # Generation status: "idle", "single_running", "infinite_running"
        self.generation_status = "idle"
        self.generation_task = None # Holds the asyncio task for generation
        self.output_block_counter = 1
        self.current_mode = "generate" # Initial mode: "generate" or "idea"
        self.infinite_generation_prompt = "" # Store prompt for infinite loop

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

        # --- Edit Menu ---
        edit_menu = menu_bar.addMenu("編集(&E)") # Japanese
        placeholder_edit = edit_menu.addAction("(未実装)")
        placeholder_edit.setEnabled(False)

        # --- View Menu ---
        view_menu = menu_bar.addMenu("表示(&V)") # Japanese
        placeholder_view = view_menu.addAction("(未実装)")
        placeholder_view.setEnabled(False)

        # --- Generate Menu ---
        generate_menu = menu_bar.addMenu("生成(&G)") # Use Japanese & Mnemonic

        # Single Generation Action
        self.single_gen_action = generate_menu.addAction("単発生成 (Ctrl+G)")
        self.single_gen_action.setShortcut("Ctrl+G")
        self.single_gen_action.triggered.connect(self._trigger_single_generation)

        # Infinite Generation Action
        self.infinite_gen_action = generate_menu.addAction("無限生成 開始/停止 (F5)")
        self.infinite_gen_action.setShortcut("F5")
        self.infinite_gen_action.setCheckable(True)
        self.infinite_gen_action.triggered.connect(self._toggle_infinite_generation)

        # --- Settings Menu ---
        settings_menu = menu_bar.addMenu("設定(&S)") # Japanese & Mnemonic
        kobold_config_action = settings_menu.addAction("KoboldCpp 設定...") # Japanese
        gen_params_action = settings_menu.addAction("生成パラメータ設定...") # Japanese
        kobold_config_action.triggered.connect(self._open_kobold_config_dialog)
        gen_params_action.triggered.connect(self._open_gen_params_dialog)

        # --- Help Menu ---
        help_menu = menu_bar.addMenu("ヘルプ(&H)") # Japanese
        placeholder_help = help_menu.addAction("バージョン情報 (未実装)")
        placeholder_help.setEnabled(False)

    def _create_toolbar(self):
        """Creates the main toolbar for mode switching."""
        toolbar = QToolBar("モード選択")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        self.gen_mode_action = QAction("小説生成", self)
        self.gen_mode_action.setCheckable(True)
        self.gen_mode_action.setChecked(True)
        self.gen_mode_action.triggered.connect(self._set_mode_generate)
        toolbar.addAction(self.gen_mode_action)
        mode_group.addAction(self.gen_mode_action)

        self.idea_mode_action = QAction("アイデア出し", self)
        self.idea_mode_action.setCheckable(True)
        self.idea_mode_action.triggered.connect(self._set_mode_idea)
        toolbar.addAction(self.idea_mode_action)
        mode_group.addAction(self.idea_mode_action)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了") # Changed to Japanese

    def _create_central_widget(self):
        central_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(central_splitter)

        left_widget = QWidget()
        left_main_layout = QVBoxLayout(left_widget)
        left_main_layout.setContentsMargins(0,0,0,0)
        left_main_layout.setSpacing(0)
        left_splitter = QSplitter(Qt.Vertical)
        left_main_layout.addWidget(left_splitter)

        main_text_container = QWidget()
        main_text_layout = QVBoxLayout(main_text_container)
        main_text_layout.setContentsMargins(0, 5, 0, 0)
        main_text_layout.setSpacing(5)
        self.main_text_edit = QPlainTextEdit()
        self.main_text_edit.setPlaceholderText("ここに小説本文を入力・編集します...")
        main_text_layout.addWidget(self.main_text_edit)
        left_splitter.addWidget(main_text_container)

        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 5, 0, 0)
        output_layout.setSpacing(5)
        self.output_text_edit = QPlainTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setPlaceholderText("LLMからの出力がここに表示されます...")
        output_layout.addWidget(self.output_text_edit)
        output_button_layout = QHBoxLayout()
        output_clear_button = QPushButton("[ 出力物クリア ]")
        output_to_main_button = QPushButton("[ 選択部分を本文へ転記 ]")
        output_to_memo_button = QPushButton("[ 選択部分をメモへ転記 ]")
        output_clear_button.clicked.connect(self._clear_output_edit)
        output_to_main_button.clicked.connect(self._transfer_output_to_main)
        output_to_memo_button.clicked.connect(self._transfer_output_to_memo)
        output_button_layout.addWidget(output_clear_button)
        output_button_layout.addWidget(output_to_main_button)
        output_button_layout.addWidget(output_to_memo_button)
        output_button_layout.addStretch()
        output_layout.addLayout(output_button_layout)
        left_splitter.addWidget(output_container)

        self.right_tab_widget = QTabWidget()
        self._create_details_tab()
        self._create_memo_tab()
        self.right_tab_widget.addTab(self.details_tab_widget, "詳細情報")
        self.right_tab_widget.addTab(self.memo_tab_widget, "メモ")

        central_splitter.addWidget(left_widget)
        central_splitter.addWidget(self.right_tab_widget)
        central_splitter.setSizes([700, 500])
        left_splitter.setSizes([600, 200])

    def _create_details_tab(self):
        self.details_tab_widget = QWidget()
        details_main_layout = QVBoxLayout(self.details_tab_widget)
        details_main_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        details_main_layout.addWidget(scroll_area)
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)
        details_layout = QVBoxLayout(scroll_content_widget)
        details_layout.setSpacing(5)

        # Title
        title_section = CollapsibleSection("タイトル")
        title_layout = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_transfer_button = QPushButton("← 転記")
        self.title_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("title"))
        title_layout.addWidget(self.title_edit)
        title_layout.addWidget(self.title_transfer_button)
        title_section.content_layout.addLayout(title_layout)
        details_layout.addWidget(title_section)

        # Keywords
        keywords_section = CollapsibleSection("キーワード")
        self.keywords_widget = TagWidget()
        self.keywords_widget.transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("keywords"))
        keywords_section.addWidget(self.keywords_widget)
        details_layout.addWidget(keywords_section)

        # Genre
        genre_section = CollapsibleSection("ジャンル")
        self.genre_widget = TagWidget()
        self.genre_widget.transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("genres"))
        genre_section.addWidget(self.genre_widget)
        details_layout.addWidget(genre_section)

        # Synopsis
        synopsis_section = CollapsibleSection("あらすじ")
        synopsis_layout = QHBoxLayout()
        self.synopsis_edit = QPlainTextEdit()
        self.synopsis_edit.setPlaceholderText("小説のあらすじを入力...")
        self.synopsis_transfer_button = QPushButton("← 転記")
        self.synopsis_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("synopsis"))
        synopsis_layout.addWidget(self.synopsis_edit)
        synopsis_layout.addWidget(self.synopsis_transfer_button, 0, Qt.AlignTop)
        synopsis_section.content_layout.addLayout(synopsis_layout)
        details_layout.addWidget(synopsis_section)

        # Setting
        setting_section = CollapsibleSection("設定")
        setting_layout = QHBoxLayout()
        self.setting_edit = QPlainTextEdit()
        self.setting_edit.setPlaceholderText("世界観、キャラクター設定などを入力...")
        self.setting_transfer_button = QPushButton("← 転記")
        self.setting_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("setting"))
        setting_layout.addWidget(self.setting_edit)
        setting_layout.addWidget(self.setting_transfer_button, 0, Qt.AlignTop)
        setting_section.content_layout.addLayout(setting_layout)
        details_layout.addWidget(setting_section)

        # Plot
        plot_section = CollapsibleSection("プロット")
        plot_layout = QHBoxLayout()
        self.plot_edit = QPlainTextEdit()
        self.plot_edit.setPlaceholderText("物語の展開、構成などを入力...")
        self.plot_transfer_button = QPushButton("← 転記")
        self.plot_transfer_button.clicked.connect(lambda: self._transfer_idea_to_details("plot"))
        plot_layout.addWidget(self.plot_edit)
        plot_layout.addWidget(self.plot_transfer_button, 0, Qt.AlignTop)
        plot_section.content_layout.addLayout(plot_layout)
        details_layout.addWidget(plot_section)

        details_layout.addStretch()

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
        self.memo_edit.clear()

    def _open_kobold_config_dialog(self):
        dialog = KoboldConfigDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_bar.showMessage("KoboldCpp 設定が更新されました。", 3000)
            self.kobold_client.reload_settings()
        else:
            self.status_bar.showMessage("KoboldCpp 設定の変更はキャンセルされました。", 3000)

    def _open_gen_params_dialog(self):
        dialog = GenerationParamsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_bar.showMessage("生成パラメータが更新されました。", 3000)
            self.kobold_client.reload_settings()
        else:
            self.status_bar.showMessage("生成パラメータの変更はキャンセルされました。", 3000)

    # --- Generation Control Slots ---
    @Slot()
    def _trigger_single_generation(self):
        """Starts a single generation task."""
        if self.generation_status != "idle":
            QMessageBox.warning(self, "生成中", "現在、別の生成が実行中です。")
            return

        self.generation_status = "single_running"
        self._update_ui_for_generation_start()

        main_text = self.main_text_edit.toPlainText()
        metadata = self._get_metadata_from_ui()
        prompt = build_prompt(self.current_mode, main_text, metadata)

        separator = f"\n--- 生成ブロック {self.output_block_counter} ---\n"
        self._append_to_output(separator)

        self.generation_task = asyncio.ensure_future(self._run_single_generation(prompt))

    @Slot()
    def _toggle_infinite_generation(self):
        """Starts or stops the infinite generation loop."""
        if self.generation_status == "infinite_running":
            self._stop_current_generation()
        elif self.generation_status == "idle":
            self._start_infinite_generation()
        else: # single_running
            QMessageBox.warning(self, "生成中", "現在、単発生成が実行中です。停止してから無限生成を開始してください。")
            self.infinite_gen_action.setChecked(False) # Uncheck the button

    def _start_infinite_generation(self):
        """Starts the infinite generation loop."""
        self.generation_status = "infinite_running"
        self._update_ui_for_generation_start()

        main_text = self.main_text_edit.toPlainText()
        metadata = self._get_metadata_from_ui()
        self.infinite_generation_prompt = build_prompt(self.current_mode, main_text, metadata)

        self.generation_task = asyncio.ensure_future(self._run_infinite_generation_loop())

    def _stop_current_generation(self):
        """Stops any currently running generation task."""
        if self.generation_status == "idle" or self.generation_task is None:
            return

        current_status_before_stop = self.generation_status
        self.generation_status = "idle" # Set status to idle first

        if current_status_before_stop == "infinite_running":
            self.status_bar.showMessage("無限生成 停止中...", 2000)
        else: # single_running
            self.status_bar.showMessage("単発生成 停止中...", 2000)

        if self.generation_task and not self.generation_task.done():
            self.generation_task.cancel()
            # Set task to None immediately after cancellation request
            self.generation_task = None

        self._update_ui_for_generation_stop()
        # Add a slight delay before final status message if needed
        # QTimer.singleShot(100, lambda: self.status_bar.showMessage("停止中", 3000))
        self.status_bar.showMessage("停止中", 3000)


    def _update_ui_for_generation_start(self):
        """Updates UI elements when generation starts."""
        if self.generation_status == "infinite_running":
            self.infinite_gen_action.setChecked(True)
            self.status_bar.showMessage("無限生成中 (F5で停止)...")
        elif self.generation_status == "single_running":
             self.infinite_gen_action.setChecked(False) # Ensure infinite is unchecked
             self.status_bar.showMessage("単発生成中...")

        self.single_gen_action.setEnabled(False)
        self.infinite_gen_action.setEnabled(self.generation_status == "infinite_running") # Only enable stop for infinite

    def _update_ui_for_generation_stop(self):
        """Updates UI elements when generation stops or completes."""
        self.infinite_gen_action.setChecked(False)
        self.single_gen_action.setEnabled(True)
        self.infinite_gen_action.setEnabled(True)
        # Status message is set by the calling function (_stop_current_generation or async methods)


    # --- Async Generation Methods ---
    async def _run_single_generation(self, prompt: str):
        """Runs a single generation and updates status."""
        try:
            async for token in self.kobold_client.generate_stream(prompt):
                self._append_to_output(token)
                await asyncio.sleep(0.001) # Yield control briefly

            # Finished successfully
            self.output_block_counter += 1
            self.status_bar.showMessage("単発生成 完了", 3000)

        except KoboldClientError as e:
            error_msg = f"\n--- エラー: {e} ---\n"
            self._append_to_output(error_msg)
            self.status_bar.showMessage("生成エラー", 3000)
        except asyncio.CancelledError:
            print("Single generation task cancelled unexpectedly.")
            self._append_to_output("\n--- 生成がキャンセルされました ---\n")
            self.status_bar.showMessage("生成キャンセル", 3000)
        except Exception as e:
             error_msg = f"\n--- 予期せぬエラーが発生しました: {e} ---\n"
             print(error_msg)
             self._append_to_output(error_msg)
             self.status_bar.showMessage("予期せぬエラー", 3000)
        finally:
            # Reset status after single run finishes or errors out
            self.generation_status = "idle"
            self._update_ui_for_generation_stop()
            self.generation_task = None

    async def _run_infinite_generation_loop(self):
        """Continuously generates text using the stored prompt."""
        if not self.infinite_generation_prompt:
            print("Error: Infinite generation prompt is empty.")
            self._stop_current_generation()
            return

        try:
            while self.generation_status == "infinite_running":
                separator = f"\n--- 生成ブロック {self.output_block_counter} ---\n"
                self._append_to_output(separator)
                try:
                    async for token in self.kobold_client.generate_stream(self.infinite_generation_prompt):
                        if self.generation_status != "infinite_running":
                            raise asyncio.CancelledError("Infinite generation stopped during stream.")
                        self._append_to_output(token)
                        await asyncio.sleep(0.001)

                    self.output_block_counter += 1
                    await asyncio.sleep(0.5) # Wait before next generation

                except KoboldClientError as e:
                    error_msg = f"\n--- 無限生成中エラー: {e} ---\n"
                    self._append_to_output(error_msg)
                    self.status_bar.showMessage("無限生成エラー発生、停止します", 5000)
                    self._stop_current_generation()
                    break
                except asyncio.CancelledError:
                     print("Infinite generation loop cancelled.")
                     # Don't append message here, _stop_current_generation handles UI
                     break
                except Exception as e:
                     error_msg = f"\n--- 無限生成中に予期せぬエラー: {e} ---\n"
                     print(error_msg)
                     self._append_to_output(error_msg)
                     self.status_bar.showMessage("予期せぬエラー発生、停止します", 5000)
                     self._stop_current_generation()
                     break
        finally:
            # Ensure status is reset if loop exits unexpectedly
            if self.generation_status == "infinite_running":
                 self._stop_current_generation()


    def _append_to_output(self, text: str):
        """Safely appends text to the output area and handles scrolling."""
        cursor = self.output_text_edit.textCursor()
        v_bar = self.output_text_edit.verticalScrollBar()
        is_at_bottom = v_bar.value() >= v_bar.maximum() - 5

        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)

        if is_at_bottom:
            v_bar.setValue(v_bar.maximum())

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
        if self.generation_status != "idle":
            self._stop_current_generation() # Attempt to stop gracefully
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
        if self.generation_status != "idle":
             QMessageBox.warning(self, "生成中", "生成中にモードは変更できません。")
             self.idea_mode_action.setChecked(self.current_mode == "idea") # Revert check state
             self.gen_mode_action.setChecked(self.current_mode == "generate")
             return
        self.current_mode = "generate"
        self.status_bar.showMessage("モード: 小説生成", 2000)

    @Slot()
    def _set_mode_idea(self):
        """Sets the application mode to 'idea'."""
        if self.generation_status != "idle":
             QMessageBox.warning(self, "生成中", "生成中にモードは変更できません。")
             self.idea_mode_action.setChecked(self.current_mode == "idea") # Revert check state
             self.gen_mode_action.setChecked(self.current_mode == "generate")
             return
        self.current_mode = "idea"
        self.status_bar.showMessage("モード: アイデア出し", 2000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    async def async_cleanup():
        await window._cleanup()
    app.aboutToQuit.connect(lambda: asyncio.ensure_future(async_cleanup()))
    window.show()

    with loop:
        loop.run_forever()
