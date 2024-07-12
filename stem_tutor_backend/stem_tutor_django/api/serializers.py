from rest_framework import serializers
from .models import User, Subject, Question, Answer, LearningPath, Progress, Project

class UserSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'profile_picture', 'learning_style', 'grade_level', 'interests']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)  

    class Meta:
        model = Question
        fields = '__all__'


class AnswerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = '__all__'  

class LearningPathSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Use PrimaryKeyRelatedField for user
    subjects = SubjectSerializer(many=True)

    class Meta:
        model = LearningPath
        fields = '__all__'

class ProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    learning_path = LearningPathSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = Progress
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer()

    class Meta:
        model = Project
        fields = '__all__'
