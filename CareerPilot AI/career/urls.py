from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("workspace/", views.workspace, name="workspace"),
    path("workspace/<str:section>/", views.workspace, name="workspace_section"),
    path("analyze/", views.analyze_resume, name="analyze_resume"),
    path("github/", views.analyze_github, name="analyze_github"),
    path("roadmap/", views.generate_roadmap, name="generate_roadmap"),
    path("roadmap/tasks/<int:task_id>/toggle/", views.toggle_roadmap_task, name="toggle_roadmap_task"),
    path("interview/start/", views.start_interview, name="start_interview"),
    path("interview/roles/", views.interview_roles, name="interview_roles"),
    path("interview/history/", views.interview_history, name="interview_history"),
    path("interview/<int:session_id>/", views.interview_result, name="interview_result"),
    path("interview/<int:session_id>/answer/", views.submit_interview_answer, name="submit_interview_answer"),
]
