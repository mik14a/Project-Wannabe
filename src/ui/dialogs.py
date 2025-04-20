from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
                               QDoubleSpinBox, QTextEdit, QFormLayout,
                               QDialogButtonBox, QWidget)
from src.core.settings import load_settings, save_settings, DEFAULT_SETTINGS

class KoboldConfigDialog(QDialog):
    """Dialog for configuring KoboldCpp connection settings."""
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("KoboldCpp 設定")

        self.current_settings = load_settings()

        layout = QVBoxLayout(self)

        # Port setting
        port_layout = QHBoxLayout()
        port_label = QLabel("KoboldCpp API Port:")
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(self.current_settings.get("kobold_port", 5001))
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_spinbox)
        layout.addLayout(port_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        """Saves the settings when OK is clicked."""
        self.current_settings["kobold_port"] = self.port_spinbox.value()
        save_settings(self.current_settings)
        super().accept()

    @staticmethod
    def show_dialog(parent: QWidget | None = None) -> bool:
        """Creates and shows the dialog, returning True if accepted."""
        dialog = KoboldConfigDialog(parent)
        return dialog.exec() == QDialog.Accepted

class GenerationParamsDialog(QDialog):
    """Dialog for configuring LLM generation parameters."""
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("生成パラメータ設定")
        self.setMinimumWidth(400) # Set a minimum width

        self.current_settings = load_settings()

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # max_length
        self.max_length_spinbox = QSpinBox()
        self.max_length_spinbox.setRange(1, 10000) # Adjust max as needed
        self.max_length_spinbox.setValue(self.current_settings.get("max_length", DEFAULT_SETTINGS["max_length"]))
        form_layout.addRow("Max Length:", self.max_length_spinbox)

        # temperature
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(0.0, 5.0) # Allow higher temps if needed
        self.temp_spinbox.setSingleStep(0.05)
        self.temp_spinbox.setDecimals(2)
        self.temp_spinbox.setValue(self.current_settings.get("temperature", DEFAULT_SETTINGS["temperature"]))
        form_layout.addRow("Temperature:", self.temp_spinbox)

        # min_p
        self.min_p_spinbox = QDoubleSpinBox()
        self.min_p_spinbox.setRange(0.0, 1.0)
        self.min_p_spinbox.setSingleStep(0.01)
        self.min_p_spinbox.setDecimals(2)
        self.min_p_spinbox.setValue(self.current_settings.get("min_p", DEFAULT_SETTINGS["min_p"]))
        form_layout.addRow("Min P:", self.min_p_spinbox)

        # top_p
        self.top_p_spinbox = QDoubleSpinBox()
        self.top_p_spinbox.setRange(0.0, 1.0)
        self.top_p_spinbox.setSingleStep(0.01)
        self.top_p_spinbox.setDecimals(2)
        self.top_p_spinbox.setValue(self.current_settings.get("top_p", DEFAULT_SETTINGS["top_p"]))
        form_layout.addRow("Top P:", self.top_p_spinbox)

        # rep_pen
        self.rep_pen_spinbox = QDoubleSpinBox()
        self.rep_pen_spinbox.setRange(1.0, 5.0) # Adjust max as needed
        self.rep_pen_spinbox.setSingleStep(0.01)
        self.rep_pen_spinbox.setDecimals(2)
        self.rep_pen_spinbox.setValue(self.current_settings.get("rep_pen", DEFAULT_SETTINGS["rep_pen"]))
        form_layout.addRow("Repetition Penalty:", self.rep_pen_spinbox)

        main_layout.addLayout(form_layout)

        # Stop Sequences
        stop_seq_label = QLabel("ストップシーケンス (1行に1つ):")
        self.stop_seq_edit = QTextEdit()
        self.stop_seq_edit.setAcceptRichText(False)
        self.stop_seq_edit.setPlaceholderText("例:\n[INST]\n[/INST]\n<|endoftext|>")
        stop_sequences = self.current_settings.get("stop_sequences", DEFAULT_SETTINGS["stop_sequences"])
        self.stop_seq_edit.setText("\n".join(stop_sequences))
        main_layout.addWidget(stop_seq_label)
        main_layout.addWidget(self.stop_seq_edit)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def accept(self):
        """Saves the settings when OK is clicked."""
        self.current_settings["max_length"] = self.max_length_spinbox.value()
        self.current_settings["temperature"] = self.temp_spinbox.value()
        self.current_settings["min_p"] = self.min_p_spinbox.value()
        self.current_settings["top_p"] = self.top_p_spinbox.value()
        self.current_settings["rep_pen"] = self.rep_pen_spinbox.value()

        # Process stop sequences: split by newline, strip whitespace, remove empty lines
        stop_sequences_text = self.stop_seq_edit.toPlainText()
        stop_sequences_list = [line.strip() for line in stop_sequences_text.splitlines() if line.strip()]
        self.current_settings["stop_sequences"] = stop_sequences_list

        save_settings(self.current_settings)
        super().accept()

    @staticmethod
    def show_dialog(parent: QWidget | None = None) -> bool:
       """Creates and shows the dialog, returning True if accepted."""
       dialog = GenerationParamsDialog(parent)
       return dialog.exec() == QDialog.Accepted

if __name__ == '__main__':
    # Example usage for testing dialogs individually
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test KoboldConfigDialog
    print("Showing Kobold Config Dialog...")
    if KoboldConfigDialog.show_dialog():
        print("Kobold Config Dialog Accepted. Settings potentially saved.")
        print("Current settings:", load_settings())
    else:
        print("Kobold Config Dialog Cancelled.")

    # Test GenerationParamsDialog
    print("\nShowing Generation Params Dialog...")
    if GenerationParamsDialog.show_dialog():
        print("Generation Params Dialog Accepted. Settings potentially saved.")
        print("Current settings:", load_settings())
    else:
        print("Generation Params Dialog Cancelled.")

    sys.exit(app.exec())
