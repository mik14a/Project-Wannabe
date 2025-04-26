import sys
import asyncio
import qasync # Import qasync
import re # Import regex module
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QStatusBar,
                               QSplitter, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QScrollArea, QLineEdit, QPushButton, QMessageBox,
                               QPlainTextEdit, QToolBar, QDialog, QLineEdit, QLabel, QComboBox, # Add QLabel, QComboBox
                               QPlainTextEdit) # Ensure QPlainTextEdit is imported
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor, QAction, QActionGroup, QFont # Add QFont

# Correctly import custom widgets and other modules
from src.ui.widgets import CollapsibleSection, TagWidget
from src.ui.dialogs import KoboldConfigDialog, GenerationParamsDialog
from src.core.kobold_client import KoboldClient, KoboldClientError
from src.core.prompt_builder import build_prompt
from src.core.settings import load_settings, DEFAULT_SETTINGS # Import DEFAULT_SETTINGS
from src.ui.menu_handler import MenuHandler # Import the new MenuHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Wannabe") # "(仮称)" を削除
        self.setGeometry(100, 100, 1200, 800)

        self.kobold_client = KoboldClient()
        # Generation status: "idle", "single_running", "infinite_running"
        self.generation_status = "idle"
        self.generation_task = None # Holds the asyncio task for generation
        self.output_block_counter = 1
        self.current_mode = "generate" # Initial mode: "generate" or "idea"
        self.infinite_generation_prompt = "" # Store prompt for infinite loop

        # Instantiate MenuHandler
        self.menu_handler = MenuHandler(self)

        # Create UI elements
        self._create_toolbar() # Create toolbar first
        self._create_status_bar()
        self._create_central_widget() # Create central widget before menu bar needs it
        self._create_menu_bar() # Create menu bar using the handler

        # Apply initial theme and font from settings via MenuHandler
        # These might be called within MenuHandler's creation logic already
        # self.menu_handler._apply_initial_font() # Ensure initial font is applied
        # self.menu_handler._apply_theme(load_settings().get("theme", "light")) # Ensure initial theme

    def _create_menu_bar(self):
        """Creates the menu bar using MenuHandler."""
        self.setMenuBar(self.menu_handler.create_menu_bar())

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

        # --- Rating Selection (Moved to top) ---
        rating_section = CollapsibleSection("レーティング (生成時)")
        rating_layout = QHBoxLayout()
        rating_label = QLabel("レーティング:")
        self.rating_combo_details = QComboBox()
        self.rating_combo_details.addItem("General (全年齢)", "general")
        self.rating_combo_details.addItem("R-18", "r18")
        rating_layout.addWidget(rating_label)
        rating_layout.addWidget(self.rating_combo_details)
        rating_layout.addStretch()
        rating_section.content_layout.addLayout(rating_layout)
        details_layout.addWidget(rating_section)
        # Load initial rating from settings
        initial_settings = load_settings()
        initial_rating = initial_settings.get("default_rating", DEFAULT_SETTINGS["default_rating"])
        initial_rating_index = self.rating_combo_details.findData(initial_rating)
        if initial_rating_index != -1:
            self.rating_combo_details.setCurrentIndex(initial_rating_index)
        # --- End Rating Selection ---

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

        # Dialogue Level
        dialogue_section = CollapsibleSection("セリフ量")
        dialogue_layout = QHBoxLayout()
        dialogue_label = QLabel("セリフ量:")
        self.dialogue_level_combo = QComboBox()
        self.dialogue_level_combo.addItems([
            "指定なし", "少ない", "やや少ない", "普通", "やや多い", "多い"
        ])
        dialogue_layout.addWidget(dialogue_label)
        dialogue_layout.addWidget(self.dialogue_level_combo)
        dialogue_layout.addStretch() # Add stretch to push combo box to the left
        dialogue_section.content_layout.addLayout(dialogue_layout)
        details_layout.addWidget(dialogue_section)

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
        """Starts a single generation task, or stops it if already running."""
        if self.generation_status == "single_running":
            # If single generation is running, stop it.
            self._stop_current_generation()
            return
        elif self.generation_status == "infinite_running":
            # If infinite generation is running, show warning and do nothing.
            QMessageBox.warning(self, "生成中", "現在、無限生成が実行中です。停止してから単発生成を開始してください。")
            return
        elif self.generation_status != "idle":
             # Handle unexpected status (should ideally not happen)
             QMessageBox.warning(self, "不明な状態", f"予期せぬ生成ステータスです: {self.generation_status}")
             return

        # Only proceed if status is idle
        self.generation_status = "single_running"
        self._update_ui_for_generation_start()

        main_text = self.main_text_edit.toPlainText()
        metadata, selected_rating = self._get_metadata_from_ui() # Get rating from UI
        # Load settings to get the prompt order (rating is now passed explicitly)
        settings = load_settings()
        cont_order = settings.get("cont_prompt_order", DEFAULT_SETTINGS["cont_prompt_order"])
        # Pass the selected rating from the details tab to build_prompt
        prompt = build_prompt(
            self.current_mode,
            main_text,
            metadata,
            cont_prompt_order=cont_order,
            rating_override=selected_rating # Pass the rating from UI
        )

        separator = f"\n--- 生成ブロック {self.output_block_counter} ---\n"
        self._append_to_output(separator)

        self.generation_task = asyncio.ensure_future(self._run_single_generation(prompt))

    @Slot()
    def _toggle_infinite_generation(self):
        """Starts/stops infinite generation, or stops single generation if running."""
        if self.generation_status == "infinite_running":
            # If infinite is running, stop it.
            self._stop_current_generation()
        elif self.generation_status == "single_running":
            # If single is running, stop it.
            self._stop_current_generation()
            # Ensure the infinite gen button remains unchecked as we just stopped single gen
            self.infinite_gen_action.setChecked(False)
        elif self.generation_status == "idle":
            # If idle, start infinite generation.
            self._start_infinite_generation()
        else: # Handle unexpected status
             QMessageBox.warning(self, "不明な状態", f"予期せぬ生成ステータスです: {self.generation_status}")
             self.infinite_gen_action.setChecked(False) # Ensure button is unchecked

    def _start_infinite_generation(self):
        """Starts the infinite generation loop."""
        self.generation_status = "infinite_running"
        self._update_ui_for_generation_start()

        # Initial prompt build (might be overwritten in loop if immediate update is on)
        main_text = self.main_text_edit.toPlainText()
        metadata, selected_rating = self._get_metadata_from_ui() # Get rating from UI
        # Load settings for initial prompt build (rating is now passed explicitly)
        settings = load_settings()
        cont_order = settings.get("cont_prompt_order", DEFAULT_SETTINGS["cont_prompt_order"])
        # Pass the selected rating from the details tab to build_prompt
        self.infinite_generation_prompt = build_prompt(
            self.current_mode,
            main_text,
            metadata,
            cont_prompt_order=cont_order,
            rating_override=selected_rating # Pass the rating from UI
        )

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

        # Keep actions enabled so they can be used to stop generation
        # self.single_gen_action.setEnabled(False) # Keep enabled
        # self.infinite_gen_action.setEnabled(False) # Keep enabled
        # The logic within the action handlers (_trigger_single_generation, _toggle_infinite_generation)
        # will determine whether to start or stop based on self.generation_status.

    def _update_ui_for_generation_stop(self):
        """Updates UI elements when generation stops or completes."""
        self.infinite_gen_action.setChecked(False) # Ensure infinite toggle is unchecked
        # Keep actions enabled
        # self.single_gen_action.setEnabled(True)
        # self.infinite_gen_action.setEnabled(True)
        # Status message is set by the calling function (_stop_current_generation or async methods)


    # --- Async Generation Methods ---
    async def _run_single_generation(self, prompt: str):
        """Runs a single generation and updates status."""
        try:
            # Get mode-specific max_length
            settings = load_settings()
            if self.current_mode == "idea":
                current_max_length = settings.get("max_length_idea", DEFAULT_SETTINGS["max_length_idea"])
            else: # generate mode
                current_max_length = settings.get("max_length_generate", DEFAULT_SETTINGS["max_length_generate"])

            # Pass max_length to generate_stream (assuming it accepts it)
            async for token in self.kobold_client.generate_stream(prompt, max_length=current_max_length):
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
        """Continuously generates text, potentially rebuilding the prompt based on settings."""
        # Load behavior setting based on current mode
        settings = load_settings()
        inf_gen_behavior = settings.get("infinite_generation_behavior", DEFAULT_SETTINGS["infinite_generation_behavior"])
        behavior_key = self.current_mode # "idea" or "generate"
        update_behavior = inf_gen_behavior.get(behavior_key, "manual") # Default to manual

        # Use the initially built prompt if behavior is manual
        current_prompt = self.infinite_generation_prompt
        if not current_prompt and update_behavior == "manual":
             print("Error: Initial infinite generation prompt is empty and behavior is manual.")
             self._stop_current_generation()
             return

        try:
            while self.generation_status == "infinite_running":
                # --- Rebuild prompt if behavior is 'immediate' ---
                if update_behavior == "immediate":
                    main_text = self.main_text_edit.toPlainText()
                    metadata, selected_rating = self._get_metadata_from_ui() # Get rating from UI
                    # Load settings again inside loop for immediate update (cont_order)
                    settings = load_settings()
                    cont_order = settings.get("cont_prompt_order", DEFAULT_SETTINGS["cont_prompt_order"])
                    # Pass the selected rating from the details tab to build_prompt
                    current_prompt = build_prompt(
                        self.current_mode,
                        main_text,
                        metadata,
                        cont_prompt_order=cont_order,
                        rating_override=selected_rating # Pass the rating from UI
                    )
                    if not current_prompt:
                         print("Warning: Rebuilt prompt for immediate update is empty. Skipping generation cycle.")
                         await asyncio.sleep(0.5) # Avoid busy-waiting
                         continue # Skip this generation cycle

                # --- Generate using the current_prompt ---
                separator = f"\n--- 生成ブロック {self.output_block_counter} ---\n"
                self._append_to_output(separator)
                try:
                    # Get mode-specific max_length inside the loop (in case settings change)
                    # Although changing settings during infinite gen might be blocked by UI logic
                    settings = load_settings()
                    if self.current_mode == "idea":
                        current_max_length = settings.get("max_length_idea", DEFAULT_SETTINGS["max_length_idea"])
                    else: # generate mode
                        current_max_length = settings.get("max_length_generate", DEFAULT_SETTINGS["max_length_generate"])

                    # Pass max_length to generate_stream (assuming it accepts it)
                    async for token in self.kobold_client.generate_stream(current_prompt, max_length=current_max_length):
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

    def _get_metadata_from_ui(self) -> tuple[dict, str]:
        """Retrieves metadata values and the selected rating from the UI widgets."""
        metadata = { # Initialize the dictionary first
            "title": self.title_edit.text(),
            "keywords": self.keywords_widget.get_tags(),
            "genres": self.genre_widget.get_tags(),
            "synopsis": self.synopsis_edit.toPlainText(),
            "setting": self.setting_edit.toPlainText(),
            "plot": self.plot_edit.toPlainText(),
        }
        # Add dialogue level if selected
        selected_level = self.dialogue_level_combo.currentText()
        if selected_level != "指定なし":
            metadata["dialogue_level"] = selected_level # Add to the dictionary

        # Get the selected rating from the details tab combo box
        selected_rating = self.rating_combo_details.currentData()

        return metadata, selected_rating # Return metadata dict and rating string

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
        """Transfers selected text from output area to main text area based on settings."""
        selected_text = self.output_text_edit.textCursor().selectedText()
        if not selected_text:
            self.status_bar.showMessage("出力エリアでテキストが選択されていません。", 2000)
            return

        settings = load_settings()
        transfer_mode = settings.get("transfer_to_main_mode", DEFAULT_SETTINGS["transfer_to_main_mode"])
        newlines_before = settings.get("transfer_newlines_before", DEFAULT_SETTINGS["transfer_newlines_before"])

        cursor = self.main_text_edit.textCursor()

        if transfer_mode == "cursor":
            cursor.insertText(selected_text)
        elif transfer_mode == "next_line_always":
            cursor.movePosition(QTextCursor.EndOfLine)
            newlines_to_insert = "\n" * (newlines_before + 1)
            cursor.insertText(newlines_to_insert + selected_text)
        elif transfer_mode == "next_line_eol":
            if cursor.atBlockEnd():
                # Behave like next_line_always if at end of line (block)
                cursor.movePosition(QTextCursor.EndOfLine) # Ensure truly at end
                newlines_to_insert = "\n" * (newlines_before + 1)
                cursor.insertText(newlines_to_insert + selected_text)
            else:
                # Behave like cursor mode if not at end of line
                cursor.insertText(selected_text)
        else: # Fallback to cursor mode if setting is invalid
            cursor.insertText(selected_text)

        self.status_bar.showMessage("選択範囲を本文エリアに転記しました。", 2000)

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

        # Find the target section header anywhere in the selection and capture everything after it
        pattern = re.compile(rf"# {re.escape(target_name)}:\s*(.*)", re.MULTILINE | re.DOTALL)
        match = pattern.search(selected_text)

        if not match:
            self.status_bar.showMessage(f"選択範囲から「{target_name}」セクションが見つかりませんでした。", 3000)
            return

        # Extract content after the header and process line by line
        content_after_header = match.group(1).strip()
        lines = content_after_header.splitlines()
        extracted_lines = []
        for line in lines:
            # Check if the line starts with another section header
            is_next_header = False
            # Iterate through all possible Japanese names in the map
            for key, jp_name in japanese_name_map.items():
                # Make sure we don't stop at the *current* header if it appears again,
                # only stop if it's a *different* header.
                if key != metadata_key and line.strip().startswith(f"# {jp_name}:"):
                    is_next_header = True
                    break # Found a different header, stop checking for this line
            
            if is_next_header:
                break # Stop extracting lines when the next header is found
            extracted_lines.append(line) # Append the line if it's not a subsequent header

        extracted_value = "\n".join(extracted_lines).strip() # Join the extracted lines

        # Handle potential empty extraction if the target header was last or immediately followed
        # (extracted_value might be "" here, which is generally okay, but check specific cases)

        try:
            if metadata_key == "title":
                # Title should be single line, take the first extracted line
                extracted_value = extracted_value.splitlines()[0] if extracted_value else ""
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
