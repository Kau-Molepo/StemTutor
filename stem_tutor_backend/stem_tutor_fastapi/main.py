from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()


# Initialize Firebase
cred = credentials.Certificate("B:\Documents\Projects\StemTutor\stemtutor-4cdc5-firebase-adminsdk-zfueo-a203f8c8a3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class User(BaseModel):
    email: str
    password: str
    grade_level: int
    subjects: List[str]

class Question(BaseModel):
    text: str
    subject: str
    grade_level: int

class Answer(BaseModel):
    text: str
    explanation: Optional[str] = None

class Feedback(BaseModel):
    question_id: str
    helpful: bool

# Helper functions
def create_firebase_user(email: str, password: str):
    try:
        user = auth.create_user(email=email, password=password)
        return user.uid
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")

def store_user_data(user_id: str, grade_level: int, subjects: List[str]):
    db.collection('users').document(user_id).set({
        'grade_level': grade_level,
        'subjects': subjects,
        'created_at': firestore.SERVER_TIMESTAMP
    })

def store_question_answer(user_id: str, question: str, answer: str, subject: str, grade_level: int):
    doc_ref = db.collection('qa_pairs').add({
        'user_id': user_id,
        'question': question,
        'answer': answer,
        'subject': subject,
        'grade_level': grade_level,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return doc_ref.id

def get_user_progress(user_id: str):
    qa_pairs = db.collection('qa_pairs').where('user_id', '==', user_id).get()
    subjects_covered = set()
    total_questions = 0
    for qa in qa_pairs:
        subjects_covered.add(qa.to_dict()['subject'])
        total_questions += 1
    return {
        'total_questions': total_questions,
        'subjects_covered': list(subjects_covered)
    }

# Endpoints
@app.post("/register/")
async def register_user(user: User):
    user_id = create_firebase_user(user.email, user.password)
    store_user_data(user_id, user.grade_level, user.subjects)
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/ask_question/")
async def ask_question(question: Question, user_id: str):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"Question: {question.text}\nProvide a concise answer and a brief explanation.")
        answer_parts = response.text.split('\n\n', 1)
        answer = Answer(text=answer_parts[0], explanation=answer_parts[1] if len(answer_parts) > 1 else None)
        
        qa_id = store_question_answer(user_id, question.text, answer.text, question.subject, question.grade_level)
        
        return {"answer": answer, "qa_id": qa_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/personalized_questions/{user_id}")
async def get_personalized_questions(user_id: str, limit: int = 10):
    user_data = db.collection('users').document(user_id).get().to_dict()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    questions = db.collection('qa_pairs')\
        .where('grade_level', '==', user_data['grade_level'])\
        .where('subject', 'in', user_data['subjects'])\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(limit)\
        .get()
    
    return [q.to_dict() for q in questions]

@app.post("/feedback/")
async def submit_feedback(feedback: Feedback):
    try:
        db.collection('qa_pairs').document(feedback.question_id).update({
            'feedback': feedback.helpful,
            'feedback_timestamp': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@app.get("/user_progress/{user_id}")
async def user_progress(user_id: str):
    progress = get_user_progress(user_id)
    return progress

@app.get("/leaderboard/")
async def get_leaderboard(limit: int = 10):
    users = db.collection('users').get()
    leaderboard = []
    for user in users:
        user_data = user.to_dict()
        progress = get_user_progress(user.id)
        leaderboard.append({
            'user_id': user.id,
            'grade_level': user_data['grade_level'],
            'total_questions': progress['total_questions'],
            'subjects_covered': len(progress['subjects_covered'])
        })
    
    leaderboard.sort(key=lambda x: x['total_questions'], reverse=True)
    return leaderboard[:limit]

@app.get("/daily_challenge/")
async def get_daily_challenge():
    today = datetime.now().strftime("%Y-%m-%d")
    challenge = db.collection('daily_challenges').document(today).get()
    if not challenge.exists:
        # Generate a new challenge if one doesn't exist for today
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Generate a challenging STEM question suitable for high school students.")
        challenge_data = {
            'question': response.text,
            'date': today
        }
        db.collection('daily_challenges').document(today).set(challenge_data)
        return challenge_data
    else:
        return challenge.to_dict()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.2", port=8000)
