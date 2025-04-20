from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QFrame,
                               QScrollArea, QLineEdit, QLabel, QPushButton, QSizePolicy, # Keep QSizePolicy
                               QSpacerItem, QLayout)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Signal, QSize, QRect, QPoint # Add QSize, QRect, QPoint for FlowLayout
from PySide6.QtGui import QResizeEvent

class CollapsibleSection(QWidget):
    """
    A collapsible section widget containing a header button and a content area.
    """
    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)

        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self._on_pressed)

        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)
        # Correct usage of QSizePolicy:
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setFrameShape(QFrame.NoFrame)

        # Use a QWidget as the container for the actual content layout
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5) # Add some padding
        self.content_area.setWidget(self.content_widget)
        self.content_area.setWidgetResizable(True) # Important for layout

        self.toggle_animation = QParallelAnimationGroup(self)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

        # Initial state: collapsed
        self.toggle_button.setChecked(False)


    def _on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if not checked else Qt.RightArrow)
        self.toggle_animation.clear() # Clear previous animations

        # Determine start and end values based on current state
        start_value = self.content_area.maximumHeight()
        end_value = 0 if checked else self.content_widget.sizeHint().height() + 10 # Add a bit extra space

        animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        animation.setDuration(300) # Animation duration in ms
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(QEasingCurve.InOutQuart)

        self.toggle_animation.addAnimation(animation)
        self.toggle_animation.start()

    def setContentLayout(self, layout: QVBoxLayout):
        """Sets the layout for the content area."""
        # Remove the old layout and widget if they exist
        old_layout = self.content_widget.layout()
        if old_layout is not None:
            # Properly delete widgets within the old layout
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            del old_layout

        # Set the new layout on the content_widget
        self.content_widget.setLayout(layout)
        # Recalculate collapsed height after setting new content
        collapsed_height = self.sizeHint().height() - self.content_area.maximumHeight()
        self.content_area.setMaximumHeight(0 if not self.toggle_button.isChecked() else self.content_widget.sizeHint().height() + 10)
        self.setMinimumHeight(collapsed_height)

    def addWidget(self, widget: QWidget):
        """Adds a widget to the content layout."""
        self.content_layout.addWidget(widget)


# Simple Flow Layout (adjust as needed)
# Based on https://doc.qt.io/qtforpython-6/examples/example_widgets_layouts_flowlayout.html
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.hSpacing = hSpacing
        self.vSpacing = vSpacing
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)
        self.invalidate() # Trigger recalculation

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            item = self.itemList.pop(index)
            self.invalidate() # Trigger recalculation
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0) # Not expanding

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(width, True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect.width(), False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _doLayout(self, width, testOnly):
        margins = self.contentsMargins()
        effectiveWidth = width - margins.left() - margins.right()
        x = margins.left()
        y = margins.top()
        lineHeight = 0

        hSpacing = self.spacing() if self.hSpacing == -1 else self.hSpacing
        vSpacing = self.spacing() if self.vSpacing == -1 else self.vSpacing

        for item in self.itemList:
            wid = item.widget()
            spaceX = hSpacing
            if spaceX == -1:
                spaceX = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = vSpacing
            if spaceY == -1:
                spaceY = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveWidth and lineHeight > 0:
                x = margins.left()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight + margins.bottom()


class TagWidget(QWidget):
    """
    A widget for inputting and displaying tags.
    """
    tagsChanged = Signal(list) # Signal emitted when tags change

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._tags = set()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Input area
        input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("タグを入力 (スペース区切り)")
        self.tag_input.returnPressed.connect(self._add_tags_from_input)
        add_button = QPushButton("追加")
        add_button.clicked.connect(self._add_tags_from_input)
        self.transfer_button = QPushButton("← 転記") # Transfer button

        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(add_button)
        input_layout.addWidget(self.transfer_button) # Add transfer button here
        main_layout.addLayout(input_layout)

        # Tag display area using FlowLayout
        self.tags_display_widget = QWidget() # Container for flow layout
        self.tags_layout = FlowLayout(self.tags_display_widget, 5, 5, 5) # margin, hspacing, vspacing
        main_layout.addWidget(self.tags_display_widget)
        main_layout.addStretch() # Push tags upwards

    def _add_tags_from_input(self):
        text = self.tag_input.text().strip()
        if not text:
            return
        new_tags = [tag.strip() for tag in text.split() if tag.strip()]
        added = False
        for tag in new_tags:
            if tag not in self._tags:
                self._tags.add(tag)
                self._add_tag_label(tag)
                added = True
        self.tag_input.clear()
        if added:
            self.tagsChanged.emit(self.get_tags())
            self.tags_display_widget.adjustSize() # Adjust container size

    def _add_tag_label(self, tag_text: str):
        tag_label_widget = QWidget()
        tag_layout = QHBoxLayout(tag_label_widget)
        tag_layout.setContentsMargins(2, 2, 2, 2)
        tag_layout.setSpacing(3)

        label = QLabel(tag_text)
        label = QLabel(tag_text)
        label.setStyleSheet("color: black;") # Ensure text is black

        remove_button = QPushButton("x")
        remove_button.setFixedSize(16, 16)
        # Ensure button text is visible too, and provide some contrast
        remove_button.setStyleSheet("QPushButton { border: none; font-weight: bold; color: black; background-color: #cccccc; border-radius: 8px; } QPushButton:hover { background-color: #bbbbbb; }")
        remove_button.clicked.connect(lambda: self._remove_tag(tag_text, tag_label_widget))

        tag_layout.addWidget(label)
        tag_layout.addWidget(remove_button)
        # Use a slightly lighter gray background for the tag itself
        tag_label_widget.setStyleSheet("QWidget { background-color: #d3d3d3; border-radius: 5px; padding: 1px 3px; }") # Added padding
        tag_label_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed) # Prevent stretching

        self.tags_layout.addWidget(tag_label_widget)

    def _remove_tag(self, tag_text: str, widget: QWidget):
        if tag_text in self._tags:
            self._tags.remove(tag_text)
            self.tags_layout.removeWidget(widget)
            widget.deleteLater()
            self.tagsChanged.emit(self.get_tags())
            self.tags_display_widget.adjustSize() # Adjust container size

    def get_tags(self) -> list[str]:
        """Returns the current list of tags."""
        return sorted(list(self._tags))

    def set_tags(self, tags: list[str]):
        """Sets the tags, replacing existing ones."""
        # Clear existing tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._tags.clear()

        # Add new tags
        added = False
        for tag in tags:
            tag = tag.strip()
            if tag and tag not in self._tags:
                self._tags.add(tag)
                self._add_tag_label(tag)
                added = True
        if added:
            self.tagsChanged.emit(self.get_tags())
            self.tags_display_widget.adjustSize() # Adjust container size

    def clear(self):
        """Clears all tags."""
        self.set_tags([])
