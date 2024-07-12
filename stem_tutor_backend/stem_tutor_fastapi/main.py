from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
import os
import google.generativeai as genai

# Manually set the API key to ensure it's correctly loaded
api_key = os.environ.get('GEMINI_API_KEY')
if api_key is None:
    raise ValueError("API key not found. Make sure it is set in the environment variables.")
genai.configure(api_key=api_key)
genai.sets('gemini-pro')
genai.sets('gemini-pro-vision')

app = FastAPI()

# CORS Configuration (Allow requests from your Flutter frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration (Load from environment variables or a config file)
DJANGO_API_BASE_URL = "http://your-django-api-url/api/" 
GEMINI_API_URL = "https://api.gemini.com/v1/completions"  # Replace with actual Gemini API URL
GEMINI_API_KEY = api_key  # Add your Gemini API key


# Pydantic Models
class Question(BaseModel):
    question_text: str
    student_id: int

class GeminiResponse(BaseModel):
    answer: str
    explanation: str = Field(None, description="Optional explanation from Gemini")

class FinalResponse(BaseModel):
    question: Question
    answer: GeminiResponse
    additional_context: dict = Field(None, description="Optional context from Django")


# Helper Functions
async def get_gemini_answer(question_text: str):
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": question_text,
        "max_tokens": 2048, # Adjust as needed
    }
    response = requests.post(GEMINI_API_URL, headers=headers, json=data)
    response.raise_for_status()  # Raise an exception for bad responses
    return response.json()['choices'][0]['text']

async def get_student_context(student_id: int):
    try:
        response = requests.get(f"{DJANGO_API_BASE_URL}students/{student_id}/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Error fetching student context from Django API")

# Main Endpoint
@app.post("/ask_question/")
async def ask_question(question: Question):
    try:
        gemini_answer = await get_gemini_answer(question.question_text)
        student_context = await get_student_context(question.student_id) if question.student_id else None

        return FinalResponse(
            question=question,
            answer=GeminiResponse(answer=gemini_answer),  # Use the GeminiResponse model
            additional_context=student_context
        )

    except HTTPException as e:
        raise e  # Re-raise HTTPExceptions to pass them to the client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {e}")
