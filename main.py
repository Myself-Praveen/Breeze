import sys
from PyQt6.QtWidgets import QApplication
from overlay_ui import ChatWindow
from breeze_agent import BreezeAgent

def main():
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
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
