import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 65,
    "max_output_tokens": 150,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
)

def generate_answer(prompt: str):
    response = model.generate_content(
        contents={"parts": [{"text": prompt}]}, 
        generation_config=generation_config,
        stream=False
    )
    if response:
        return response.text
    else:
        return None
