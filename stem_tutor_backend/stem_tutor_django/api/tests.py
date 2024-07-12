import requests
import json
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.test import TestCase  # Import TestCase

BASE_URL = 'http://127.0.0.1:8000/api/'

# Authentication
def get_auth_token(username, password):
    url = f'{BASE_URL}token/'  # Use the correct token endpoint
    response = requests.post(url, data={'username': username, 'password': password})

    # Print full response for debugging
    print(f"\n[DEBUG] Token Request:")
    print(f"  URL: {url}")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.content}")

    if response.status_code == 200:
        return response.json()['access']
    elif response.status_code == 401:  # Handle Unauthorized error
        raise Exception(f"Authentication failed: Invalid credentials. Please check your username and password.")
    else:
        try:
            error_data = response.json()
            raise Exception(f"Authentication failed: {error_data}")
        except json.decoder.JSONDecodeError:
            raise Exception(f"Authentication failed with an unexpected error (status code {response.status_code})")

# Replace with your actual credentials
token = get_auth_token('kau', '12345678')
headers = {'Authorization': f'Bearer {token}'}

# Helper Functions
def get_or_create_subject(subject_name):
    response = requests.get(f'{BASE_URL}subjects/', params={'name': subject_name}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]['id']
    # Subject doesn't exist, create it
    response = requests.post(f'{BASE_URL}subjects/', headers=headers, json={'name': subject_name})
    response.raise_for_status()  # Raise exception for HTTP errors (4xx, 5xx)
    return response.json()['id']

def create_question(text, subject_id, difficulty):
    response = requests.post(f'{BASE_URL}questions/', headers=headers, json={
        'text': text,
        'subject': subject_id,  # Pass subject ID, not a dictionary
        'difficulty': difficulty
    })
    response.raise_for_status() 
    return response.json()['id']

def create_answer(question_id, user_id, text):
    response = requests.post(f'{BASE_URL}answers/', headers=headers, json={
        'question': question_id,
        'user': user_id,
        'text': text
    })
    response.raise_for_status()
    return response.json()

# Test Cases
try:
    print("\n--- User Tests ---")
    # Create User
    response = requests.post(f'{BASE_URL}users/', data={
        'username': 'newuser',
        'password': 'password123',
        'grade_level': '11',
        'learning_style': 'Auditory'
    })
    print("Create User:", response.json() if response.status_code == 201 else response.text)
    user_id = response.json()['id']

    # Get User
    response = requests.get(f'{BASE_URL}users/{user_id}/', headers=headers)
    print("Get User:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Subject Tests ---")
    # Subject
    subject_id = get_or_create_subject("Mathematics")
    subject_id2 = get_or_create_subject("Physics")

    # Get Subjects
    response = requests.get(f'{BASE_URL}subjects/', headers=headers)
    print("Get Subjects:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Question Tests ---")
    # Question
    question_id = create_question("What is 2+2?", subject_id, "Easy")
    question_id2 = create_question("What is Newton's first law of motion?", subject_id2, "Medium")

    # Get Questions
    response = requests.get(f'{BASE_URL}questions/', headers=headers)
    print("Get Questions:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Answer Tests ---")
    # Answer
    answer_data = create_answer(question_id, user_id, "4")
    print("Create Answer:", answer_data)

    # Get Answers for a Question
    response = requests.get(f'{BASE_URL}questions/{question_id}/answers/', headers=headers)
    print("Get Answers for Question:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Learning Path Tests ---")
    # Create Learning Path
    response = requests.post(f'{BASE_URL}learning_paths/', headers=headers, json={
        'user': user_id,
        'subjects': [subject_id, subject_id2],
        'current_level': 'Beginner'
    })
    print("Create Learning Path:", response.json() if response.status_code == 201 else response.text)

    # Get Learning Paths
    response = requests.get(f'{BASE_URL}learning_paths/', headers=headers)
    print("Get Learning Paths:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Progress Tests ---")
    # Assuming the 'Progress' viewset is set up, you would test creating progress objects here.

    print("\n--- Project Tests ---")
    # Create Project
    response = requests.post(f'{BASE_URL}projects/', headers=headers, json={
        'title': 'Math Project',
        'description': 'A project about algebra',
        'subject': subject_id,
        'difficulty': 'Medium',
        'resources': '[https://www.example.com/math-resources](https://www.example.com/math-resources)'
    })
    print("Create Project:", response.json() if response.status_code == 201 else response.text)

    # Get Projects
    response = requests.get(f'{BASE_URL}projects/', headers=headers)
    print("Get Projects:", response.json() if response.status_code == 200 else response.text)

except requests.exceptions.RequestException as e:
    print(f"API Error: {e}")
except Exception as e:
    print(f"Other Error: {e}")
