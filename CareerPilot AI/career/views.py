from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import (
    GitHubAnalysis,
    InterviewAnswer,
    InterviewSession,
    ResumeAnalysis,
    Roadmap,
    RoadmapTask,
    StudentProfile,
)
from .services.resume import detect_skills, extract_pdf_text, extract_resume_sections
from .services.matching import ROLE_PROFILES, analyze_match, recommend_alternative_roles
from .services.github import fetch_github_profile
from .services.ollama import create_roadmap
from .services.interview import evaluate_answer, generate_interview_questions, summarize_interview

WORKSPACE_SECTIONS = {"overview", "resume", "github", "match", "roadmap", "interview", "progress"}

def home(request):
    if request.user.is_authenticated:
        return redirect("workspace")
    return render(request, "career/home.html", {"roles": ROLE_PROFILES})


def signup(request):
    if request.user.is_authenticated:
        return redirect("workspace")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        StudentProfile.objects.get_or_create(user=user)
        login(request, user)
        return redirect("workspace")
    return render(request, "career/auth.html", {"form": form, "mode": "signup"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("workspace")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("workspace")
    return render(request, "career/auth.html", {"form": form, "mode": "login"})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def workspace(request, section="overview"):
    if section not in WORKSPACE_SECTIONS:
        section = "overview"
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    latest_analysis = request.user.resume_analyses.first()
    latest_github = request.user.github_analyses.first()
    latest_roadmap = request.user.roadmaps.first()
    selected_session_id = request.GET.get("session")
    if selected_session_id:
        latest_interview = request.user.interview_sessions.filter(pk=selected_session_id).first()
    else:
        latest_interview = request.user.interview_sessions.filter(status="active").first()
        if latest_interview is None:
            latest_interview = request.user.interview_sessions.first()
    resume_history = request.user.resume_analyses.all()[:5]
    interview_history = request.user.interview_sessions.all()[:5]
    requested_role = request.GET.get("role", "").strip()
    roadmap_role = latest_roadmap.role if latest_roadmap and latest_roadmap.role in ROLE_PROFILES else ""
    default_role = roadmap_role if section == "roadmap" and roadmap_role else (latest_analysis.role if latest_analysis else "")
    invalid_role = bool(requested_role) and requested_role not in ROLE_PROFILES
    selected_role = None if invalid_role else (requested_role or default_role)
    result = analyze_match(
        latest_analysis.skills,
        selected_role,
        latest_github.profile_data.get("portfolio_skills", []) if latest_github else [],
    ) if latest_analysis and selected_role else None
    if result:
        result = {**result, "resume_name": latest_analysis.resume_name, "sections": latest_analysis.sections}
    github = latest_github.profile_data if latest_github else None
    roadmap = latest_roadmap.content if latest_roadmap else None
    tasks = latest_roadmap.tasks.all() if latest_roadmap else []
    roadmap_weeks = [
        {**week, "number": week_number, "items": [task for task in tasks if task.week == week_number]}
        for week_number, week in enumerate(roadmap.get("weeks", []) if roadmap else [], start=1)
    ]
    answers = latest_interview.answers.all() if latest_interview else []
    total_tasks = len(tasks)
    completed_tasks = latest_roadmap.tasks.filter(completed=True).count() if latest_roadmap else 0
    completed_interviews = request.user.interview_sessions.filter(status="completed")
    completed_interview = completed_interviews.first()
    completed_scores = [item.summary.get("score", 0) for item in completed_interviews if isinstance(item.summary.get("score"), (int, float))]
    match_data = result or {}
    alternatives = recommend_alternative_roles(
        latest_analysis.skills,
        selected_role or latest_analysis.role,
        latest_github.profile_data.get("portfolio_skills", []) if latest_github else [],
    ) if latest_analysis else {"ready": [], "enhancement": []}
    return render(request, "career/workspace.html", {
        "roles": ROLE_PROFILES,
        "section": section,
        "profile": profile,
        "result": result,
        "alternatives": alternatives,
        "selected_role": selected_role,
        "invalid_role": invalid_role,
        "github": github,
        "roadmap": roadmap,
        "roadmap_tasks": tasks,
        "roadmap_weeks": roadmap_weeks,
        "interview": latest_interview,
        "interview_answers": answers,
        "latest_answer": answers.last() if latest_interview else None,
        "resume_history": resume_history,
        "interview_history": interview_history,
        "active_question": latest_interview.questions[latest_interview.question_index] if latest_interview and latest_interview.status == "active" and latest_interview.question_index < len(latest_interview.questions) else None,
        "metrics": {
            "readiness": match_data.get("score", 0),
            "identified_skills": len(latest_analysis.skills) if latest_analysis else 0,
            "missing_skills": len(match_data.get("missing_skills", [])),
            "repositories": github.get("repository_count", 0) if github else 0,
            "roadmap_progress": round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
            "interview_score": completed_interview.summary.get("score", 0) if completed_interview else 0,
            "interviews_completed": completed_interviews.count(),
            "interview_roles": completed_interviews.values_list("role", flat=True).distinct().count(),
            "interview_best_score": max(completed_scores) if completed_scores else 0,
        },
        "chart_data": {
            "matched": len(match_data.get("matched_skills", [])),
            "missing": len(match_data.get("missing_skills", [])),
            "preferred": len(match_data.get("preferred_skills", [])),
            "required_matched": len(match_data.get("matched_skills", [])),
            "required_missing": len(match_data.get("missing_skills", [])),
            "preferred_matched": len(match_data.get("preferred_skills", [])),
            "preferred_missing": len(match_data.get("missing_preferred_skills", [])),
            "completed_tasks": completed_tasks,
            "open_tasks": max(0, total_tasks - completed_tasks),
        },
    })

@require_POST
@login_required
def analyze_resume(request):
    uploaded = request.FILES.get("resume")
    role = request.POST.get("role", "").strip()
    if not uploaded:
        messages.error(request, "Please choose a PDF resume.")
        return redirect("workspace_section", section="resume")
    if not uploaded.name.lower().endswith(".pdf"):
        messages.error(request, "Please upload a PDF file.")
        return redirect("workspace_section", section="resume")
    if uploaded.size > 5 * 1024 * 1024:
        messages.error(request, "Please upload a PDF smaller than 5 MB.")
        return redirect("workspace_section", section="resume")
    if role not in ROLE_PROFILES:
        messages.error(request, "Choose one of the listed target roles.")
        return redirect("workspace_section", section="resume")
    try:
        file_bytes = uploaded.read()
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("The uploaded file is not a valid PDF.")
        text = extract_pdf_text(file_bytes)
        if len(text.strip()) < 30:
            messages.error(request, "No readable text found. This may be a scanned PDF. Try a text-based PDF.")
            return redirect("workspace_section", section="resume")
        skills = detect_skills(text)
        github_record = request.user.github_analyses.first()
        github_skills = github_record.profile_data.get("portfolio_skills", []) if github_record else []
        result = analyze_match(skills, role, github_skills)
        sections = extract_resume_sections(text)
        ResumeAnalysis.objects.create(
            user=request.user,
            role=role,
            resume_name=uploaded.name[:255],
            skills=skills,
            sections=sections,
            match_data=result,
        )
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        profile.target_role = role
        profile.save(update_fields=["target_role"])
        messages.success(request, "Resume analyzed successfully.")
    except (ValueError, OSError):
        messages.error(request, "Could not read this PDF. Please use a readable, text-based PDF under 5 MB.")
    return redirect("workspace_section", section="resume")

@login_required
@require_POST
def analyze_github(request):
    username = request.POST.get("username", "").strip()
    if not username:
        messages.error(request, "Enter a GitHub username.")
        return redirect("workspace_section", section="github")
    analysis = request.user.resume_analyses.first()
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    role = analysis.role if analysis else profile.target_role
    try:
        data = fetch_github_profile(username, role)
        GitHubAnalysis.objects.create(user=request.user, username=username, profile_data=data)
        if analysis:
            analysis.match_data = analyze_match(
                analysis.skills,
                analysis.role,
                data.get("portfolio_skills", []),
            )
            analysis.save(update_fields=["match_data"])
        profile.github_username = username
        profile.save(update_fields=["github_username"])
        messages.success(request, "Public GitHub profile analyzed.")
    except (ValueError, ConnectionError):
        messages.error(request, "GitHub could not analyze that profile. Check the username, connection, or API rate limit.")
    return redirect("workspace_section", section="github")

@login_required
@require_POST
def generate_roadmap(request):
    analysis_record = request.user.resume_analyses.first()
    if not analysis_record:
        messages.error(request, "Analyze a resume first.")
        return redirect("workspace_section", section="roadmap")
    github_record = request.user.github_analyses.first()
    role = request.POST.get("role", "").strip() or analysis_record.role
    if role not in ROLE_PROFILES:
        role = analysis_record.role
    analysis = analyze_match(
        analysis_record.skills,
        role,
        github_record.profile_data.get("portfolio_skills", []) if github_record else [],
    )
    analysis["sections"] = analysis_record.sections
    if not analysis.get("missing_skills"):
        messages.success(request, "You already meet all mandatory skills for this role. A skill-gap roadmap is not needed.")
        return redirect("workspace_section", section="match")
    generated = create_roadmap(analysis, github_record.profile_data if github_record else None)
    roadmap = Roadmap.objects.create(
        user=request.user,
        resume_analysis=analysis_record,
        role=role,
        content=generated,
    )
    RoadmapTask.objects.bulk_create([
        RoadmapTask(roadmap=roadmap, week=week_number, position=position, title=task)
        for week_number, week in enumerate(generated["weeks"], start=1)
        for position, task in enumerate(week["tasks"], start=1)
    ])
    messages.success(request, "Four-week learning roadmap saved to your progress.")
    return redirect("workspace_section", section="roadmap")


@login_required
@require_POST
def toggle_roadmap_task(request, task_id):
    task = get_object_or_404(RoadmapTask, pk=task_id, roadmap__user=request.user)
    task.completed = not task.completed
    task.completed_at = timezone.now() if task.completed else None
    task.save(update_fields=["completed", "completed_at"])
    return redirect("workspace_section", section="roadmap")


@login_required
@require_POST
def start_interview(request):
    role = request.POST.get("role", "").strip()
    if role not in ROLE_PROFILES:
        messages.error(request, "Choose a target role for your practice interview.")
        return redirect("workspace_section", section="interview")
    with transaction.atomic():
        attempt_number = (
            InterviewSession.objects.select_for_update()
            .filter(user=request.user, role=role)
            .count() + 1
        )
        session = InterviewSession.objects.create(
            user=request.user,
            role=role,
            attempt_number=attempt_number,
            questions=generate_interview_questions(role),
        )
    messages.success(request, "Practice interview started. Answer one question at a time.")
    return redirect(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")


@login_required
@require_POST
def submit_interview_answer(request, session_id):
    session = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    if session.status != "active" or session.question_index >= len(session.questions):
        messages.error(request, "This practice interview is already complete.")
        return redirect(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")
    answer = request.POST.get("answer", "").strip()
    if not answer or len(answer) > 5000:
        messages.error(request, "Enter an answer of up to 5,000 characters.")
        return redirect(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")
    index = session.question_index
    question = session.questions[index]
    feedback = evaluate_answer(session.role, question, answer)
    InterviewAnswer.objects.create(
        session=session,
        question_index=index,
        question=question,
        answer=answer,
        feedback=feedback,
    )
    session.question_index += 1
    if session.question_index >= len(session.questions):
        session.status = "completed"
        session.completed_at = timezone.now()
        session.summary = summarize_interview(session.answers.all())
        session.save(update_fields=["question_index", "status", "completed_at", "summary"])
        messages.success(request, "Practice interview complete. Review your feedback summary.")
    else:
        session.save(update_fields=["question_index"])
        messages.success(request, "Answer saved. Your feedback is ready below.")
    return redirect(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")


@login_required
def interview_history(request):
    sessions = request.user.interview_sessions.all()
    return render(request, "career/interview_history.html", {
        "interview_history": sessions,
        "roles": ROLE_PROFILES,
    })


@login_required
def interview_roles(request):
    sessions = request.user.interview_sessions.all()
    attempts_by_role = {}
    for session in sessions:
        attempts_by_role.setdefault(session.role, []).append(session)

    role_cards = []
    for role, profile in ROLE_PROFILES.items():
        attempts = attempts_by_role.get(role, [])
        completed = [item for item in attempts if item.status == "completed"]
        latest_completed = completed[0] if completed else None
        role_cards.append({
            "name": role,
            "description": f"Practice role-specific questions on {', '.join(profile['interview_topics'][:3])}.",
            "topics": profile["interview_topics"],
            "attempt_count": len(attempts),
            "latest_score": latest_completed.summary.get("score") if latest_completed else None,
            "practised": bool(attempts),
        })
    return render(request, "career/interview_roles.html", {
        "role_cards": role_cards,
    })


@login_required
def interview_result(request, session_id):
    session = get_object_or_404(
        InterviewSession,
        pk=session_id,
        user=request.user,
    )
    if session.status != "completed":
        messages.info(request, "This interview is still in progress.")
    return redirect(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")
