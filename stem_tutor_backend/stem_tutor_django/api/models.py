from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField

class User(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True)
    learning_style = models.CharField(max_length=20, blank=True)  # Visual, Auditory, Kinesthetic, etc.
    grade_level = models.CharField(max_length=50, blank=True)    # K, 1, 2, ... , Undergraduate, Postgraduate, etc.
    interests = models.ManyToManyField('Subject', related_name='interested_users', blank=True)  

class Subject(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    text = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    difficulty = models.CharField(max_length=20, choices=[
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard')
    ])
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)
    learning_objectives = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    tags = ArrayField(models.CharField(max_length=50), blank=True, default=list)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class LearningPath(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_path')
    subjects = models.ManyToManyField(Subject, related_name='learning_paths')
    current_level = models.CharField(max_length=50, default='Beginner') 

class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='projects')
    difficulty = models.CharField(max_length=20, choices=[
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard')
    ])
    resources = models.TextField(blank=True)
