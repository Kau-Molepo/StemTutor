import firebase_admin
from typing import List, Optional
from fastapi import HTTPException
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate("B:/Documents/Projects/StemTutor/stemtutor-4cdc5-firebase-adminsdk-zfueo-a203f8c8a3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

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
    doc_ref = db.collection('qa_pairs').document()
    doc_ref.set({
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
