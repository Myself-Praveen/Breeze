import sys
import os
import warnings

# Suppress annoying terminal warnings
warnings.filterwarnings("ignore", module="requests")
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"

import signal
from PyQt6.QtWidgets import QApplication
from overlay_ui import ChatWindow
from breeze_agent import BreezeAgent

def main():
    # Allow Ctrl+C to close the application in the terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    
    # Ensure the app doesn't quit if the transparent window is the only one open
    app.setQuitOnLastWindowClosed(True)
    
    # Initialize UI
    window = ChatWindow()
    
    # Initialize Agent
    agent = BreezeAgent(window)
    
    # Connect callbacks
    window.agent_callback = agent.process_command
    window.voice_callback = agent.handle_voice_command
    window.stop_tts_callback = agent.stop_speaking
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
