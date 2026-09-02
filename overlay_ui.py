import sys
import ctypes
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor
import threading

WDA_EXCLUDEFROMCAPTURE = 0x00000011

class BoundingBoxOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make the window invisible to screen capture
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        
        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.boxes = [] # List of QRect to draw

    def set_boxes(self, boxes):
        self.boxes = boxes
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(255, 0, 0, 255)) # Red color
        pen.setWidth(4)
        painter.setPen(pen)
        
        for box in self.boxes:
            painter.drawRect(box)

class ChatWindow(QWidget):
    def __init__(self, agent_callback=None, voice_callback=None):
        super().__init__()
        self.agent_callback = agent_callback
        self.voice_callback = voice_callback
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make the window invisible to screen capture
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        
        self.initUI()
        
        self.overlay = BoundingBoxOverlay()
        self.overlay.show()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 15px;
            }
        """)
        h_layout = QHBoxLayout(self.container)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Breeze to do something...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(50, 50, 50, 255);
                color: white;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        self.input_field.returnPressed.connect(self.on_submit)
        
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(40, 40)
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.voice_btn.clicked.connect(self.on_voice)
        
        h_layout.addWidget(self.input_field)
        h_layout.addWidget(self.voice_btn)
        
        layout.addWidget(self.container)
        self.setLayout(layout)
        
        # Position at bottom center
        screen = QApplication.primaryScreen().geometry()
        width = 600
        height = 60
        x = (screen.width() - width) // 2
        y = screen.height() - height - 40
        self.setGeometry(x, y, width, height)

    def on_submit(self):
        text = self.input_field.text().strip()
        if text and self.agent_callback:
            self.input_field.clear()
            self.input_field.setPlaceholderText("Thinking...")
            # Run in a separate thread so UI doesn't freeze
            threading.Thread(target=self.run_agent, args=(text,), daemon=True).start()

    def on_voice(self):
        if self.voice_callback:
            self.input_field.setPlaceholderText("Listening...")
            threading.Thread(target=self.run_voice, daemon=True).start()

    def run_agent(self, text):
        self.agent_callback(text)
        # We need a signal/slot to update placeholder from thread, but keeping it simple for now
        # Will handle UI updates properly later.
        
    def run_voice(self):
        self.voice_callback()

    def draw_highlight(self, x, y, w, h):
        self.overlay.set_boxes([QRect(x, y, w, h)])
        # Hide after 5 seconds
        QTimer.singleShot(5000, lambda: self.overlay.set_boxes([]))
