import sys
import ctypes
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QApplication, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QRect, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
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


class VoiceButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.is_listening = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        if self.is_listening:
            painter.setBrush(QColor(50, 120, 240)) # ChatGPT blue
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            if self.underMouse():
                painter.setBrush(QColor(255, 255, 255, 30))
            else:
                painter.setBrush(QColor(255, 255, 255, 10))
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
            
        # Draw circle
        painter.drawEllipse(1, 1, 38, 38)
        
        # Setup pen for icons
        painter.setPen(QPen(Qt.GlobalColor.white, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        
        cx, cy = 20, 20
        
        if self.is_listening:
            # Draw Audio Waveform (5 bars)
            painter.drawLine(cx, cy - 8, cx, cy + 8)         # Center
            painter.drawLine(cx - 5, cy - 4, cx - 5, cy + 4) # Inner left
            painter.drawLine(cx + 5, cy - 4, cx + 5, cy + 4) # Inner right
            painter.drawLine(cx - 10, cy - 2, cx - 10, cy + 2) # Outer left
            painter.drawLine(cx + 10, cy - 2, cx + 10, cy + 2) # Outer right
        else:
            # Draw Microphone
            # Capsule
            painter.drawRoundedRect(int(cx - 3.5), int(cy - 8), 7, 11, 3.5, 3.5)
            # Arc
            painter.drawArc(cx - 8, cy - 4, 16, 12, 180 * 16, 180 * 16)
            # Stand
            painter.drawLine(cx, cy + 8, cx, cy + 12)
            
    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

class ChatWindow(QWidget):
    error_signal = pyqtSignal(str)
    highlight_signal = pyqtSignal(int, int, int, int)
    listening_signal = pyqtSignal(bool)

    def __init__(self, agent_callback=None, voice_callback=None, stop_tts_callback=None):
        super().__init__()
        self.agent_callback = agent_callback
        self.voice_callback = voice_callback
        self.stop_tts_callback = stop_tts_callback
        
        self.error_signal.connect(self._show_error_slot)
        self.highlight_signal.connect(self._draw_highlight_slot)
        self.listening_signal.connect(self._set_listening_state_slot)
        
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
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(40, 40, 45, 230), stop:1 rgba(20, 20, 25, 230));
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        h_layout = QHBoxLayout(self.container)
        h_layout.setContentsMargins(15, 10, 15, 10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Breeze to do something...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                padding: 5px;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 16px;
                font-weight: 400;
            }
        """)
        self.input_field.returnPressed.connect(self.on_submit)
        
        self.voice_btn = VoiceButton()
        self.voice_btn.clicked.connect(self.on_voice)
        
        self.close_btn = QPushButton("✖")
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                color: #e0e0e0;
                border-radius: 20px;
                font-size: 16px;
                border: 1px solid rgba(255, 255, 255, 15);
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 30);
                color: #FF4444;
                border: 1px solid rgba(255, 0, 0, 50);
            }
        """)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        
        h_layout.addWidget(self.input_field)
        h_layout.addWidget(self.voice_btn)
        h_layout.addWidget(self.close_btn)
        
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
        self.anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self.anim.start()

    def on_submit(self):
        text = self.input_field.text().strip()
        if text and self.agent_callback:
            self.input_field.clear()
            self.input_field.setPlaceholderText("Thinking...")
            # Run in a separate thread so UI doesn't freeze
            threading.Thread(target=self.run_agent, args=(text,), daemon=True).start()

    def set_listening_state(self, is_listening):
        self.listening_signal.emit(is_listening)

    def _set_listening_state_slot(self, is_listening):
        self.voice_btn.is_listening = is_listening
        self.voice_btn.update()
        
        if is_listening:
            self.input_field.setPlaceholderText("Listening...")
        else:
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

