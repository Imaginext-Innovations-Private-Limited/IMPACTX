import json
from unittest.mock import Mock, patch

import pymupdf
import requests
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import GitHubAnalysis, InterviewSession, ResumeAnalysis, Roadmap, RoadmapTask
from .services.github import fetch_github_profile
from .services.interview import evaluate_answer, interview_questions, generate_interview_questions, summarize_interview
from .services.matching import ROLE_PROFILES, analyze_match, recommend_alternative_roles
from .services.ollama import create_roadmap, generate_json
from .services.resume import detect_skills, extract_pdf_text, extract_resume_sections


class ResumeServiceTests(TestCase):
    def test_phrase_matching_avoids_substrings_and_keeps_punctuation(self):
        self.assertEqual(detect_skills("Capital city and reactions"), [])
        self.assertEqual(
            detect_skills("React, REST API, C++, and Python"),
            ["c++", "python", "react", "rest api"],
        )

    def test_extracts_pdf_text_and_named_sections(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "EDUCATION\nBSc Computer Science\nPROJECTS\nBuilt a Django REST API using Python")
        pdf_bytes = document.tobytes()
        document.close()

        text = extract_pdf_text(pdf_bytes)
        sections = extract_resume_sections(text)

        self.assertIn("Django", text)
        self.assertIn("BSc Computer Science", sections["education"])
        self.assertIn("Django REST API", sections["projects"])

    def test_rejects_unreadable_pdf(self):
        with self.assertRaises(ValueError):
            extract_pdf_text(b"not a pdf")


class MatchingServiceTests(TestCase):
    def test_weighted_score_and_breakdown(self):
        profile = ROLE_PROFILES["Python Developer"]
        result = analyze_match(profile["required"][:4] + profile["preferred"][:2], "Python Developer")

        self.assertEqual(result["score"], round(100 * (0.80 * 4 / len(profile["required"]) + 0.20 * 2 / len(profile["preferred"]))))
        self.assertEqual(len(result["skill_breakdown"]), len(profile["required"]) + len(profile["preferred"]))
        self.assertEqual(len(result["missing_skills"]), len(profile["required"]) - 4)
        self.assertIn("not a hiring probability", result["score_explanation"])

    def test_unknown_role_falls_back_to_supported_profile(self):
        self.assertEqual(analyze_match([], "Other")['role'], "Python Developer")

    def test_all_mandatory_skills_are_a_perfect_match_but_optional_skills_remain_optional(self):
        profile = ROLE_PROFILES["Python Developer"]
        result = analyze_match(profile["required"], "Python Developer")

        self.assertTrue(result["perfect_match"])
        self.assertEqual(result["match_category"], "Perfect Match")
        self.assertEqual(result["score"], 80)
        self.assertEqual(result["readiness_status"], "NO MANDATORY SKILL ENHANCEMENT REQUIRED")
        self.assertLess(result["score"], 100)
        self.assertFalse(result["missing_skills"])
        self.assertTrue(result["missing_preferred_skills"])

    def test_one_hundred_percent_requires_all_mandatory_and_preferred_skills(self):
        profile = ROLE_PROFILES["Python Developer"]
        result = analyze_match(
            profile["required"] + profile["preferred"],
            "Python Developer",
        )

        self.assertTrue(result["perfect_match"])
        self.assertTrue(result["all_defined_requirements_satisfied"])
        self.assertEqual(result["score"], 100)

    def test_rounding_never_displays_one_hundred_with_an_unmet_requirement(self):
        profile = {
            "required": [f"skill-{index}" for index in range(170)],
            "preferred": ["optional-skill"],
            "tools": [], "projects": [], "interview_topics": [],
        }
        with patch.dict(ROLE_PROFILES, {"Rounding Test": profile}):
            result = analyze_match(
                profile["required"][:-1] + profile["preferred"],
                "Rounding Test",
            )

        self.assertFalse(result["perfect_match"])
        self.assertFalse(result["all_defined_requirements_satisfied"])
        self.assertEqual(result["score"], 99)

    def test_one_missing_mandatory_skill_is_a_partial_match_with_minimum_enhancement(self):
        profile = ROLE_PROFILES["Python Developer"]
        skills = profile["required"][:-1] + profile["preferred"][:1]
        result = analyze_match(skills, "Python Developer")

        self.assertFalse(result["perfect_match"])
        self.assertEqual(result["match_category"], "Strong Match")
        self.assertEqual(result["missing_skills"], [profile["required"][-1]])
        self.assertEqual(
            [item["skill"] for item in result["enhancement_recommendations"]],
            result["missing_skills"],
        )
        self.assertGreater(result["expected_score_after_mandatory_skills"], result["score"])
        self.assertIn("does not predict hiring outcomes", result["expected_score_note"])

    def test_duplicate_skills_and_github_skill_evidence_do_not_inflate_coverage(self):
        result = analyze_match(["python", "Python", " SQL "], "Python Developer", ["django", "django"])

        self.assertEqual(result["student_skills"].count("python"), 1)
        self.assertEqual(result["student_skills"].count("django"), 1)
        self.assertEqual(result["github_matched_skills"], ["django"])

    def test_missing_github_data_does_not_change_resume_match(self):
        skills = ["python", "sql"]
        without_github = analyze_match(skills, "Python Developer")
        with_empty_github = analyze_match(skills, "Python Developer", [])

        self.assertEqual(without_github["score"], with_empty_github["score"])
        self.assertEqual(without_github["missing_skills"], with_empty_github["missing_skills"])

    def test_optional_skills_affect_score_but_not_readiness(self):
        profile = ROLE_PROFILES["Python Developer"]
        result = analyze_match(profile["required"], "Python Developer")

        self.assertTrue(result["ready_for_role"])
        self.assertEqual(result["mandatory_coverage"], 100)
        self.assertEqual(result["optional_coverage"], 0)
        self.assertEqual(result["score"], 80)

    def test_zero_optional_requirements_are_handled_safely(self):
        profile = {
            "required": ["python", "sql"],
            "preferred": [],
            "tools": [], "projects": [], "interview_topics": [],
        }
        with patch.dict(ROLE_PROFILES, {"No Optional Role": profile}):
            result = analyze_match(["python"], "No Optional Role")

        self.assertFalse(result["ready_for_role"])
        self.assertIsNone(result["optional_coverage"])
        self.assertEqual(result["score"], 50)

        with patch.dict(ROLE_PROFILES, {"No Optional Role": profile}):
            ready = analyze_match(["python", "sql"], "No Optional Role")
        self.assertTrue(ready["ready_for_role"])
        self.assertEqual(ready["score"], 100)

    def test_recommends_multiple_roles_ready_now_and_excludes_selected_role(self):
        skills = ROLE_PROFILES["Frontend Developer"]["required"] + ["node.js", "python", "django", "sql"]
        result = recommend_alternative_roles(skills, "Python Developer")

        roles = [item["role"] for item in result["ready"]]
        self.assertIn("Frontend Developer", roles)
        self.assertIn("Full Stack Developer", roles)
        self.assertNotIn("Python Developer", roles)
        self.assertEqual(len(roles), len(set(roles)))

    def test_recommends_only_roles_with_enough_mandatory_overlap(self):
        skills = ROLE_PROFILES["Frontend Developer"]["required"]
        result = recommend_alternative_roles(skills, "Data Analyst")

        self.assertEqual([item["role"] for item in result["ready"]], ["Frontend Developer"])
        self.assertNotIn("Machine Learning Engineer", [item["role"] for item in result["enhancement"]])

    def test_no_immediately_applicable_roles_is_an_empty_ready_group(self):
        result = recommend_alternative_roles(["python", "sql", "git"], "Python Developer")

        self.assertEqual(result["ready"], [])
        self.assertEqual(result["enhancement"], [])

    def test_missing_optional_skills_does_not_block_ready_recommendation(self):
        result = recommend_alternative_roles(ROLE_PROFILES["Frontend Developer"]["required"], "Python Developer")
        frontend = next(item for item in result["ready"] if item["role"] == "Frontend Developer")

        self.assertTrue(frontend["ready_for_role"])
        self.assertEqual(frontend["missing_mandatory_skills"], [])
        self.assertEqual(frontend["missing_optional_skills"], ROLE_PROFILES["Frontend Developer"]["preferred"])

    def test_missing_mandatory_skills_are_explained_for_enhancement_roles(self):
        profile = ROLE_PROFILES["Frontend Developer"]
        result = recommend_alternative_roles(profile["required"][:5], "Python Developer")
        frontend = next(item for item in result["enhancement"] if item["role"] == "Frontend Developer")

        self.assertFalse(frontend["ready_for_role"])
        self.assertEqual(frontend["missing_mandatory_skills"], profile["required"][5:])
        self.assertIn("mandatory", frontend["explanation"])

    def test_missing_github_profile_is_supported_without_penalty(self):
        skills = ROLE_PROFILES["Frontend Developer"]["required"]
        without_github = recommend_alternative_roles(skills, "Python Developer")
        with_empty_github = recommend_alternative_roles(skills, "Python Developer", [])

        self.assertEqual(without_github, with_empty_github)

    def test_github_explicit_skills_can_complete_an_alternative_role(self):
        profile = ROLE_PROFILES["Frontend Developer"]
        result = recommend_alternative_roles(profile["required"][:-1], "Python Developer", ["rest api"])
        frontend = next(item for item in result["ready"] if item["role"] == "Frontend Developer")

        self.assertIn("rest api", frontend["github_matched_skills"])
        self.assertIn("explicit public project descriptions", frontend["explanation"])


class GitHubServiceTests(TestCase):
    @staticmethod
    def response(data):
        response = Mock(status_code=200, headers={}, json=lambda: data)
        response.raise_for_status.return_value = None
        return response

    @patch("career.services.github.requests.get")
    def test_returns_role_ranked_public_repository_metadata(self, get):
        get.side_effect = [
            self.response({"name": "Dev", "public_repos": 1, "followers": 2, "html_url": "https://github.com/dev"}),
            self.response([{
                "name": "django-api", "description": "REST API with Django", "language": "Python",
                "stargazers_count": 4, "forks_count": 2, "updated_at": "2026-01-01T00:00:00Z",
                "html_url": "https://github.com/dev/django-api",
            }]),
        ]

        result = fetch_github_profile("dev", "Python Developer")

        self.assertEqual(result["repository_count"], 1)
        self.assertEqual(result["total_forks"], 2)
        self.assertGreater(result["top_repos"][0]["relevance"], 0)
        self.assertEqual(set(result["portfolio_skills"]), {"django", "rest api"})
        self.assertEqual(get.call_count, 2)

    @patch("career.services.github.requests.get")
    def test_repository_language_alone_is_not_counted_as_a_skill(self, get):
        get.side_effect = [
            self.response({"name": "Dev", "public_repos": 1}),
            self.response([{
                "name": "python-project", "description": "A starter repository",
                "language": "Python", "html_url": "https://github.com/dev/python-project",
            }]),
        ]

        result = fetch_github_profile("dev", "Python Developer")

        self.assertNotIn("python", result["portfolio_skills"])
        self.assertEqual(result["languages"], {"Python": 1})

    @patch("career.services.github.requests.get")
    def test_rejects_invalid_username_before_network_call(self, get):
        with self.assertRaises(ValueError):
            fetch_github_profile("bad/name")
        get.assert_not_called()


class OllamaServiceTests(TestCase):
    def test_generate_json_handles_local_model_response(self):
        response = Mock()
        response.json.return_value = {"response": json.dumps({"ok": True})}
        response.raise_for_status.return_value = None
        with patch("career.services.ollama.requests.post", return_value=response):
            self.assertEqual(generate_json("Return JSON"), {"ok": True})

    @patch("career.services.ollama.requests.post", side_effect=requests.ConnectionError)
    def test_unavailable_ollama_uses_the_built_in_roadmap_fallback(self, _post):
        result = create_roadmap({"role": "Python Developer", "missing_skills": ["django"]})

        self.assertTrue(result["source"].startswith("Built-in"))
        self.assertEqual(len(result["weeks"]), 4)

    @patch("career.services.ollama.generate_json", return_value=None)
    def test_roadmap_fallback_is_four_weeks(self, _generate):
        result = create_roadmap({"role": "Python Developer", "missing_skills": ["django"]})
        self.assertTrue(result["source"].startswith("Built-in"))
        self.assertEqual(len(result["weeks"]), 4)
        self.assertTrue(all(week["tasks"] and week["resources"] for week in result["weeks"]))

    @patch("career.services.ollama.generate_json")
    def test_roadmap_replaces_unverified_resource_names(self, generate):
        generate.return_value = {"weeks": [{
            "objective": "Learn", "topics": ["Python"], "tasks": ["Build", "Test"],
            "outcome": "A small API", "resources": ["unverified title"],
        } for _ in range(4)]}
        result = create_roadmap({"role": "Python Developer", "missing_skills": ["django"]})
        self.assertEqual(result["weeks"][0]["resources"], ["Official Python tutorial", "Exercism Python track"])


class InterviewServiceTests(TestCase):
    def test_questions_are_role_specific(self):
        questions = interview_questions("Data Analyst")
        self.assertEqual(len(questions), 4)
        self.assertIn("SQL", questions[0])

    @patch("career.services.interview.generate_json", return_value=None)
    def test_generated_frontend_questions_are_frontend_specific(self, _generate):
        questions = generate_interview_questions("Frontend Developer")
        self.assertEqual(len(questions), 4)
        self.assertTrue(any("React" in question or "CSS" in question or "DOM" in question for question in questions))

    @patch("career.services.interview.generate_json", return_value=None)
    def test_offline_answer_feedback_is_bounded_and_structured(self, _generate):
        feedback = evaluate_answer("Python Developer", "How would you test an API?", "For example, I would test invalid inputs and measure response behavior.")
        self.assertTrue(0 <= feedback["score"] <= 100)
        self.assertTrue(feedback["strengths"])
        self.assertTrue(feedback["improvements"])
        self.assertEqual(feedback["source"], "Built-in practice rubric (local AI unavailable)")

    @patch("career.services.interview.generate_json", return_value={"score": 120, "feedback": "", "strengths": [], "improvements": []})
    def test_invalid_ai_feedback_uses_fallback(self, _generate):
        feedback = evaluate_answer("Python Developer", "Explain SQL joins", "I would compare examples and test the output.")
        self.assertTrue(feedback["source"].startswith("Built-in"))

    @patch("career.services.interview.generate_json", return_value=None)
    def test_irrelevant_answer_receives_low_fallback_score(self, _generate):
        feedback = evaluate_answer("Python Developer", "How would you test an API?", "I enjoy cooking pizza and watching movies.")
        self.assertLess(feedback["score"], 20)
        self.assertIn("unrelated", feedback["feedback"].lower())

    @patch("career.services.interview.generate_json", return_value=None)
    def test_empty_answer_receives_zero_fallback_score(self, _generate):
        feedback = evaluate_answer("Python Developer", "How would you test an API?", "")
        self.assertEqual(feedback["score"], 0)
        self.assertEqual(feedback["strengths"], [])

    @patch("career.services.interview.generate_json", return_value=None)
    def test_partial_answer_receives_partial_fallback_score(self, _generate):
        feedback = evaluate_answer("Python Developer", "Explain SQL joins", "A join combines tables using a related on key.")
        self.assertGreater(feedback["score"], 0)
        self.assertLess(feedback["score"], 70)

    @patch("career.services.interview.generate_json", return_value=None)
    def test_complete_answer_scores_higher_than_incomplete_answer(self, _generate):
        incomplete = evaluate_answer("Python Developer", "How would you test an API?", "Use unit test assertions for invalid input.")
        complete = evaluate_answer(
            "Python Developer",
            "How would you test an API?",
            "I would use pytest unit tests and integration tests to call each endpoint. "
            "I would assert successful status codes and JSON responses, and test invalid input, authentication, edge cases, and mocks.",
        )
        self.assertLess(incomplete["score"], complete["score"])
        self.assertGreaterEqual(complete["score"], 70)

    @patch("career.services.interview.generate_json", return_value={"response": "not-json"})
    def test_invalid_ollama_json_shape_uses_fallback(self, _generate):
        feedback = evaluate_answer("Python Developer", "How would you test an API?", "I would use unit tests and pytest.")
        self.assertTrue(feedback["source"].startswith("Built-in"))

    @patch("career.services.interview.generate_json", return_value={
        "rubric": {
            "relevance": 90,
            "technical_correctness": 80,
            "completeness": 75,
            "practical_understanding": 85,
            "clarity": 90,
        },
        "feedback": "The answer gave a clear API testing approach.",
        "strengths": ["Described endpoint testing."],
        "improvements": ["Add authentication edge cases."],
    })
    def test_ollama_rubric_dimensions_calculate_weighted_score(self, _generate):
        feedback = evaluate_answer("Python Developer", "How would you test an API?", "I would test endpoints with pytest.")
        self.assertEqual(feedback["score"], 83)
        self.assertTrue(feedback["source"].startswith("Local AI"))

    def test_overall_score_is_average_of_individual_scores(self):
        records = [
            Mock(feedback={"score": 10, "strengths": [], "improvements": [], "source": "Test"}),
            Mock(feedback={"score": 20, "strengths": [], "improvements": [], "source": "Test"}),
            Mock(feedback={"score": 0, "strengths": [], "improvements": [], "source": "Test"}),
            Mock(feedback={"score": 30, "strengths": [], "improvements": [], "source": "Test"}),
        ]
        summary = summarize_interview(records)
        self.assertEqual(summary["score"], 15)


class CareerViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="career-user", password="Strong-test-password-52")
        self.other_user = get_user_model().objects.create_user(username="other-user", password="Strong-test-password-53")

    def test_authentication_required_for_workspace_and_resume_upload(self):
        response = self.client.get(reverse("workspace"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('workspace')}")
        response = self.client.post(reverse("analyze_resume"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_resume_upload_saves_analysis_without_saving_pdf(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "EDUCATION\nComputer Science\nSKILLS\nPython Django SQL REST API Git\nPROJECTS\nBuilt a Django REST API project with Python and SQL")
        pdf_bytes = document.tobytes()
        document.close()
        self.client.force_login(self.user)
        upload = SimpleUploadedFile("resume.pdf", pdf_bytes, content_type="application/pdf")

        response = self.client.post(reverse("analyze_resume"), {"resume": upload, "role": "Python Developer"})

        self.assertEqual(response.status_code, 302)
        analysis = ResumeAnalysis.objects.get(user=self.user)
        self.assertIn("python", analysis.skills)
        self.assertIn("Django", analysis.sections["projects"])
        self.assertFalse(hasattr(analysis, "file"))

    def test_missing_github_profile_still_renders_a_resume_match(self):
        profile = ROLE_PROFILES["Python Developer"]
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["python"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "match"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["result"]["score"],
            round(100 * (0.80 / len(profile["required"]) + 0.20 * 0)),
        )
        self.assertContains(response, "Missing GitHub information does not count against your match.")

    def test_dashboard_renders_alternative_role_recommendations(self):
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=ROLE_PROFILES["Frontend Developer"]["required"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace"))

        self.assertContains(response, "YOUR CAREER OPPORTUNITIES")
        self.assertContains(response, "Ready to Apply")
        self.assertContains(response, "Frontend Developer")
        self.assertContains(response, "NO MANDATORY SKILL ENHANCEMENT REQUIRED")

    def test_alternative_role_link_opens_that_role_analysis(self):
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["html"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Frontend Developer"},
        )

        self.assertEqual(response.context["result"]["role"], "Frontend Developer")

    def test_role_navigation_reuses_resume_and_github_profile_for_selected_role(self):
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["html"], sections={"projects": ["Frontend project"]}, match_data={},
        )
        GitHubAnalysis.objects.create(
            user=self.user, username="dev", profile_data={"portfolio_skills": ["javascript"]},
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Frontend Developer"},
        )

        self.assertEqual(response.context["result"]["role"], "Frontend Developer")
        self.assertIn("html", response.context["result"]["resume_skills"])
        self.assertIn("javascript", response.context["result"]["github_skills"])
        self.assertEqual(response.context["result"]["sections"]["projects"], ["Frontend project"])
        self.assertContains(response, "Back to Career Opportunities")
        self.assertContains(response, f'href="{reverse("workspace")}"')
        self.assertContains(response, f'href="{reverse("workspace_section", kwargs={"section": "match"})}"')
        self.assertEqual(ResumeAnalysis.objects.filter(user=self.user).count(), 1)

    def test_different_alternative_roles_render_different_role_specific_results(self):
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["html", "css", "javascript", "react", "git", "rest api"],
            sections={}, match_data={},
        )
        self.client.force_login(self.user)

        frontend = self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Frontend Developer"},
        )
        full_stack = self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Full Stack Developer"},
        )

        self.assertEqual(frontend.context["result"]["role"], "Frontend Developer")
        self.assertEqual(full_stack.context["result"]["role"], "Full Stack Developer")
        self.assertNotEqual(frontend.context["result"]["required_skills"], full_stack.context["result"]["required_skills"])

    def test_returning_to_career_opportunities_preserves_saved_analysis(self):
        analysis = ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["html"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Frontend Developer"},
        )
        response = self.client.get(reverse("workspace"))

        self.assertEqual(response.context["result"]["role"], "Python Developer")
        self.assertEqual(response.context["resume_history"][0].pk, analysis.pk)

    def test_missing_analysis_shows_resume_analyzer_link(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "match"}))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["result"])
        self.assertContains(response, "Start with a resume analysis.")
        self.assertContains(response, f'href="{reverse("workspace_section", kwargs={"section": "resume"})}"')

    def test_invalid_role_does_not_fall_back_or_redirect_to_resume(self):
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["python"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workspace_section", kwargs={"section": "match"}),
            {"role": "Not A Supported Role"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["invalid_role"])
        self.assertIsNone(response.context["result"])
        self.assertContains(response, "That job role is not supported.")
        self.assertNotContains(response, "Start with a resume analysis.")

    def test_workspace_uses_only_the_authenticated_users_analysis(self):
        ResumeAnalysis.objects.create(
            user=self.other_user, role="Frontend Developer", resume_name="other.pdf",
            skills=ROLE_PROFILES["Frontend Developer"]["required"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "match"}))

        self.assertIsNone(response.context["result"])

    @patch("career.views.fetch_github_profile")
    def test_explicit_github_description_skills_are_included_in_the_match(self, fetch_profile):
        fetch_profile.return_value = {
            "username": "dev", "portfolio_skills": ["django"],
            "languages": {"Python": 1},
        }
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=["python"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        self.client.post(reverse("analyze_github"), {"username": "dev"})

        github = GitHubAnalysis.objects.get(user=self.user)
        self.assertEqual(github.profile_data["portfolio_skills"], ["django"])
        self.assertIn("django", self.user.resume_analyses.first().match_data["matched_skills"])

    @patch("career.views.create_roadmap")
    def test_perfect_match_does_not_allow_unnecessary_roadmap_generation(self, create_roadmap):
        profile = ROLE_PROFILES["Python Developer"]
        ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="resume.pdf",
            skills=profile["required"], sections={}, match_data={},
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "match"}))
        self.assertContains(response, "YOU ARE READY FOR THIS ROLE!")
        self.assertContains(response, "Explore Another Job Role")
        self.assertNotContains(response, "Generate a personalized learning roadmap")

        response = self.client.post(reverse("generate_roadmap"))
        self.assertRedirects(response, reverse("workspace_section", kwargs={"section": "match"}))
        create_roadmap.assert_not_called()

    def test_user_cannot_see_or_change_another_users_records(self):
        analysis = ResumeAnalysis.objects.create(
            user=self.user, role="Python Developer", resume_name="private-resume.pdf",
            skills=["python"], sections={}, match_data={"role": "Python Developer", "score": 80},
        )
        roadmap = Roadmap.objects.create(user=self.user, resume_analysis=analysis, role=analysis.role, content={"weeks": []})
        task = RoadmapTask.objects.create(roadmap=roadmap, week=1, position=1, title="Private task")
        self.client.force_login(self.other_user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "resume"}))
        self.assertIsNone(response.context["result"])
        response = self.client.post(reverse("toggle_roadmap_task", kwargs={"task_id": task.id}))
        self.assertEqual(response.status_code, 404)
        task.refresh_from_db()
        self.assertFalse(task.completed)

    def test_all_workspace_sections_render_for_authenticated_users(self):
        self.client.force_login(self.user)
        for section in ("overview", "resume", "github", "match", "roadmap", "interview", "progress"):
            with self.subTest(section=section):
                response = self.client.get(reverse("workspace_section", kwargs={"section": section}))
                self.assertEqual(response.status_code, 200)

    def test_resume_page_renders_drop_upload_and_role_profile_counts(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("workspace_section", kwargs={"section": "resume"}))

        self.assertContains(response, 'id="resume-dropzone"')
        self.assertContains(response, 'id="resume-file-name"')
        self.assertContains(response, 'id="role-summary"')
        for role in ROLE_PROFILES:
            with self.subTest(role=role):
                self.assertContains(response, f'data-required="{len(ROLE_PROFILES[role]["required"])}"')

    @patch("career.views.create_roadmap")
    def test_roadmap_tasks_persist_and_progress_updates(self, create_roadmap):
        self.client.force_login(self.user)
        analysis = ResumeAnalysis.objects.create(
            user=self.user,
            role="Python Developer",
            resume_name="resume.pdf",
            skills=["python"],
            sections={"projects": "Portfolio API"},
            match_data={"role": "Python Developer", "score": 30, "matched_skills": ["python"], "missing_skills": ["django"]},
        )
        weeks = [{
            "objective": f"Week {number}", "topics": ["Django"], "tasks": [f"Task {number}"],
            "outcome": f"Outcome {number}", "resources": ["Official Python tutorial"],
        } for number in range(1, 5)]
        create_roadmap.return_value = {"source": "Test fallback", "weeks": weeks}

        response = self.client.post(reverse("generate_roadmap"))

        self.assertRedirects(response, reverse("workspace_section", kwargs={"section": "roadmap"}))
        roadmap = Roadmap.objects.get(user=self.user, resume_analysis=analysis)
        self.assertEqual(roadmap.tasks.count(), 4)
        task = roadmap.tasks.first()
        self.client.post(reverse("toggle_roadmap_task", kwargs={"task_id": task.id}))
        task.refresh_from_db()
        self.assertTrue(task.completed)
        response = self.client.get(reverse("workspace_section", kwargs={"section": "roadmap"}))
        self.assertEqual(response.context["metrics"]["roadmap_progress"], 25)

    @patch("career.views.evaluate_answer", return_value={
        "score": 75, "feedback": "Clear answer.", "strengths": ["Reasoned"], "improvements": ["Add tests"], "source": "Test",
    })
    def test_interview_session_advances_and_completes(self, _evaluate):
        self.client.force_login(self.user)
        self.client.post(reverse("start_interview"), {"role": "Python Developer"})
        session = InterviewSession.objects.get(user=self.user)
        for _ in range(len(session.questions)):
            self.client.post(reverse("submit_interview_answer", kwargs={"session_id": session.id}), {"answer": "A careful example answer with test results."})
            session.refresh_from_db()
            if session.status == "active":
                self.assertContains(self.client.get(reverse("workspace_section", kwargs={"section": "interview"})), "FEEDBACK ON YOUR LAST ANSWER")
        self.assertEqual(session.status, "completed")
        self.assertEqual(session.summary["score"], 75)
        self.assertEqual(session.answers.count(), 4)
        results = self.client.get(f"{reverse('workspace_section', kwargs={'section': 'interview'})}?session={session.id}")
        self.assertContains(results, f'href="{reverse("interview_roles")}"')
        self.assertContains(results, "Retake This Role")

    @patch("career.views.generate_interview_questions", side_effect=[
        ["Python question 1", "Python question 2", "Python question 3", "Python question 4"],
        ["Python retake 1", "Python retake 2", "Python retake 3", "Python retake 4"],
        ["Frontend question 1", "Frontend question 2", "Frontend question 3", "Frontend question 4"],
    ])
    def test_multiple_attempts_retake_and_role_switch_are_separate(self, _questions):
        self.client.force_login(self.user)
        first = self.client.post(reverse("start_interview"), {"role": "Python Developer"})
        python_first = InterviewSession.objects.filter(user=self.user, role="Python Developer").latest("id")
        self.assertEqual(python_first.attempt_number, 1)
        second = self.client.post(reverse("start_interview"), {"role": "Python Developer"})
        python_second = InterviewSession.objects.filter(user=self.user, role="Python Developer").latest("id")
        self.assertNotEqual(python_first.id, python_second.id)
        self.assertEqual(python_second.attempt_number, 2)
        frontend = self.client.post(reverse("start_interview"), {"role": "Frontend Developer"})
        frontend_session = InterviewSession.objects.filter(user=self.user, role="Frontend Developer").get()
        self.assertEqual(frontend_session.attempt_number, 1)
        self.assertTrue(frontend_session.questions[0].startswith("Frontend"))
        self.assertTrue(python_second.questions[0].startswith("Python retake"))
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(frontend.status_code, 302)

    def test_user_cannot_open_another_users_interview_result(self):
        own = InterviewSession.objects.create(
            user=self.user, role="Python Developer", questions=["Question"], status="completed",
            summary={"score": 80},
        )
        other = InterviewSession.objects.create(
            user=self.other_user, role="Frontend Developer", questions=["Question"], status="completed",
            summary={"score": 90},
        )
        self.client.force_login(self.user)
        allowed = self.client.get(reverse("interview_result", kwargs={"session_id": own.id}))
        denied = self.client.get(reverse("interview_result", kwargs={"session_id": other.id}))
        self.assertEqual(allowed.status_code, 302)
        self.assertEqual(denied.status_code, 404)

    def test_completed_attempt_cannot_be_submitted_again(self):
        self.client.force_login(self.user)
        session = InterviewSession.objects.create(
            user=self.user,
            role="Python Developer",
            questions=["Question"],
            status="completed",
            summary={"score": 70},
        )
        before_answers = session.answers.count()
        response = self.client.post(
            reverse("submit_interview_answer", kwargs={"session_id": session.id}),
            {"answer": "This must not overwrite the result."},
        )
        session.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(session.answers.count(), before_answers)
        self.assertEqual(session.summary["score"], 70)

    def test_interview_history_lists_attempt_ids_and_roles(self):
        self.client.force_login(self.user)
        InterviewSession.objects.create(
            user=self.user, role="Python Developer", attempt_number=1,
            questions=["Question"], status="completed", summary={"score": 55},
        )
        InterviewSession.objects.create(
            user=self.user, role="Frontend Developer", attempt_number=1,
            questions=["Question"], status="completed", summary={"score": 65},
        )
        response = self.client.get(reverse("interview_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "Frontend Developer")

    def test_role_selection_uses_only_supported_roles_and_shows_attempt_info(self):
        self.client.force_login(self.user)
        InterviewSession.objects.create(
            user=self.user, role="Python Developer", attempt_number=1,
            questions=["Question"], status="completed", summary={"score": 72},
        )
        response = self.client.get(reverse("interview_roles"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [card["name"] for card in response.context["role_cards"]],
            list(ROLE_PROFILES),
        )
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "Latest score")
        self.assertContains(response, "72%")
        self.assertContains(response, reverse("start_interview"))
        self.assertNotContains(response, "Backend Developer")

    @patch("career.views.generate_interview_questions", return_value=[
        "Frontend HTML question", "Frontend CSS question",
        "Frontend React question", "Frontend DOM question",
    ])
    def test_role_selection_starts_fresh_role_specific_session(self, _questions):
        self.client.force_login(self.user)
        old_session = InterviewSession.objects.create(
            user=self.user, role="Python Developer", attempt_number=1,
            questions=["Old question"], status="completed", summary={"score": 72},
        )
        chooser = self.client.get(reverse("interview_roles"))
        self.assertEqual(chooser.status_code, 200)
        response = self.client.post(reverse("start_interview"), {"role": "Frontend Developer"})
        new_session = InterviewSession.objects.exclude(pk=old_session.pk).get(user=self.user)
        self.assertEqual(new_session.role, "Frontend Developer")
        self.assertEqual(new_session.attempt_number, 1)
        self.assertNotEqual(new_session.id, old_session.id)
        self.assertEqual(new_session.questions[0], "Frontend HTML question")
        self.assertEqual(old_session.questions, ["Old question"])
        self.assertIn(f"session={new_session.id}", response.url)
        active = self.client.get(response.url)
        self.assertContains(active, "Frontend HTML question")
