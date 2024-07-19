from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from models import User, Question, Feedback, UpdateProfile
from database import *
from auth import *
from ai import generate_answer

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        prompt = f"Question: {question.text}\nProvide a concise answer and a brief explanation."
        answer = generate_answer(prompt)
        if answer:
            qa_id = store_question_answer(current_user.uid, question.text, answer, question.subject, question.grade_level)
            return {"qa_id": qa_id, "question": question.text, "answer": answer, "user_id": current_user.uid}
        else:
            raise HTTPException(status_code=500, detail="Model did not return a valid response")
    except AttributeError as e:
        print(f"Error: {e}")
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
    try:
        progress = get_user_progress(current_user.uid)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user progress: {str(e)}")

@app.put("/update_profile/")
async def update_profile(profile: UpdateProfile, current_user: User = Depends(get_current_user)):
    try:
        db.collection('users').document(current_user.uid).update({
            'grade_level': profile.grade_level,
            'subjects': profile.subjects
        })
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")
    
# @app.put("/profile/")
# async def update_profile(profile: UpdateProfile, current_user: User = Depends(get_current_user)):
#     try:
#         db.collection('users').document(current_user.uid).update({
#             'grade_level': profile.grade_level,
#             'subjects': profile.subjects
#         })
#         return {"message": "Profile updated successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

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
        response = generate_answer(question)
        
        if response:
            answer = response
            return {"question": question, "answer": answer}
        else:
            raise HTTPException(status_code=500, detail="Model did not return a valid response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing daily challenge: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
