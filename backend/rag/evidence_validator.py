from datetime import date, datetime
from typing import Any


class EvidenceValidator:
    """
    Validates financial evidence before it is used by the
    decision-readiness and recommendation layers.
    """

    REQUIRED_FIELDS = [
        "text",
        "source",
        "date",
        "document_type",
    ]

    def __init__(self, freshness_days: int = 365):
        """
        freshness_days:
            Configurable threshold used to classify evidence as fresh/stale.
            This is not a universal financial rule.
        """
        if freshness_days <= 0:
            raise ValueError("freshness_days must be greater than 0.")

        self.freshness_days = freshness_days

    def validate_metadata(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """
        Check whether the evidence contains the metadata required
        by the financial evidence pipeline.
        """

        missing_fields = []

        for field in self.REQUIRED_FIELDS:
            value = evidence.get(field)

            if value is None or str(value).strip() == "":
                missing_fields.append(field)

        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
        }

    def calculate_freshness(self, document_date: str) -> dict[str, Any]:
        """
        Calculate how old the evidence is.

        The result is descriptive. It does not automatically mean
        that old evidence is unreliable.
        """

        try:
            parsed_date = datetime.strptime(
                document_date,
                "%Y-%m-%d",
            ).date()
        except (ValueError, TypeError):
            return {
                "valid_date": False,
                "age_days": None,
                "is_fresh": False,
            }

        today = date.today()

        age_days = (today - parsed_date).days

        return {
            "valid_date": True,
            "age_days": age_days,
            "is_fresh": age_days <= self.freshness_days,
        }

    def calculate_relevance(
        self,
        similarity_score: float | None,
        minimum_score: float = 0.50,
    ) -> dict[str, Any]:
        """
        Evaluate retrieval relevance using the similarity score
        returned by the vector retriever.
        """

        if similarity_score is None:
            return {
                "score_available": False,
                "is_relevant": False,
            }

        score = float(similarity_score)

        return {
            "score_available": True,
            "similarity_score": score,
            "is_relevant": score >= minimum_score,
        }

    def validate_evidence(
        self,
        evidence: dict[str, Any],
        minimum_similarity: float = 0.50,
    ) -> dict[str, Any]:
        """
        Run all basic evidence validation checks.
        """

        metadata_result = self.validate_metadata(evidence)

        freshness_result = {
            "valid_date": False,
            "age_days": None,
            "is_fresh": False,
        }

        if evidence.get("date"):
            freshness_result = self.calculate_freshness(
                evidence["date"]
            )

        relevance_result = self.calculate_relevance(
            evidence.get("score"),
            minimum_score=minimum_similarity,
        )

        validation_errors = []

        if not metadata_result["valid"]:
            validation_errors.append(
                "Missing required evidence metadata."
            )

        if not freshness_result["valid_date"]:
            validation_errors.append(
                "Evidence date is missing or invalid."
            )

        if not relevance_result["score_available"]:
            validation_errors.append(
                "Retrieval similarity score is unavailable."
            )

        return {
            "metadata": metadata_result,
            "freshness": freshness_result,
            "relevance": relevance_result,
            "validation_errors": validation_errors,
            "valid": len(validation_errors) == 0,
        }