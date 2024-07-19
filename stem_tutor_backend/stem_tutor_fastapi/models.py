from typing import List, Optional
from pydantic import BaseModel, EmailStr, constr


class User(BaseModel):
    email: EmailStr
    password: constr(min_length=6)
    grade_level: int
    subjects: List[str]

class Question(BaseModel):
    text: constr(min_length=1, max_length=1000)  # Limit the length of the question
    subject: str
    grade_level: int

class Feedback(BaseModel):
    question_id: str
    helpful: bool

class UpdateProfile(BaseModel):
    grade_level: int
    subjects: List[str]
