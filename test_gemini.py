import keyring
from google import genai
from PIL import Image
import PIL.PngImagePlugin


api_key = keyring.get_password("Breeze", "GEMINI_API_KEY")
print("API Key retrieved:", bool(api_key))
client = genai.Client(api_key=api_key)

try:
    img = Image.new('RGB', (100, 100))
    prompt = "Test"
    print("Sending to Gemini...")
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=[img, prompt]
    )
    print("Response:", response.text)
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
