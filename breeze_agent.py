import os
import mss
import pyautogui
import speech_recognition as sr
import pyttsx3
import json
from PIL import Image
import multiprocessing
import keyring
from google import genai
from google.genai import types
import pytesseract

def _tts_worker(text):
    import pyttsx3
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

class BreezeAgent:
    def __init__(self, ui_window):
        self.ui = ui_window
        self.tts_process = None
        # Initialize Gemini Client
        self.api_key = keyring.get_password("Breeze", "GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def speak(self, text):
        self.stop_speaking()
        self.tts_process = multiprocessing.Process(target=_tts_worker, args=(text,))
        self.tts_process.start()

    def stop_speaking(self):
        if self.tts_process and self.tts_process.is_alive():
            self.tts_process.terminate()
            self.tts_process.join()

    def listen(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio)
                return text
            except Exception as e:
                self.ui.show_error(f"Voice recording failed: {e}")
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
            self.ui.show_error("GEMINI_API_KEY not found in Keyring!")
            self.speak("API Key not found.")
            return

        img_path = self.capture_screen()
        img = Image.open(img_path)

        # Local OCR pass for fast simple clicks
        if command.lower().startswith("click"):
            target_text = command[5:].strip().lower()
            try:
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                for i, word in enumerate(ocr_data['text']):
                    if word.strip().lower() == target_text:
                        x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                        pyautogui.click(x + w//2, y + h//2)
                        return
            except Exception as e:
                print("OCR unavailable or failed:", e)

        prompt = f"""
        You are Breeze, an AI desktop assistant. The user has given this command: "{command}".
        You have a screenshot of the user's screen.
        If the command implies finding an element to click or highlight, provide the bounding box in the format:
        [ymin, xmin, ymax, xmax] where values are between 0 and 1000.
        If the command implies typing text, use action "type" and provide the text.
        If the command implies scrolling, use action "scroll" and provide amount (positive for up, negative for down).
        If the user asks a general question, just reply with text.
        Respond with a JSON object containing:
        {{
            "action": "click" | "highlight" | "reply" | "type" | "scroll",
            "box_2d": [ymin, xmin, ymax, xmax],
            "text": "Your reply or text to type",
            "amount": 500
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
            
            if action == "reply" and text:
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
            
            elif action == "type" and text:
                pyautogui.typewrite(text, interval=0.05)
            
            elif action == "scroll":
                amount = result.get("amount", -500)
                pyautogui.scroll(amount)
                
        except Exception as e:
            self.ui.show_error(f"Error processing command: {e}")


    def handle_voice_command(self):
        command = self.listen()
        if command:
            print("Voice Command:", command)
            # Update UI from main thread in real app, here we just print
            self.process_command(command)
