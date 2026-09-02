import sys
import ctypes
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
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
        
        # Get screen geometry covering all monitors
        rect = QRect()
        for screen in QApplication.screens():
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)
        
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
    error_signal = pyqtSignal(str)
    highlight_signal = pyqtSignal(int, int, int, int)

    def __init__(self, agent_callback=None, voice_callback=None, stop_tts_callback=None):
        super().__init__()
        self.agent_callback = agent_callback
        self.voice_callback = voice_callback
        self.stop_tts_callback = stop_tts_callback
        
        self.error_signal.connect(self._show_error_slot)
        self.highlight_signal.connect(self._draw_highlight_slot)
        
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.stop_tts_callback:
            self.stop_tts_callback()
        super().keyPressEvent(event)

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
        final_geom = QRect(x, y, width, height)
        self.animate_show(final_geom)

    def animate_show(self, final_geom):
        start_geom = QRect(final_geom.x(), final_geom.y() + 100, final_geom.width(), final_geom.height())
        self.setGeometry(start_geom)
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(600)
        self.anim.setStartValue(start_geom)
        self.anim.setEndValue(final_geom)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.start()

    def on_submit(self):
        text = self.input_field.text().strip()
        if text and self.agent_callback:
            self.input_field.clear()
            self.input_field.setPlaceholderText("Thinking...")
            # Run in a separate thread so UI doesn't freeze
            threading.Thread(target=self.run_agent, args=(text,), daemon=True).start()

    def set_listening_state(self, is_listening):
        if is_listening:
            self.voice_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border-radius: 20px;
                    font-size: 18px;
                }
            """)
            self.input_field.setPlaceholderText("Listening...")
        else:
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
            self.input_field.setPlaceholderText("Ask Breeze to do something...")

    def on_voice(self):
        if self.voice_callback:
            self.set_listening_state(True)
            threading.Thread(target=self.run_voice, daemon=True).start()

    def run_agent(self, text):
        self.agent_callback(text)
        
    def run_voice(self):
        self.voice_callback()
        # Reset state after recording (needs main thread UI update, but simpler here)
        self.set_listening_state(False)


    def draw_highlight(self, x, y, w, h):
        self.highlight_signal.emit(x, y, w, h)

    def _draw_highlight_slot(self, x, y, w, h):
        self.overlay.set_boxes([QRect(x, y, w, h)])
        # Hide after 5 seconds
        QTimer.singleShot(5000, lambda: self.overlay.set_boxes([]))

    def show_error(self, msg):
        self.error_signal.emit(msg)

    def _show_error_slot(self, msg):
        self.input_field.setText("")
        self.input_field.setPlaceholderText(f"Error: {msg}")
        QTimer.singleShot(3000, lambda: self.input_field.setPlaceholderText("Ask Breeze to do something..."))

