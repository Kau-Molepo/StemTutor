import requests

BASE_URL = "http://127.0.0.1:8000"

# User data for registration and login
user_data = {
    "email": "testuser@example.com",
    "password": "testpassword",
    "grade_level": 10,
    "subjects": ["math", "science"]
}

def score_response(response, expected_status=200):
    if response.status_code == expected_status:
        try:
            response.json()  # Try to parse JSON to ensure it's a valid JSON response
            return "Success"
        except requests.exceptions.JSONDecodeError:
            return "Failed - Invalid JSON"
    else:
        return f"Failed - Status Code: {response.status_code}"

results = {}
total_tests = 10
success_count = 0

# Register user
response = requests.post(f"{BASE_URL}/register/", json=user_data)
results["Register User"] = score_response(response)
if results["Register User"] == "Success":
    success_count += 1

# Login to get the token
login_data = {
    "username": user_data['email'],
    "password": user_data['password']
}
response = requests.post(f"{BASE_URL}/token", data=login_data)
token = response.json().get("access_token")
results["Login"] = score_response(response)
if results["Login"] == "Success":
    success_count += 1

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
ask_question_response = response.json()
results["Ask Question"] = score_response(response)
if results["Ask Question"] == "Success":
    success_count += 1
    # Extract user_id and qa_id from response
    user_id = ask_question_response.get("user_id")
    qa_id = ask_question_response.get("qa_id")
else:
    user_id = None
    qa_id = None

# Get personalized questions
if user_id:
    response = requests.get(f"{BASE_URL}/personalized_questions/{user_id}", headers=headers)
    results["Personalized Questions"] = score_response(response)
    if results["Personalized Questions"] == "Success":
        success_count += 1
else:
    results["Personalized Questions"] = "Failed - No User ID from Ask Question"

# Submit feedback
if qa_id:
    feedback_data = {
        "question_id": qa_id,
        "helpful": True
    }
    response = requests.post(f"{BASE_URL}/feedback/", json=feedback_data, headers=headers)
    results["Submit Feedback"] = score_response(response)
    if results["Submit Feedback"] == "Success":
        success_count += 1
else:
    results["Submit Feedback"] = "Failed - No QA ID from Ask Question"

# Get user progress
response = requests.get(f"{BASE_URL}/user_progress/", headers=headers)
results["User Progress"] = score_response(response)
if results["User Progress"] == "Success":
    success_count += 1

# Update profile
profile_data = {
    "grade_level": 11,
    "subjects": ["math", "science", "english"]
}
response = requests.put(f"{BASE_URL}/update_profile/", json=profile_data, headers=headers)
results["Update Profile"] = score_response(response)
if results["Update Profile"] == "Success":
    success_count += 1

# Get question history
response = requests.get(f"{BASE_URL}/question_history/", headers=headers)
results["Question History"] = score_response(response)
if results["Question History"] == "Success":
    success_count += 1

# Get leaderboard
response = requests.get(f"{BASE_URL}/leaderboard/")
results["Leaderboard"] = score_response(response)
if results["Leaderboard"] == "Success":
    success_count += 1

# Get daily challenge
response = requests.get(f"{BASE_URL}/daily_challenge/")
results["Daily Challenge"] = score_response(response)
if results["Daily Challenge"] == "Success":
    success_count += 1

# Calculate overall score
overall_score = (success_count / total_tests) * 100

# Display results and overall score
print("\nTest Results:")
for test, result in results.items():
    print(f"{test}: {result}")

print(f"\nOverall Score: {overall_score:.2f}%")
