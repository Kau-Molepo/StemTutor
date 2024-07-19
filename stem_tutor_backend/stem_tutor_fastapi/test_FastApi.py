import requests

BASE_URL = "http://127.0.0.1:8000"

# User data for registration and login
user_data = {
    "email": "testuser@example.com",
    "password": "testpassword",
    "grade_level": 10,
    "subjects": ["math", "science"]
}

# Register user
response = requests.post(f"{BASE_URL}/register/", json=user_data)
print("Register User:", response.text)

# Login to get the token
login_data = {
    "username": user_data['email'],
    "password": user_data['password']
}
response = requests.post(f"{BASE_URL}/token", data=login_data)
token = response.json().get("access_token")
print("Login:", response.text)

# Authorization header
headers = {
    "Authorization": f"Bearer {token}"
}

# Ask a question
question_data = {
    "text": "What is the Pythagorean theorem?",
    "subject": "math",
    "grade_level": 10
}
response = requests.post(f"{BASE_URL}/ask_question/", json=question_data, headers=headers)
print("Ask Question Response Code:", response.status_code)
print("Ask Question Raw Response:", response.text)

# Get personalized questions
user_id = response.json().get("qa_id")  # Assuming the response contains the user_id
response = requests.get(f"{BASE_URL}/personalized_questions/{user_id}", headers=headers)
print("Personalized Questions:", response.json())

# Submit feedback
feedback_data = {
    "question_id": user_id,  # Using the same qa_id for feedback
    "helpful": True
}
response = requests.post(f"{BASE_URL}/feedback/", json=feedback_data, headers=headers)
print("Submit Feedback:", response.json())

# Get user progress
response = requests.get(f"{BASE_URL}/user_progress/", headers=headers)
print("User Progress:", response.json())

# Update profile
profile_data = {
    "grade_level": 11,
    "subjects": ["math", "science", "english"]
}
response = requests.put(f"{BASE_URL}/profile/", json=profile_data, headers=headers)
print("Update Profile:", response.json())

# Get question history
response = requests.get(f"{BASE_URL}/question_history/", headers=headers)
try:
    print("Question History:", response.json())
except requests.exceptions.JSONDecodeError:
    print("Question History: Failed to decode JSON response")

# Get leaderboard
response = requests.get(f"{BASE_URL}/leaderboard/")
print("Leaderboard:", response.json())

# Get daily challenge
response = requests.get(f"{BASE_URL}/daily_challenge/")
print("Daily Challenge:", response.json())
