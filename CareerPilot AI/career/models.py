from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_profile")
    target_role = models.CharField(max_length=80, blank=True)
    github_username = models.CharField(max_length=39, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Career profile for {self.user.username}"


class ResumeAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resume_analyses")
    role = models.CharField(max_length=80)
    resume_name = models.CharField(max_length=255)
    skills = models.JSONField(default=list)
    sections = models.JSONField(default=dict)
    match_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.role} resume analysis for {self.user.username}"


class GitHubAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="github_analyses")
    username = models.CharField(max_length=39)
    profile_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Roadmap(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmaps")
    resume_analysis = models.ForeignKey(ResumeAnalysis, on_delete=models.SET_NULL, null=True, blank=True, related_name="roadmaps")
    role = models.CharField(max_length=80)
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RoadmapTask(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="tasks")
    week = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=240)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["week", "position"]
        constraints = [
            models.UniqueConstraint(fields=["roadmap", "week", "position"], name="unique_roadmap_task_position")
        ]


class InterviewSession(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("completed", "Completed")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_sessions")
    role = models.CharField(max_length=80)
    attempt_number = models.PositiveIntegerField(default=1)
    questions = models.JSONField(default=list)
    question_index = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="active")
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class InterviewAnswer(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="answers")
    question_index = models.PositiveSmallIntegerField()
    question = models.TextField()
    answer = models.TextField()
    feedback = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_index"]
        constraints = [
            models.UniqueConstraint(fields=["session", "question_index"], name="unique_interview_answer_question")
        ]
