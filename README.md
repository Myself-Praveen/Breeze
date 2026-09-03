<div align="center">
  <img src="website/banner.png" alt="Breeze Banner" width="100%" style="border-radius: 20px;">
  <h1>Breeze</h1>
  <p><strong>An offline-first AI desktop assistant that reads your screen and automates your workflows.</strong></p>
  
  [![Website](https://img.shields.io/badge/Website-breeze--desktop.vercel.app-blue?style=flat-square)](https://breeze-desktop.vercel.app/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
  [![Windows Only](https://img.shields.io/badge/Platform-Windows_10_|_11-0078D6?style=flat-square&logo=windows)](https://microsoft.com)
</div>

<br />

Breeze is a next-generation, AI-powered Windows desktop agent designed to streamline your daily computer interactions. Operating entirely as a sleek, transparent glassmorphic overlay, Breeze sits quietly above your taskbar. It is always one click or voice command away from helping you navigate software, process on-screen text, open media, and take autonomous actions across your operating system.

---

## Core Features

- **Agent Mode (Autonomous Action)**: Breeze acts as an active agent on your computer. When given a complex command, it processes the intent, calculates screen coordinates, and autonomously executes precise mouse clicks, keystrokes, and scrolling actions.
- **Voice First Interaction**: Built-in Speech-to-Text integration means you can seamlessly talk to Breeze without ever touching your keyboard. Click the microphone button to initiate a secure, local listening session.
- **High-Quality Speech Synthesis**: Breeze talks back using state-of-the-art neural Edge TTS, providing natural, human-like voice feedback that is significantly superior to standard OS text-to-speech engines.
- **Media Deep Links**: Instantly play music and media. You can instruct Breeze to search YouTube for specific content or open a song directly in the desktop Spotify client, and it dynamically handles the application routing.
- **WhatsApp Automation**: Send messages hands-free. Breeze integrates with the Windows WhatsApp client to automatically open specific chats, type out messages, and send them on your behalf.
- **Screen Awareness (Hybrid OCR Architecture)**: To respect rate limits and maximize privacy, Breeze uses a custom Hybrid Map Architecture. It leverages local Tesseract OCR to read and map your screen's text natively, completely bypassing the need to constantly upload heavy screenshots to cloud vision APIs.
- **Premium Glassmorphic UI**: Built with PyQt6, the interface features a modern, custom vector-drawn command bar that reads your active display geometry to ensure it floats perfectly above your taskbar without interrupting your workflow.

---

## Architecture & Technology Stack

Breeze is built on a robust, multi-threaded combination of local processing tools and cloud language models:

- **PyQt6**: Drives the frameless, transparent overlay. All icons and visual elements are custom-painted using QPainter for crisp vector graphics on high-DPI displays.
- **Tesseract OCR (pytesseract)**: Powers the local screen text extraction, allowing the application to build a spatial map of interactable UI elements locally.
- **Google GenAI API (Gemini)**: Serves as the core reasoning engine. It processes the text-only intent maps and generates JSON-formatted spatial coordinate commands.
- **PyAutoGUI**: Executes low-level OS automation for controlling the cursor and keyboard input.
- **Edge-TTS & Pygame**: Delivers high-fidelity neural voice output asynchronously to prevent UI blocking.
- **SpeechRecognition**: Handles raw microphone input and transcription.
- **MSS**: Provides lightning-fast, multi-monitor screen captures required for the OCR pipeline.
- **Keyring**: Secures your API keys natively in the Windows Credential Manager.

---

## Installation & Setup Guide

### System Prerequisites
1. **Operating System**: Windows 10 or Windows 11
2. **Python**: Python 3.10 or higher
3. **Tesseract OCR engine**: You must install the Tesseract engine on your system for the local vision capabilities to function. 
   - Download the installer from the [UB Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
   - Install the software (default path is usually `C:\Program Files\Tesseract-OCR`).
   - **Crucial Step**: Ensure the installation directory is added to your Windows system `PATH` environment variable.

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Myself-Praveen/Breeze.git
   cd Breeze
   ```

2. **Install all required dependencies:**
   It is highly recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your API Key:**
   Breeze requires a Google Gemini API key to process complex intents. The application uses the Python `keyring` library to securely store this key in your Windows Credential Manager. 
   
   When you launch the application for the first time, it will detect if a key is missing and securely prompt you to enter it in the terminal before initializing the UI.

### Launching the Application
Execute the main entry point:
```bash
python main.py
```
Upon successful launch, Breeze will initialize as a transparent overlay at the bottom center of your primary monitor. Click the microphone icon to begin a voice command, or simply type your instruction into the command bar.

---

## Usage Examples & Capabilities

Breeze is designed to understand natural language. Below are examples of operations the agent can perform natively:

- **Web Searches**: *"Search the web for the latest Python documentation."*
- **Media Playback**: *"Play the Interstellar soundtrack on YouTube."* or *"Open Spotify and play my liked songs."*
- **Application Launching**: *"Open Calculator."*
- **Communication Automation**: *"Text Praveen on WhatsApp saying I will be 5 minutes late."*
- **Spatial Interactions**: *"Click on the search bar"* or *"Scroll down the page."*

---

## Packaging for Deployment (Optional)

If you wish to compile Breeze into a standalone `.exe` executable for distribution, the repository is already configured for PyInstaller.

```bash
pip install pyinstaller
pyinstaller main.spec
```
The compiled executable will be available in the `dist/` directory.

---

## Project Website
For additional information, documentation, and download links, please visit the official landing page: 
[https://breeze-desktop.vercel.app/](https://breeze-desktop.vercel.app/)

## License
This project is open-source and available under the MIT License.
