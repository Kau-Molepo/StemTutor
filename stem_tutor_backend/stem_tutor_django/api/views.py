from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (UserSerializer, SubjectSerializer, QuestionSerializer, 
                          AnswerSerializer, LearningPathSerializer, ProgressSerializer, ProjectSerializer)
from .models import User, Subject, Question, Answer, LearningPath, Progress, Project
from rest_framework.views import exception_handler

import requests
import os
import google.generativeai as genai

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://api.gemini.com/v1/completions'

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'])
    def create_learning_path(self, request, pk=None):
        user = self.get_object()
        serializer = LearningPathSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def get_learning_path(self, request, pk=None):
        user = self.get_object()
        learning_path = user.learning_path  # Access the related learning path directly
        if learning_path:
            serializer = LearningPathSerializer(learning_path)
            return Response(serializer.data)
        return Response({"error": "Learning path not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'])
    def update_learning_path(self, request, pk=None):
        user = self.get_object()
        learning_path = user.learning_path
        if learning_path:
            serializer = LearningPathSerializer(learning_path, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Learning path not found"}, status=status.HTTP_404_NOT_FOUND)

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def by_subject(self, request):
        subject_id = request.query_params.get('subject_id')
        if not subject_id:
            return Response({"error": "Please provide a subject_id"}, status=status.HTTP_400_BAD_REQUEST)
        questions = Question.objects.filter(subject_id=subject_id)
        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def answers(self, request, pk=None):
        question = self.get_object()
        answers = question.answers.all()
        serializer = AnswerSerializer(answers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_next_question(self, request, pk=None):
        user = request.user
        learning_path = LearningPath.objects.filter(user=user).first()  # Get the user's learning path
        if learning_path:
            current_level = learning_path.current_level
            questions = Question.objects.filter(
                subject__in=learning_path.subjects.all(),
                difficulty=current_level
            ).exclude(
                id__in=Progress.objects.filter(
                    user=user, learning_path=learning_path, is_correct=True
                ).values_list('question_id', flat=True)
            )
            if questions.exists():
                next_question = questions.order_by('?').first()  # Get random question
                return Response(QuestionSerializer(next_question).data)
            else:
                return Response({"error": "No new questions found for the current level"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "No learning path found for the user"}, status=status.HTTP_404_NOT_FOUND)

class AnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        answer = serializer.save(user=self.request.user)
        question = answer.question

        # Get/Generate Explanation (with caching)
        if not question.explanation:  # Only fetch if explanation doesn't exist
            prompt = f"Explain this {question.subject.name} concept in a way that is easy to understand: '{question.text}'"
            explanation = self.get_gemini_response(prompt)
            question.explanation = explanation
            question.save()

        # Get Feedback from Gemini
        feedback_prompt = (
            f"Evaluate this answer for the question '{question.text}' by a {answer.user.grade_level} "
            f"grade student with a {answer.user.learning_style} learning style: '{answer.text}'. "
            "Provide detailed feedback explaining why it is correct or incorrect, "
            "and suggest improvements or additional information if applicable."
        )
        feedback = self.get_gemini_response(feedback_prompt)

        # Analyze feedback (you'll need to implement this logic)
        is_correct = 'correct' in feedback.lower() or 'right' in feedback.lower()  

        answer.is_correct = is_correct
        answer.feedback = feedback
        answer.save()

    def get_gemini_response(self, prompt):
        headers = {'Authorization': f'Bearer {GEMINI_API_KEY}'}
        data = {'prompt': prompt, 'max_tokens': 300}
        try:
            response = requests.post(GEMINI_API_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get('choices', [{}])[0].get('text', '')
        except requests.RequestException as e:
            print(f"Error calling Gemini API: {e}")
            return "Error getting response from the AI. Please try again later."

class LearningPathViewSet(viewsets.ModelViewSet):
    queryset = LearningPath.objects.all()
    serializer_class = LearningPathSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ProgressViewSet(viewsets.ModelViewSet):
    queryset = Progress.objects.all()
    serializer_class = ProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    

# Error handler to provide a custom response for 404 errors
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # If no response or not a JSON response, create a custom 404 response
    if response is None or not isinstance(response.data, dict):
        response = Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    return response
