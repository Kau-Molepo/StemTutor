import requests
import json

BASE_URL = 'http://127.0.0.1:8000/api/'

# Authentication (If applicable)
def get_auth_token(username, password):
    url = f'{BASE_URL}token/'
    response = requests.post(url, data={'username': username, 'password': password})
    
    print(f"\n[DEBUG] Token Request:")
    print(f"  URL: {url}")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.text}")  # Print raw content for debugging

    if response.status_code == 200:
        try:
            data = response.json()
            if 'access' in data:
                return data['access']
            else:
                raise Exception("Authentication response does not contain 'access' token.")
        except json.decoder.JSONDecodeError:
            raise Exception("Failed to parse authentication response as JSON.")
    elif response.status_code == 401:
        raise Exception("Authentication failed: Invalid credentials.")
    else:
        try:
            error_data = response.json()
            raise Exception(f"Authentication failed: {error_data}")
        except json.decoder.JSONDecodeError:
            raise Exception(f"Authentication failed with status code {response.status_code}")

# Replace with your actual credentials
token = get_auth_token('kau', '12345678')
headers = {'Authorization': f'Bearer {token}'}

# Helper Functions
def get_or_create_subject(headers, subject_name):
    response = requests.get(f'{BASE_URL}subjects/', params={'name': subject_name}, headers=headers)
    print(f"\n[DEBUG] Get or Create Subject - {subject_name}:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.text}")  # Print raw content for debugging

    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]  # Return full subject dictionary if subject exists
        else:
            response = requests.post(f'{BASE_URL}subjects/', headers=headers, json={'name': subject_name})
            print(f"\n[DEBUG] Create Subject - {subject_name}:")
            print(f"  Status Code: {response.status_code}")
            print(f"  Response Content: {response.text}")  # Print raw content for debugging

            if response.status_code == 201:
                return response.json()  # Return full subject dictionary of newly created subject
            else:
                raise Exception(f"Failed to create subject: {response.json()}")
    else:
        raise Exception(f"Failed to retrieve subjects: {response.text}")

def create_question(text, subject, difficulty):  # Removed subject_id argument
    print(f"\n[DEBUG] Create Question - {text}:")
    print(f"  Subject: {subject}")  # Print subject dictionary for debugging
    response = requests.post(f'{BASE_URL}questions/', headers=headers, json={
        'text': text,
        'subject': subject,  # Subject is already a dictionary with id
        'difficulty': difficulty
    })
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.text}")  # Print raw content for debugging

    if response.status_code == 201:
        return response.json()  # Return full question dictionary
    else:
        raise Exception(f"Failed to create question: {response.json()}")

def create_answer(question, user, text):
    response = requests.post(f'{BASE_URL}answers/', headers=headers, json={
        'question': question['id'], 
        'user': user['id'],
        'text': text
    })
    print(f"\n[DEBUG] Create Answer - {text}:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Content: {response.text}")  # Print raw content for debugging

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create answer: {response.json()}")

# Test Cases
try:
    print("\n--- User Tests ---")
    # Get Authentication Token
    response = requests.post(f'{BASE_URL}token/', data={'username': 'kau', 'password': '12345678'})
    token = response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}

    # List of interests as PKs (assuming 'AI' interest has PK 1)
    interests = [1]  # Adjust based on actual PKs in your database

    # Create User
    response = requests.post(f'{BASE_URL}users/', headers=headers, json={
        'username': 'newuser',
        'password': 'password123',
        'grade_level': '11',
        'learning_style': 'Auditory',
        'interests': interests  # Corrected to use list of PKs
    })
    print("Create User:", response.json() if response.status_code == 201 else response.text)

    user = None  # Initialize user variable outside the if block
    if response.status_code == 201:
        user = response.json()  # Store full user dictionary
    elif response.status_code == 400 and "username" in response.json():
        print("Create User: User with this username already exists.")
        # Retrieve existing user
        response = requests.get(f'{BASE_URL}users/?username=newuser', headers=headers)
        if response.status_code == 200:
            user = response.json()[0]
            print("Existing User ID:", user['id'])
        else:
            raise Exception("Failed to retrieve existing user.")
    else:
        print("Create User Error:", response.text)

    # Get User
    if user is not None:  # Check if user exists before trying to get it
        response = requests.get(f'{BASE_URL}users/{user["id"]}/', headers=headers)
        print("Get User:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Subject Tests ---")
    subject_math = get_or_create_subject(headers, "Mathematics")
    subject_physics = get_or_create_subject(headers, "Physics")

    response = requests.get(f'{BASE_URL}subjects/', headers=headers)
    print("Get Subjects:", response.json() if response.status_code == 200 else response.text)

    print("\n--- Question Tests ---")
    # Create Question 1
    question_math = create_question("What is 2+2?", subject_math, "Easy")
    response = requests.get(f'{BASE_URL}questions/{question_math["id"]}/', headers=headers)
    print(response.content)  # Print raw content
    print("Get Question:", response.json() if response.status_code == 200 else response.text)

    # Create Question 2
    question_physics = create_question("What is Newton's first law of motion?", subject_physics, "Medium")
    response = requests.get(f'{BASE_URL}questions/{question_physics["id"]}/', headers=headers)
    print("Get Question:", response.json() if response.status_code == 200 else response.text)

    response = requests.get(f'{BASE_URL}questions/', headers=headers)
    print("Get Questions:", response.json() if response.status_code == 200 else response.text)

    questions = response.json()
    print(questions)
    
    print("\n--- Answer Tests ---")
    # Answer
    answer_data = create_answer(question_math, user, "4")
    print("Create Answer:", answer_data)
        
    # Get Answers for a Question
    response = requests.get(f'{BASE_URL}questions/{question_math["id"]}/answers/', headers=headers)
    print("Get Answers for Question:", response.json() if response.status_code == 200 else response.text)
    
    print("\n--- Learning Path Tests ---")
    response = requests.post(f'{BASE_URL}learning_paths/', headers=headers, json={
        'user': user['id'],
        'subjects': [subject_math['id'], subject_physics['id']],
        'current_level': 'Beginner'
    })
    print("Create Learning Path:", response.json() if response.status_code == 201 else response.text)
    
    response = requests.get(f'{BASE_URL}learning_paths/', headers=headers)
    print("Get Learning Paths:", response.json() if response.status_code == 200 else response.text)
    
    print("\n--- Progress Tests ---")
    # Assuming the 'Progress' viewset is set up, you would test creating progress objects here.

    print("\n--- Project Tests ---")
    response = requests.post(f'{BASE_URL}projects/', headers=headers, json={
        'title': 'Math Project',
        'description': 'A project about algebra',
        'subject': subject_math['id'],
        'difficulty': 'Medium',
        'resources': 'https://www.example.com/math-resources' 
    })
    print("Create Project:", response.json() if response.status_code == 201 else response.text)

    response = requests.get(f'{BASE_URL}projects/', headers=headers)
    print("Get Projects:", response.json() if response.status_code == 200 else response.text)
    
except Exception as e:
    print(f"Error: {e}")
