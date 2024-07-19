from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import requests
import jwt

# Load environment variables
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate("B:/Documents/Projects/StemTutor/stemtutor-4cdc5-firebase-adminsdk-zfueo-a203f8c8a3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create the model
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

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Authentication Setup
SECRET_KEY = "your-secret-key" 
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired", headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = auth.get_user(user_id)
    if user is None:
        raise credentials_exception
    return user

def verify_password(email, password):
    api_key = os.getenv("FIREBASE_API_KEY")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        return None

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

class UpdateProfile(BaseModel):
    grade_level: int
    subjects: List[str]

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
    doc_ref = db.collection('qa_pairs').document()  # Create a document reference
    doc_ref.set({
        'user_id': user_id,
        'question': question,
        'answer': answer,
        'subject': subject,
        'grade_level': grade_level,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return doc_ref.id  # Return the document ID

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
    try:
        user_id = create_firebase_user(user.email, user.password)
        store_user_data(user_id, user.grade_level, user.subjects)
        return {"message": "User registered successfully", "user_id": user_id}
    except HTTPException as e:
        if "EMAIL_EXISTS" in str(e.detail):
            return {"message": "User already exists", "user_id": None}
        raise e

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = verify_password(form_data.username, form_data.password)
        if user is None:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": user["localId"]})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error logging in: {str(e)}")

@app.post("/ask_question/")
async def ask_question(question: Question, current_user: User = Depends(get_current_user)):
    try:
        # Create the prompt for the model
        prompt = f"Question: {question.text}\nProvide a concise answer and a brief explanation."

        # Generate the content using the `generate_content` method
        response = model.generate_content(
            contents={"parts": [{"text": prompt}]},  # Adjusted to match the expected format
            generation_config=generation_config,
            stream=False
        )

        # Extract the generated content from the response
        if response:
            answer = response.text
            
            # Store the question and answer in Firestore
            qa_id = store_question_answer(current_user.uid, question.text, answer, question.subject, question.grade_level)

            return {"qa_id": qa_id, "question": question.text, "answer": answer}
        else:
            raise HTTPException(status_code=500, detail="Model did not return a valid response")
    except AttributeError as e:
        print(f"Error: {e}")  # Log the specific error
        raise HTTPException(status_code=500, detail="Error processing question: missing user ID")
    except Exception as e: 
        print(f"Error in ask_question endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.get("/personalized_questions/{user_id}")
async def personalized_questions(user_id: str, current_user: User = Depends(get_current_user)):
    if user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Not authorized to view these questions")
    user_data = db.collection('users').document(user_id).get().to_dict()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    questions = db.collection('qa_pairs')\
        .where('grade_level', '==', user_data['grade_level'])\
        .where('subject', 'in', user_data['subjects'])\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(10)\
        .get()
    
    return [q.to_dict() for q in questions]

@app.post("/feedback/")
async def submit_feedback(feedback: Feedback, current_user: User = Depends(get_current_user)):
    if not isinstance(feedback.question_id, str) or feedback.question_id is None:
        raise HTTPException(status_code=400, detail="Input should be a valid string")
    try:
        db.collection('feedback').add({
            'user_id': current_user.uid,
            'question_id': feedback.question_id,
            'helpful': feedback.helpful,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@app.get("/user_progress/")
async def user_progress(current_user: User = Depends(get_current_user)):
    progress = get_user_progress(current_user.uid)
    return progress

@app.put("/profile/")
async def update_profile(profile: UpdateProfile, current_user: User = Depends(get_current_user)):
    try:
        db.collection('users').document(current_user.uid).update({
            'grade_level': profile.grade_level,
            'subjects': profile.subjects
        })
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

@app.get("/question_history/")
async def question_history(current_user: User = Depends(get_current_user)):
    try:
        qa_pairs = db.collection('qa_pairs').where('user_id', '==', current_user.uid).get()
        history = [{'question': qa.to_dict().get('question', 'No question'), 'answer': qa.to_dict().get('answer', 'No answer')} for qa in qa_pairs]
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving question history: {str(e)}")


@app.get("/leaderboard/")
async def leaderboard():
    users = db.collection('users').get()
    leaderboard = []
    for user in users:
        user_data = user.to_dict()
        progress = get_user_progress(user.id)
        leaderboard.append({
            'user_id': user.id,
            'grade_level': user_data.get('grade_level'),
            'total_questions': progress['total_questions'],
            'subjects_covered': len(progress['subjects_covered'])  # Adjust to count
        })
    leaderboard.sort(key=lambda x: (x['total_questions'], x['subjects_covered']), reverse=True)
    return leaderboard


@app.get("/daily_challenge/")
async def daily_challenge():
    try:
        # Generate a daily challenge question based on a random subject and grade level
        import random
        subjects = ["math", "science", "english"]
        grade_levels = list(range(1, 13))
        subject = random.choice(subjects)
        grade_level = random.choice(grade_levels)
        
        question = "Solve for x: 2x + 3 = 7"  # This should be dynamically generated based on the subject and grade level
        response = model.generate_content(
            contents={"parts": [{"text": question}]},
            generation_config=generation_config,
            stream=False
        )
        
        # Extract the generated content from the response
        if response:
            answer = response.text
            return {"question": question, "answer": answer}
        else:
            raise HTTPException(status_code=500, detail="Model did not return a valid response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing daily challenge: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
