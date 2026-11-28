"""
Agent Tools Module for Sahaaya AI.
Defines the six official registered agent tools for government welfare scheme navigation:
1. search_schemes
2. retrieve_scheme_information
3. check_eligibility
4. get_required_documents
5. compare_schemes
6. get_application_guidance

All tools wrap existing deterministic Python engines and database models.
Includes strict argument validation, tool execution whitelisting, and zero use of eval/exec.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from models import GovernmentScheme, db
from engine.eligibility_engine import EligibilityEngine
from engine.document_engine import DocumentEngine
from engine.validator import validate_citizen_profile
from rag.retriever import DocumentRetriever
from rag.citation import CitationBuilder
from flask import has_app_context

logger = logging.getLogger("agent_tools")

try:
    from google.genai import types
    GENAI_TYPES_AVAILABLE = True
except ImportError:
    types = None
    GENAI_TYPES_AVAILABLE = False


# Whitelist of allowed tool names
ALLOWED_TOOL_NAMES = {
    "search_schemes",
    "retrieve_scheme_information",
    "check_eligibility",
    "get_required_documents",
    "compare_schemes",
    "get_application_guidance",
}


# =====================================================================
# 1. TOOL IMPLEMENTATIONS (Pure Python & SQLAlchemy Backed)
# =====================================================================

def tool_search_schemes(
    query: str,
    government_level: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search the government scheme catalog by query keyword and optional filters.
    Never fabricates missing fields.
    """
    if not query or not str(query).strip():
        return {
            "success": False,
            "error": "Query string is required for searching schemes.",
            "total_found": 0,
            "schemes": [],
        }

    clean_query = str(query).strip().lower()
    
    # Query database - filter for active schemes (status is VARCHAR like 'Active')
    db_query = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    )

    if government_level and str(government_level).strip():
        db_query = db_query.filter(
            GovernmentScheme.government_level.ilike(f"%{str(government_level).strip()}%")
        )

    if state and str(state).strip():
        db_query = db_query.filter(
            GovernmentScheme.state.ilike(f"%{str(state).strip()}%")
        )

    if category and str(category).strip():
        db_query = db_query.filter(
            GovernmentScheme.category.ilike(f"%{str(category).strip()}%")
        )

    all_schemes = db_query.all()

    # Match against name, description, category, and benefits
    matched = []
    keywords = [kw for kw in clean_query.split() if len(kw) > 1]

    for scheme in all_schemes:
        searchable_corpus = (
            f"{scheme.name} {scheme.description} {scheme.category} "
            f"{scheme.department} {scheme.benefits} {scheme.slug}"
        ).lower()

        # Score matching
        if any(kw in searchable_corpus for kw in keywords) or clean_query in searchable_corpus:
            matched.append({
                "scheme_name": scheme.name,
                "scheme_slug": scheme.slug,
                "government_level": scheme.government_level,
                "state": scheme.state or "All India",
                "department": scheme.department or "Not specified",
                "category": scheme.category or "General Welfare",
                "description": scheme.description,
                "benefits": scheme.benefits or "Financial or in-kind assistance as per government guidelines.",
                "verification_status": "Verified" if scheme.active_status else "Unverified",
                "official_portal_url": scheme.official_url,
                "application_url": scheme.application_url or scheme.official_url,
            })

    # If no keyword matches found, but category/level filter was applied, return the filtered set
    if not matched and (government_level or state or category):
        for scheme in all_schemes[:5]:
            matched.append({
                "scheme_name": scheme.name,
                "scheme_slug": scheme.slug,
                "government_level": scheme.government_level,
                "state": scheme.state or "All India",
                "department": scheme.department or "Not specified",
                "category": scheme.category or "General Welfare",
                "description": scheme.description,
                "benefits": scheme.benefits or "Financial or in-kind assistance as per government guidelines.",
                "verification_status": "Verified" if scheme.active_status else "Unverified",
                "official_portal_url": scheme.official_url,
                "application_url": scheme.application_url or scheme.official_url,
            })

    return {
        "success": True,
        "query": query,
        "filters_applied": {
            "government_level": government_level,
            "state": state,
            "category": category,
        },
        "total_found": len(matched),
        "schemes": matched,
    }


def tool_retrieve_scheme_information(
    query: str,
    scheme_slug: Optional[str] = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Retrieve grounded passages from official scheme guideline documents using the RAG pipeline.
    Preserves page numbers, source URLs, and verification statuses (verified vs demo_only).
    """
    if not query or not str(query).strip():
        return {
            "success": False,
            "query_status": "empty_query",
            "message": "Query string is required for information retrieval.",
            "citations": [],
        }

    clamped_k = max(1, min(10, int(top_k) if str(top_k).isdigit() else 3))
    retriever = DocumentRetriever()
    search_res = retriever.search(query=str(query).strip(), scheme_slug=scheme_slug, top_k=clamped_k)

    citations = search_res.get("citations", [])
    has_demo_only = any(c.get("verification_status") == "demo_only" for c in citations)
    has_unverified = any(c.get("verification_status") == "unverified" for c in citations)

    return {
        "success": search_res.get("query_status") == "success",
        "query": query,
        "scheme_slug": scheme_slug,
        "query_status": search_res.get("query_status"),
        "total_results": len(citations),
        "system_description": search_res.get("system_description", "SQLite FTS5 BM25 keyword-based retrieval engine"),
        "has_demo_material": has_demo_only,
        "has_unverified_material": has_unverified,
        "source_disclosure": (
            "NOTICE: Passages cited with [DEMO ONLY - LOCALLY GENERATED MATERIAL] are locally generated "
            "demonstration excerpts for offline testing, not authenticated government-issued gazette PDFs. "
            "Please confirm current rules with the official portal."
            if has_demo_only else "Official government documents cited."
        ),
        "citations": citations,
        "message": search_res.get("message", ""),
    }


def tool_check_eligibility(
    scheme_slug: str,
    citizen_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministically evaluate citizen eligibility for a scheme using EligibilityEngine.
    Gemini must NEVER compute or override this output.
    """
    if not scheme_slug or not str(scheme_slug).strip():
        return {
            "success": False,
            "overall_status": "unable_to_verify",
            "error": "scheme_slug is required for eligibility checking.",
        }

    clean_slug = str(scheme_slug).strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()

    if not scheme:
        return {
            "success": False,
            "scheme_slug": clean_slug,
            "overall_status": "unable_to_verify",
            "error": f"Scheme with slug '{clean_slug}' was not found in the verified database.",
            "disclaimer": "Welfare Scheme Navigator provides eligibility assessment only for schemes registered in its official catalog.",
        }

    # Ensure profile is a dict
    if isinstance(citizen_profile, str):
        try:
            citizen_profile = json.loads(citizen_profile)
        except Exception:
            citizen_profile = {}

    if not isinstance(citizen_profile, dict):
        citizen_profile = {}

    # Validate profile attributes before evaluation
    is_valid, val_err, val_details = validate_citizen_profile(citizen_profile, scheme_slug=clean_slug)
    if not is_valid:
        return {
            "success": False,
            "scheme_slug": clean_slug,
            "scheme_name": scheme.name,
            "overall_status": "unable_to_verify",
            "error": val_err,
            "details": val_details,
            "rules_evaluated": [],
            "rules_passed": [],
            "rules_failed": [],
            "rules_needing_info": [],
            "missing_information": [],
            "failed_rules": [],
            "passed_rules": [],
            "next_questions": [],
            "next_recommended_questions": [],
            "disclaimer": "Invalid demographic or socio-economic input provided for evaluation.",
        }

    # Execute deterministic engine
    eval_result = EligibilityEngine.evaluate_scheme(scheme, citizen_profile)
    eval_result["success"] = True
    eval_result["missing_information"] = [r["field_name"] for r in eval_result.get("rules_needing_info", [])]
    eval_result["failed_rules"] = eval_result.get("rules_failed", [])
    eval_result["passed_rules"] = eval_result.get("rules_passed", [])
    eval_result["next_questions"] = eval_result.get("next_recommended_questions", [])
    return eval_result


def tool_get_required_documents(scheme_slug: str) -> Dict[str, Any]:
    """
    Retrieve official document checklist for a scheme using DocumentEngine.
    Does NOT ask for uploads or sensitive identity credentials.
    """
    if not scheme_slug or not str(scheme_slug).strip():
        return {
            "success": False,
            "error": "scheme_slug is required to retrieve documents.",
        }

    clean_slug = str(scheme_slug).strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()

    if not scheme:
        return {
            "success": False,
            "scheme_slug": clean_slug,
            "error": f"Scheme with slug '{clean_slug}' was not found in the database.",
        }

    checklist = DocumentEngine.generate_checklist(scheme)
    checklist["success"] = True
    checklist["privacy_notice"] = (
        "Welfare Scheme Navigator does not ask for or collect physical document uploads, "
        "Aadhaar numbers, PAN numbers, or bank account credentials. "
        "This checklist is for your personal preparation only."
    )
    return checklist


def tool_compare_schemes(
    scheme_slugs: Optional[Union[List[str], str]] = None,
    slugs: Optional[Union[List[str], str]] = None,
) -> Dict[str, Any]:
    """
    Compare two or three government schemes side-by-side using database records.
    Never invents benefits or eligibility conditions.
    """
    target = scheme_slugs if scheme_slugs is not None else slugs

    if not target:
        return {
            "success": False,
            "error": "scheme_slugs list cannot be empty. Please provide at least two scheme slugs.",
            "schemes": [],
            "missing_schemes": [],
            "total_compared": 0,
        }

    if isinstance(target, str):
        target = [s.strip() for s in target.split(",") if s.strip()]

    if not isinstance(target, list):
        return {
            "success": False,
            "error": "Please provide a list of at least two valid scheme slugs to compare.",
            "schemes": [],
            "missing_schemes": [],
            "total_compared": 0,
        }

    # Deduplicate while preserving order
    unique_slugs = []
    for item in target:
        if isinstance(item, (str, int)):
            clean = str(item).strip().lower()
            if clean and clean not in unique_slugs:
                unique_slugs.append(clean)

    if len(unique_slugs) < 2:
        return {
            "success": False,
            "error": "Please provide at least two distinct valid schemes to compare.",
            "schemes": [],
            "missing_schemes": [],
            "total_compared": 0,
        }

    if len(unique_slugs) > 3:
        return {
            "success": False,
            "error": "You can compare a maximum of 3 schemes at a time.",
            "schemes": [],
            "missing_schemes": [],
            "total_compared": 0,
        }

    compared_schemes = []
    missing_slugs = []

    for slug in unique_slugs:
        if slug.isdigit():
            scheme = GovernmentScheme.query.filter(
                (GovernmentScheme.id == int(slug)) | (GovernmentScheme.slug == slug)
            ).first()
        else:
            scheme = GovernmentScheme.query.filter_by(slug=slug).first()

        if not scheme:
            missing_slugs.append(slug)
            continue

        # Extract summary of eligibility rules
        rules_summary = [r.description for r in scheme.rules] or ["Criteria as per official portal guidelines."]
        mandatory_docs = [d.document_name for d in scheme.documents if d.is_mandatory] or ["Refer to official portal."]

        compared_schemes.append({
            "scheme_name": scheme.name,
            "scheme_slug": scheme.slug,
            "government_level": scheme.government_level,
            "state": scheme.state or "All India",
            "department": scheme.department or "Not specified",
            "category": scheme.category or "General Welfare",
            "description": scheme.description,
            "benefits": scheme.benefits or "As specified in official guidelines.",
            "key_eligibility_criteria": rules_summary,
            "mandatory_documents": mandatory_docs,
            "official_portal_url": scheme.official_url,
            "application_url": scheme.application_url or scheme.official_url,
        })

    notes = [
        "Each government scheme addresses distinct socio-economic objectives and demographic groups.",
        "Benefits and eligibility cannot be cross-transferred between different state and central schemes.",
        "Citizens should verify individual application windows and documentation criteria on official portals.",
    ]

    if missing_slugs:
        return {
            "success": False,
            "error": f"The following scheme(s) could not be found: {', '.join(missing_slugs)}.",
            "total_compared": len(compared_schemes),
            "schemes": compared_schemes,
            "missing_schemes": missing_slugs,
            "comparison_notes": notes,
            "disclaimer": "Scheme comparisons are based on currently seeded database records.",
        }

    if len(compared_schemes) < 2:
        return {
            "success": False,
            "error": "At least two valid schemes are required for comparison.",
            "total_compared": len(compared_schemes),
            "schemes": compared_schemes,
            "missing_schemes": missing_slugs,
            "comparison_notes": notes,
            "disclaimer": "Scheme comparisons are based on currently seeded database records.",
        }

    return {
        "success": True,
        "total_compared": len(compared_schemes),
        "schemes": compared_schemes,
        "missing_schemes": [],
        "comparison_notes": notes,
        "disclaimer": (
            "Scheme comparisons are based on currently seeded database records. "
            "Always verify concurrent receipt restrictions with the respective department."
        ),
    }


def tool_get_application_guidance(scheme_slug: str) -> Dict[str, Any]:
    """
    Retrieve official step-by-step application guidance for a scheme.
    Discloses that Sahaaya AI cannot submit applications on behalf of citizens.
    """
    if not scheme_slug or not str(scheme_slug).strip():
        return {
            "success": False,
            "error": "scheme_slug is required for application guidance.",
        }

    clean_slug = str(scheme_slug).strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()

    if not scheme:
        return {
            "success": False,
            "scheme_slug": clean_slug,
            "error": f"Scheme with slug '{clean_slug}' was not found in the database.",
        }

    steps = [
        {
            "step_number": s.step_number,
            "instruction": s.instruction,
            "official_url": s.official_url or scheme.application_url or scheme.official_url,
        }
        for s in sorted(scheme.steps, key=lambda x: x.step_number)
    ]

    return {
        "success": True,
        "scheme_name": scheme.name,
        "scheme_slug": scheme.slug,
        "steps_count": len(steps),
        "steps": steps,
        "official_application_url": scheme.application_url or scheme.official_url,
        "official_portal_url": scheme.official_url,
        "department": scheme.department,
        "important_notice": (
            "Welfare Scheme Navigator (Sahaaya AI provides informational step-by-step guidance only). "
            "Welfare Scheme Navigator cannot directly submit applications, collect OTPs, or process registrations. "
            "Please use the official government portal links provided above."
        ),
    }


# =====================================================================
# 2. TOOL DISPATCHER & REGISTRATION
# =====================================================================

TOOL_REGISTRY = {
    "search_schemes": tool_search_schemes,
    "retrieve_scheme_information": tool_retrieve_scheme_information,
    "check_eligibility": tool_check_eligibility,
    "get_required_documents": tool_get_required_documents,
    "compare_schemes": tool_compare_schemes,
    "get_application_guidance": tool_get_application_guidance,
}


def execute_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Safely execute a registered tool by name with validated arguments.
    Enforces a strict whitelist and catches all execution errors without crashing.
    """
    if not name or name not in ALLOWED_TOOL_NAMES:
        logger.warning(f"Rejected execution of unregistered or disallowed tool: '{name}'")
        return {
            "success": False,
            "tool_name": name,
            "error": f"Disallowed tool '{name}'. Welfare Scheme Navigator allows only the 6 registered welfare navigation tools.",
        }

    if args is None:
        args = {}

    if not isinstance(args, dict):
        return {
            "success": False,
            "tool_name": name,
            "error": f"Invalid arguments format for tool '{name}'. Expected JSON dictionary.",
        }

    tool_fn = TOOL_REGISTRY[name]
    ctx = None
    if not has_app_context():
        try:
            from app import create_app
            flask_app = create_app("development")
            ctx = flask_app.app_context()
            ctx.push()
        except Exception as e:
            logger.warning(f"Could not push Flask application context: {e}")

    try:
        logger.info(f"Executing agent tool '{name}' with arguments: {list(args.keys())}")
        result = tool_fn(**args)
        return result
    except TypeError as te:
        logger.error(f"Tool '{name}' signature mismatch: {te}")
        return {
            "success": False,
            "tool_name": name,
            "error": f"Invalid arguments provided for tool '{name}': {str(te)}",
        }
    except Exception as exc:
        logger.error(f"Error executing tool '{name}': {type(exc).__name__} - {str(exc)}")
        return {
            "success": False,
            "tool_name": name,
            "error": f"Internal error during execution of tool '{name}': {str(exc)}",
        }
    finally:
        if ctx:
            try:
                ctx.pop()
            except Exception:
                pass


# =====================================================================
# 3. GEMINI FUNCTION DECLARATIONS (google-genai SDK Format)
# =====================================================================

def get_gemini_tools() -> List[Any]:
    """
    Construct official types.Tool with FunctionDeclarations for Google GenAI SDK.
    """
    if not GENAI_TYPES_AVAILABLE or types is None:
        return []

    declarations = [
        # Tool 1: search_schemes
        types.FunctionDeclaration(
            name="search_schemes",
            description=(
                "Search government welfare schemes across Karnataka State and Central Government in India. "
                "Use this tool whenever a citizen asks about schemes available for farmers, women, students, "
                "housing, health, electricity, or general social welfare."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Keywords to search scheme names, descriptions, or benefits (e.g. 'farmer subsidy', 'scholarship', 'electricity', 'women empowerment')."
                    },
                    "government_level": {
                        "type": "STRING",
                        "description": "Optional filter by level: 'State' or 'Central'."
                    },
                    "state": {
                        "type": "STRING",
                        "description": "Optional filter by state name, e.g. 'Karnataka'."
                    },
                    "category": {
                        "type": "STRING",
                        "description": "Optional category filter: 'Women and Child Development', 'Education', 'Social Welfare', 'Agriculture', 'Healthcare', 'Housing'."
                    }
                },
                "required": ["query"]
            }
        ),

        # Tool 2: retrieve_scheme_information
        types.FunctionDeclaration(
            name="retrieve_scheme_information",
            description=(
                "Retrieve grounded factual passages from official government guideline documents using keyword search. "
                "Use this to answer detailed factual questions about scheme provisions, income caps, unit limits, or rules."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Specific natural-language question or key terms to look up in official scheme guideline documents."
                    },
                    "scheme_slug": {
                        "type": "STRING",
                        "description": "Optional scheme slug to restrict retrieval strictly to that scheme's documents (e.g., 'gruha-lakshmi', 'yuva-nidhi', 'pm-kisan')."
                    },
                    "top_k": {
                        "type": "INTEGER",
                        "description": "Maximum number of relevant passages to retrieve (default: 3, max: 10)."
                    }
                },
                "required": ["query"]
            }
        ),

        # Tool 3: check_eligibility
        types.FunctionDeclaration(
            name="check_eligibility",
            description=(
                "Check a citizen's eligibility for a specific government scheme using the deterministic rule engine. "
                "You MUST invoke this tool whenever a citizen asks 'Am I eligible?' or wants to know if they qualify. "
                "Never compute or guess eligibility on your own."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "scheme_slug": {
                        "type": "STRING",
                        "description": "The exact slug identifier of the scheme to evaluate (e.g., 'gruha-lakshmi', 'yuva-nidhi', 'pm-kisan', 'gruha-jyothi', 'anna-bhagya')."
                    },
                    "citizen_profile": {
                        "type": "OBJECT",
                        "description": "Dictionary of known citizen demographic and socioeconomic attributes (e.g., age, gender, state, district, annual_household_income, occupation, is_student, graduation_year, is_bpl_card_holder, ration_card_type, is_female_head_of_family, monthly_electricity_consumption_units, landholding_acres)."
                    }
                },
                "required": ["scheme_slug", "citizen_profile"]
            }
        ),

        # Tool 4: get_required_documents
        types.FunctionDeclaration(
            name="get_required_documents",
            description=(
                "Retrieve the official document checklist for a government welfare scheme. "
                "Returns mandatory and optional document requirements with official source references."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "scheme_slug": {
                        "type": "STRING",
                        "description": "The scheme slug to retrieve the required document checklist for (e.g., 'gruha-lakshmi', 'yuva-nidhi', 'pm-kisan')."
                    }
                },
                "required": ["scheme_slug"]
            }
        ),

        # Tool 5: compare_schemes
        types.FunctionDeclaration(
            name="compare_schemes",
            description=(
                "Compare two or more government schemes side-by-side on benefits, eligibility criteria, and required documents. "
                "Use when a citizen asks to compare schemes or choose between multiple programs."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "scheme_slugs": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of 2 or more scheme slugs to compare (e.g., ['pm-kisan', 'ayushman-bharat-pmjay'])."
                    }
                },
                "required": ["scheme_slugs"]
            }
        ),

        # Tool 6: get_application_guidance
        types.FunctionDeclaration(
            name="get_application_guidance",
            description=(
                "Retrieve step-by-step application instructions and official government portal links for a welfare scheme. "
                "Use when a citizen asks how to apply or where to register."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "scheme_slug": {
                        "type": "STRING",
                        "description": "The scheme slug to get step-by-step application instructions for."
                    }
                },
                "required": ["scheme_slug"]
            }
        ),
    ]

    return [types.Tool(function_declarations=declarations)]
