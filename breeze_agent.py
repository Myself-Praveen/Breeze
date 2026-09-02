import os
import mss
import pyautogui
import speech_recognition as sr
import pyttsx3
import json
from PIL import Image
import keyring
from google import genai
from google.genai import types

class BreezeAgent:
    def __init__(self, ui_window):
        self.ui = ui_window
        # Initialize TTS
        self.tts_engine = pyttsx3.init()
        # Initialize Gemini Client
        self.api_key = keyring.get_password("Breeze", "GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def speak(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio)
                return text
            except Exception as e:
                print("Error recording voice:", e)
                return ""

    def capture_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img_path = "screenshot.jpg"
            img.save(img_path)
            return img_path

    def process_command(self, command):
        if not self.client:
            print("GEMINI_API_KEY not set!")
            self.speak("API Key not found.")
            return

        img_path = self.capture_screen()
        img = Image.open(img_path)

        prompt = f"""
        You are Breeze, an AI desktop assistant. The user has given this command: "{command}".
        You have a screenshot of the user's screen.
        If the command implies finding an element to click or highlight, provide the bounding box in the format:
        [ymin, xmin, ymax, xmax] where values are between 0 and 1000.
        If the user asks a general question, just reply with text.
        Respond with a JSON object containing:
        {{
            "action": "click" | "highlight" | "reply",
            "box_2d": [ymin, xmin, ymax, xmax],
            "text": "Your reply or explanation"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            result = json.loads(response.text)
            print("AI Response:", result)
            
            action = result.get("action")
            text = result.get("text", "")
            
            if text:
                self.speak(text)
                
            if action in ["click", "highlight"] and "box_2d" in result:
                box = result["box_2d"]
                # Convert 0-1000 scale to screen coordinates
                screen_width, screen_height = pyautogui.size()
                ymin, xmin, ymax, xmax = box
                x = int((xmin / 1000) * screen_width)
                y = int((ymin / 1000) * screen_height)
                w = int(((xmax - xmin) / 1000) * screen_width)
                h = int(((ymax - ymin) / 1000) * screen_height)
                
                if action == "highlight":
                    self.ui.draw_highlight(x, y, w, h)
                elif action == "click":
                    # Center of the box
                    cx = x + w // 2
                    cy = y + h // 2
                    pyautogui.click(cx, cy)
                    
        except Exception as e:
            print("Error processing command:", e)

    def handle_voice_command(self):
        command = self.listen()
        if command:
            print("Voice Command:", command)
            # Update UI from main thread in real app, here we just print
            self.process_command(command)
