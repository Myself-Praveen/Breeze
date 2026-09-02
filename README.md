# Breeze

Breeze is an AI-powered Windows desktop tutor and agent. It runs as a transparent overlay on your screen, ready to help you navigate software, learn how to use applications, and automate your workflows.

## Features

- **Tutor Mode**: Asks the AI for guidance, and it draws visual highlights (bounding boxes) directly on your screen to show you where to click or look.
- **Agent Mode**: Tell the AI what you want to achieve, and it takes control, executing mouse clicks and keyboard typing autonomously.
- **Voice Commands**: Integrated Speech-to-Text allows you to simply talk to Breeze.
- **Voice Readback**: Breeze speaks to you, providing audio feedback using Text-to-Speech.
- **Text Chat Bar**: A sleek, non-intrusive chat interface floating on your screen for quick commands.
- **Privacy Respecting**: Operates locally where possible, and only captures the screen when a command is given.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Myself-Praveen/Breeze.git
   cd Breeze
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your API Key (e.g., Google Gemini):
   ```bash
   set GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the main application:
```bash
python main.py
```

Breeze will start as a transparent overlay. Use the chat bar at the bottom to type your instructions, or click the microphone button to speak.

## Architecture

- **PyQt6**: Drives the transparent overlay and chat interface.
- **mss**: Fast screen capturing.
- **google-genai**: Provides the multimodal vision capabilities to understand the screen and generate coordinates.
- **pyautogui**: Executes OS-level automation for clicks and keyboard input.
- **SpeechRecognition & pyttsx3**: Handles Voice Input and Output.
