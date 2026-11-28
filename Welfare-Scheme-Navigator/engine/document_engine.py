"""
Document Checklist Engine for Sahaaya AI.
Generates tailored document verification checklists from official SchemeDocument models.
Allows citizens to track preparation progress without uploading sensitive files.
"""

from typing import Dict, Any, List, Optional, Union
from models import GovernmentScheme, SchemeDocument


class DocumentEngine:
    """
    Engine for generating and tracking document checklists for government schemes.
    Strictly source-grounded in SchemeDocument records. Never invents documents.
    """

    @classmethod
    def generate_checklist(
        cls,
        scheme: GovernmentScheme,
        collected_items: Optional[List[Union[str, int]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive document checklist for a scheme.
        Can evaluate collected progress using list of collected document IDs or names.
        """
        if collected_items is None:
            collected_items = []

        # Normalize collected items for flexible matching (by ID or lowercase document_name)
        collected_ids = {item for item in collected_items if isinstance(item, int)}
        collected_names = {
            str(item).strip().lower() for item in collected_items if isinstance(item, (str, int))
        }

        mandatory_docs: List[Dict[str, Any]] = []
        optional_docs: List[Dict[str, Any]] = []

        mandatory_collected_count = 0
        optional_collected_count = 0

        for doc in scheme.documents:
            # Check if citizen has marked this item as collected
            is_collected = (
                doc.id in collected_ids
                or doc.document_name.strip().lower() in collected_names
            )

            doc_entry = {
                "document_id": doc.id,
                "document_name": doc.document_name,
                "description": doc.description or "Official document required for application verification.",
                "is_mandatory": doc.is_mandatory,
                "source_reference": doc.source_reference,
                "is_collected": is_collected,
            }

            if doc.is_mandatory:
                mandatory_docs.append(doc_entry)
                if is_collected:
                    mandatory_collected_count += 1
            else:
                optional_docs.append(doc_entry)
                if is_collected:
                    optional_collected_count += 1

        total_mandatory = len(mandatory_docs)
        total_optional = len(optional_docs)
        total_documents = total_mandatory + total_optional

        # Citizen is ready to apply if all mandatory documents have been marked collected
        is_ready = (mandatory_collected_count == total_mandatory) and (total_mandatory > 0)

        # Readiness summary message
        if is_ready:
            readiness_summary = (
                f"You have prepared all {total_mandatory} mandatory document(s) for '{scheme.name}'. "
                "You are ready to proceed with the official application."
            )
        else:
            remaining = total_mandatory - mandatory_collected_count
            readiness_summary = (
                f"You need to collect {remaining} more mandatory document(s) before applying for '{scheme.name}'."
            )

        return {
            "scheme_name": scheme.name,
            "scheme_slug": scheme.slug,
            "official_url": scheme.official_url,
            "application_url": scheme.application_url,
            "total_documents": total_documents,
            "statistics": {
                "total_mandatory": total_mandatory,
                "mandatory_collected": mandatory_collected_count,
                "mandatory_pending": total_mandatory - mandatory_collected_count,
                "total_optional": total_optional,
                "optional_collected": optional_collected_count,
            },
            "is_ready_to_apply": is_ready,
            "readiness_summary": readiness_summary,
            "mandatory_documents": mandatory_docs,
            "optional_documents": optional_docs,
            "guidance_note": (
                "Sahaaya AI does not ask for or store document uploads or identification numbers. "
                "Use this checklist to prepare your documents before visiting the official portal or Seva Kendra."
            ),
        }
