import os
import mss
import pyautogui
import speech_recognition as sr
import pyttsx3
import json
from PIL import Image
import PIL.PngImagePlugin
import multiprocessing
import keyring
import requests
import base64

from google import genai
from google.genai import types
import pytesseract

def _tts_worker(text):
    import asyncio
    import edge_tts
    import os
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    import pygame
    
    # Use a high-quality Indian English voice
    voice = "en-IN-NeerjaNeural"
    output_file = "temp_speech.mp3"
    
    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
    asyncio.run(generate())
    
    # Play MP3 in the worker process
    pygame.mixer.init()
    pygame.mixer.music.load(output_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()
    try:
        os.remove(output_file)
    except:
        pass

class BreezeAgent:
    def __init__(self, ui_window):
        self.ui = ui_window
        self.tts_process = None
        self.action_count = 0
        self.last_ocr_data = None
        self.last_ocr_time = 0
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
        print("process_command started")
        self.reset_action_limit()
        
        # PREFLIGHT ROUTER
        if self.preflight_router(command):
            return

        if not self.client:
            print("No Gemini Client found")
            self.ui.show_error("GEMINI_API_KEY not found in Keyring!")
            self.speak("API Key not found.")
            return

        print("Capturing screen...")
        try:
            img_path = self.capture_screen()
            img = Image.open(img_path)
            print(f"Screen captured: {img_path}")
        except Exception as e:
            print(f"Error capturing screen: {e}")
            self.ui.show_error(f"Screen capture failed: {e}")
            return

        # Local OCR pass for fast simple clicks with Caching
        if command.lower().startswith("click"):
            target_text = command[5:].strip().lower()
            import time
            current_time = time.time()
            
            # Use Cache if within 5 seconds
            if self.last_ocr_data and current_time - self.last_ocr_time < 5.0:
                print("Using cached OCR UI Map...")
                ocr_data = self.last_ocr_data
            else:
                print("Running local OCR pass (Cache miss)...")
                try:
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    self.last_ocr_data = ocr_data
                    self.last_ocr_time = current_time
                except Exception as e:
                    print("OCR unavailable or failed:", e)
                    ocr_data = None
            
            if ocr_data:
                for i, word in enumerate(ocr_data['text']):
                    if word.strip().lower() == target_text:
                        print("OCR Match found, clicking!")
                        x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                        pyautogui.click(x + w//2, y + h//2)
                        return
                print("OCR pass found no match, falling back to Gemini.")

        print("Preparing Gemini prompt...")

        prompt = f"""
        You are Breeze, an AI desktop assistant. The user has given this command: "{command}".
        You have a screenshot of the user's screen.
        If the command implies finding an element to click or highlight, provide the bounding box in the format:
        [ymin, xmin, ymax, xmax] where values are between 0 and 1000.
        If the command implies typing text, use action "type" and provide the text.
        If the command implies pressing a keyboard shortcut, use action "hotkey" and provide the keys (e.g. ["win"], ["enter"]).
        If the command implies scrolling, use action "scroll" and provide amount (positive for up, negative for down).
        If the command asks to open an application or program, use action "open_app" and provide the "app_name".
        If the command asks to message someone on WhatsApp, use action "whatsapp" and provide the "contact" name and "text" to send.
        If the command asks to play a song on Spotify, use action "play_spotify" and provide the "song" name.
        If the command asks to search the web, use action "search_web" and provide the "query".
        If the user asks a general question, just reply with text.
        Respond with a JSON ARRAY of action objects ONLY, for example:
        [
            {{
                "action": "click" | "highlight" | "reply" | "type" | "scroll" | "hotkey" | "open_app" | "whatsapp" | "play_spotify" | "search_web",
                "box_2d": [ymin, xmin, ymax, xmax],
                "text": "Your reply or text to type",
                "amount": 500,
                "keys": ["win", "d"],
                "app_name": "camera",
                "contact": "John"
            }}
        ]
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            results = json.loads(response.text)
            print("AI Response:", results)
            
            if not isinstance(results, list):
                results = [results]
                
            for result in results:
                if not self.execute_action(result):
                    break
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            self.fallback_to_ollama(command, img_path)

    def fallback_to_ollama(self, command, img_path):
        print("Falling back to local Ollama (llava)...")
        self.ui.show_error("Gemini API Error. Falling back to local Ollama...")
        
        prompt = f"""
        You are Breeze, an AI desktop assistant. The user has given this command: "{command}".
        You have a screenshot of the user's screen.
        If the command implies finding an element to click or highlight, provide the bounding box in the format:
        [ymin, xmin, ymax, xmax] where values are between 0 and 1000.
        If the command implies typing text, use action "type" and provide the text.
        If the command implies pressing a keyboard shortcut, use action "hotkey" and provide the keys (e.g. ["win"], ["enter"]).
        If the command implies scrolling, use action "scroll" and provide amount (positive for up, negative for down).
        If the command asks to open an application or program, use action "open_app" and provide the "app_name".
        If the command asks to message someone on WhatsApp, use action "whatsapp" and provide the "contact" name and "text" to send.
        If the command asks to play a song on Spotify, use action "play_spotify" and provide the "song" name.
        If the command asks to search the web, use action "search_web" and provide the "query".
        If the user asks a general question, just reply with text.
        Respond with a JSON ARRAY of action objects ONLY, for example:
        [
            {{
                "action": "click" | "highlight" | "reply" | "type" | "scroll" | "hotkey" | "open_app" | "whatsapp" | "play_spotify" | "search_web",
                "box_2d": [ymin, xmin, ymax, xmax],
                "text": "Your reply or text to type",
                "amount": 500,
                "keys": ["win", "d"],
                "app_name": "camera",
                "contact": "John"
            }}
        ]
        """
        
        try:
            with open(img_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            payload = {
                "model": "llava",
                "prompt": prompt,
                "images": [encoded_string],
                "stream": False,
                "format": "json"
            }
            
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = json.loads(data.get("response", "{}"))
            print("Ollama Response:", results)
            
            if not isinstance(results, list):
                results = [results]
                
            for result in results:
                if not self.execute_action(result):
                    break
        except Exception as e:
            print(f"Error falling back to Ollama: {e}")
            self.ui.show_error(f"Fallback to Ollama failed: {e}")


    def reset_action_limit(self):

        self.action_count = 0



    def handle_voice_command(self):
        command = self.listen()
        if command:
            print("Voice Command:", command)
            # Update UI from main thread in real app, here we just print
            self.process_command(command)

    def preflight_router(self, command):
        cmd_lower = command.lower().strip()
        
        if cmd_lower.startswith("open "):
            app_name = cmd_lower.replace("open ", "").strip()
            self.execute_action({"action": "open_app", "app_name": app_name})
            return True
            
        if cmd_lower.startswith("play "):
            if "youtube" in cmd_lower or "yt" in cmd_lower:
                song = cmd_lower.replace("play ", "").replace("on youtube music", "").replace("on youtube", "").replace("on yt music", "").replace("on yt", "").strip()
                self.execute_action({"action": "play_youtube", "song": song})
            else:
                song = cmd_lower.replace("play ", "").replace("on spotify", "").strip()
                self.execute_action({"action": "play_spotify", "song": song})
            return True
            
        if cmd_lower.startswith("search for ") or cmd_lower.startswith("google "):
            query = cmd_lower.replace("search for ", "").replace("google ", "").strip()
            self.execute_action({"action": "search_web", "query": query})
            return True
            
        return False

    def execute_action(self, result):
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
                if self.action_count >= 3:
                    self.ui.show_error("Action limit reached! Please confirm before continuing.")
                    return False
                self.action_count += 1
                cx = x + w // 2
                cy = y + h // 2
                pyautogui.click(cx, cy)
        
        elif action == "type" and text:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            import time
            time.sleep(0.2)
            pyautogui.typewrite(text, interval=0.01)
        
        elif action == "hotkey" and "keys" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            import time
            time.sleep(0.2)
            pyautogui.hotkey(*result["keys"])
        
        elif action == "scroll":
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            amount = result.get("amount", -500)
            pyautogui.scroll(amount)
            
        elif action == "open_app" and "app_name" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            app_name = result["app_name"]
            import time
            pyautogui.hotkey("win")
            time.sleep(0.2)
            pyautogui.typewrite(app_name, interval=0.01)
            time.sleep(0.2)
            pyautogui.hotkey("enter")
            
        elif action == "play_spotify" and "song" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            song = result["song"]
            import webbrowser
            import urllib.parse
            import time
            query = urllib.parse.quote(song)
            # Try to open desktop app directly via URI scheme
            webbrowser.open(f"spotify:search:{query}")
            time.sleep(1) # Fallback if user doesn't have it installed
            
        elif action == "play_youtube" and "song" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            song = result["song"]
            import webbrowser
            import urllib.parse
            import urllib.request
            import re
            query = urllib.parse.quote(song)
            try:
                # Scrape YouTube search results for the first video ID to autoplay
                html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={query}")
                video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
                if video_ids:
                    webbrowser.open(f"https://music.youtube.com/watch?v={video_ids[0]}")
                else:
                    webbrowser.open(f"https://music.youtube.com/search?q={query}")
            except Exception as e:
                print(f"Error fetching YT: {e}")
                webbrowser.open(f"https://music.youtube.com/search?q={query}")
            
        elif action == "search_web" and "query" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            query = result["query"]
            import time
            import webbrowser
            webbrowser.open(f"https://www.google.com/search?q={query}")

        elif action == "whatsapp" and "contact" in result and "text" in result:
            if self.action_count >= 3:
                self.ui.show_error("Action limit reached! Please confirm before continuing.")
                return False
            self.action_count += 1
            contact = result["contact"]
            msg = result["text"]
            import time
            pyautogui.hotkey("win")
            time.sleep(0.2)
            pyautogui.typewrite("whatsapp", interval=0.01)
            time.sleep(0.2)
            pyautogui.hotkey("enter")
            time.sleep(1.5)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.typewrite(contact, interval=0.01)
            time.sleep(0.5)
            pyautogui.hotkey("enter")
            time.sleep(0.5)
            pyautogui.typewrite(msg, interval=0.01)
            time.sleep(0.2)
            pyautogui.hotkey("enter")
            
        return True
