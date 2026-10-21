from datetime import date, datetime
from typing import Any
import re

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
   


def normalize_text(text: str) -> str:
    """Normalize text for simple claim/evidence comparison."""

    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.%₹,-]", "", text)

    return text.strip()



def calculate_claim_support(
    claim: str,
    evidence_text: str,
) -> dict:
    """
    Validate whether financial evidence supports a claim.

    Checks:
    - Financial metric is present.
    - Claimed numerical values are present.
    - Reporting period is checked separately.
    """

    if not claim or not claim.strip():
        raise ValueError("Claim cannot be empty.")

    if not evidence_text or not evidence_text.strip():
        return {
            "claim_support_score": 0.0,
            "claim_supported": False,
            "matched_terms": [],
            "matched_numbers": [],
            "matched_dates": [],
            "status": "NO_EVIDENCE",
        }

    claim_lower = claim.lower()
    evidence_lower = evidence_text.lower()

    # 1. Identify the financial metric.
    financial_metrics = [
        "revenue from operations",
        "profit after tax",
        "profit before tax",
        "net profit",
        "operating cash flow",
        "cash flow",
        "net debt",
        "total debt",
        "borrowings",
        "ebitda",
        "ebit",
        "dividend",
        "capital expenditure",
        "capex",
        "revenue",
    ]

    matched_terms = [
        metric
        for metric in financial_metrics
        if metric in claim_lower and metric in evidence_lower
    ]

    specific_metrics = {
        "revenue from operations",
        "profit after tax",
        "profit before tax",
        "operating cash flow",
        "net debt",
    }

    if any(metric in matched_terms for metric in specific_metrics):
        matched_terms = [
            metric
            for metric in matched_terms
            if metric not in {"revenue", "cash flow"}
        ]

    metric_supported = bool(matched_terms)

    # 2. Extract numbers, including Indian comma grouping.
    # Examples: 9,80,136 | 5,32,792 | 980136 | 26.06
    number_pattern = r"(?<![\w])(?:₹\s*)?\d[\d,]*(?:\.\d+)?"

    # Remove financial-year expressions before extracting numbers.
    year_pattern = r"\b(?:fy\s*)?20\d{2}\s*[-–]\s*\d{2,4}\b"

    claim_for_numbers = re.sub(
        year_pattern, "", claim_lower, flags=re.IGNORECASE
    )
    evidence_for_numbers = re.sub(
        year_pattern, "", evidence_lower, flags=re.IGNORECASE
    )

    def extract_numbers(text: str) -> dict:
        numbers = {}

        for match in re.finditer(number_pattern, text):
            original = match.group(0).strip()
            normalized = re.sub(r"[₹,\s]", "", original)

            if normalized:
                numbers.setdefault(normalized, original)

        return numbers

    claim_numbers = extract_numbers(claim_for_numbers)
    evidence_numbers = extract_numbers(evidence_for_numbers)

    matched_numbers = [
        claim_numbers[number]
        for number in claim_numbers
        if number in evidence_numbers
    ]

    number_supported = (
        all(number in evidence_numbers for number in claim_numbers)
        if claim_numbers
        else True
    )

    # 3. Check the reporting period separately.
    period_patterns = [
        r"\bfy\s*20\d{2}\s*[-–]\s*\d{2,4}\b",
        r"\b20\d{2}\s*[-–]\s*\d{2,4}\b",
        r"\b\d{1,2}\s+\w+\s+20\d{2}\b",
    ]

    claim_periods = []
    for pattern in period_patterns:
        claim_periods.extend(
            re.findall(pattern, claim_lower, flags=re.IGNORECASE)
        )

    matched_dates = [
        period
        for period in claim_periods
        if re.search(re.escape(period), evidence_lower)
    ]

    period_supported = (
        not claim_periods or bool(matched_dates)
    )

    # 4. Calculate the support score.
    core_score = (
        int(metric_supported) + int(number_supported)
    ) / 2

    support_score = core_score
    if claim_periods and period_supported:
        support_score = min(core_score + 0.10, 1.0)

    # 5. Determine the result.
    if metric_supported and number_supported:
        claim_supported = True
        status = "SUPPORTED"
    elif metric_supported or number_supported:
        claim_supported = False
        status = "PARTIALLY_SUPPORTED"
    else:
        claim_supported = False
        status = "NOT_SUPPORTED"

    return {
        "claim_support_score": round(support_score, 4),
        "claim_supported": claim_supported,
        "matched_terms": matched_terms,
        "matched_numbers": matched_numbers,
        "matched_dates": matched_dates,
        "status": status,
    }

def detect_evidence_conflicts(
    evidence_results: list[dict],
    metric: str,
) -> dict:
    """Detect conflicting values for the same metric and reporting scope."""

    if not evidence_results:
        return {
            "has_conflict": False,
            "status": "NO_EVIDENCE",
            "values": [],
            "conflicting_evidence": [],
        }

    metric = metric.lower().strip()

    if not metric:
        return {
            "has_conflict": False,
            "status": "NO_METRIC",
            "values": [],
            "conflicting_evidence": [],
        }

    amount_pattern = re.compile(
        r"(?<![\w,])(?:₹\s*)?"
        r"\d[\d,]*(?:\.\d+)?"
        r"(?:\s*(?:crores?|cr\.?|lakhs?|millions?|billions?))?"
        r"(?!\w)",
        re.IGNORECASE,
    )

    def normalize_amount(value: str) -> str:
        value = value.lower().replace("₹", "").replace(",", "").strip()
        value = re.sub(
            r"\s*(crores?|cr\.?|lakhs?|millions?|billions?)$",
            "",
            value,
        )
        return value.strip()

    def detect_scope(text: str) -> str:
        lowered = text.lower()
        standalone = bool(re.search(r"\bstandalone\b", lowered))
        consolidated = bool(re.search(r"\bconsolidated\b", lowered))

        if standalone and not consolidated:
            return "standalone"
        if consolidated and not standalone:
            return "consolidated"

        return "unspecified"

    # Group evidence by reporting scope, so standalone and consolidated
    # amounts are never directly compared against each other.
    grouped = {}

    for evidence in evidence_results:
        text = evidence.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue

        # Work with individual lines to avoid combining unrelated table rows.
        for line in text.splitlines():
            lowered = line.lower()
            metric_position = lowered.find(metric)

            if metric_position < 0:
                continue

            # Look only at the text after the metric.
            tail = line[metric_position + len(metric):]

            # Remove financial-year labels before looking for amounts.
            tail = re.sub(
                r"\b(?:fy\s*)?20\d{2}\s*[-–/]\s*\d{2,4}\b",
                "",
                tail,
                flags=re.IGNORECASE,
            )

            matches = list(amount_pattern.finditer(tail))

            # Ambiguous lines containing multiple numbers are skipped.
            # This prevents note numbers and table columns from being
            # treated as competing values.
            if len(matches) != 1:
                continue

            value = matches[0].group(0).strip()
            scope = detect_scope(line)
            normalized = normalize_amount(value)

            item = {
                "value": value,
                "source": evidence.get("source"),
                "page": evidence.get("page"),
                "date": evidence.get("date"),
                "company": evidence.get("company"),
                "scope": scope,
                "text": text,
            }

            grouped.setdefault(scope, {})
            grouped[scope].setdefault(normalized, []).append(item)

    conflicting_evidence = []
    conflict_values = []

    for scope, amounts in grouped.items():
        if len(amounts) > 1:
            for amount_items in amounts.values():
                conflicting_evidence.extend(amount_items)
                conflict_values.append(amount_items[0]["value"])

    if conflicting_evidence:
        return {
            "has_conflict": True,
            "status": "CONFLICTING_EVIDENCE",
            "values": sorted(set(conflict_values)),
            "conflicting_evidence": conflicting_evidence,
        }

    observed_values = sorted({
        items[0]["value"]
        for amounts in grouped.values()
        for items in amounts.values()
    })

    return {
        "has_conflict": False,
        "status": "NO_CONFLICT",
        "values": observed_values,
        "conflicting_evidence": [],
    }

def validate_evidence_source(
    evidence: dict,
    reference_date: str | date | datetime | None = None,
    source_type: str = "official_company_report",
    freshness_period_months: int = 12,
) -> dict:
    """Score a source type and determine whether its evidence is recent."""
    if freshness_period_months <= 0:
        raise ValueError("freshness_period_months must be greater than 0.")

    credibility_scores = {
        "official_company_report": 1.0,
        "regulatory_filing": 1.0,
        "audited_financial_statement": 1.0,
        "financial_news": 0.75,
        "third_party_report": 0.5,
    }
    source_credibility_score = credibility_scores.get(
        source_type.strip().lower(),
        0.0,
    )

    if reference_date is None:
        comparison_date = date.today()
    elif isinstance(reference_date, datetime):
        comparison_date = reference_date.date()
    elif isinstance(reference_date, date):
        comparison_date = reference_date
    else:
        try:
            comparison_date = date.fromisoformat(reference_date)
        except (TypeError, ValueError) as error:
            raise ValueError("reference_date must be an ISO date.") from error

    evidence_date_value = evidence.get("date")
    try:
        if isinstance(evidence_date_value, datetime):
            evidence_date = evidence_date_value.date()
        elif isinstance(evidence_date_value, date):
            evidence_date = evidence_date_value
        else:
            evidence_date = date.fromisoformat(evidence_date_value)
    except (TypeError, ValueError):
        return {
            "source": evidence.get("source"),
            "page": evidence.get("page"),
            "source_type": source_type,
            "source_credibility_score": source_credibility_score,
            "freshness_score": 0.0,
            "is_fresh": False,
        }

    age_days = (comparison_date - evidence_date).days
    freshness_period_days = freshness_period_months * 30
    is_fresh = 0 <= age_days <= freshness_period_days
    freshness_score = (
        max(0.0, 1.0 - age_days / freshness_period_days)
        if age_days >= 0
        else 0.0
    )

    return {
        "source": evidence.get("source"),
        "page": evidence.get("page"),
        "source_type": source_type,
        "source_credibility_score": source_credibility_score,
        "freshness_score": round(freshness_score, 4),
        "is_fresh": is_fresh,
    }


def validate_evidence(
    evidence_results: list[dict],
    claim: str | None = None,
    metric: str | None = None,
    reference_date=None,
    source_type: str = "official_company_report",
    freshness_period_months: int = 12,
) -> dict:
    """
    Run the complete evidence-validation pipeline.

    Checks:
    1. Source credibility
    2. Evidence freshness
    3. Claim/evidence support
    4. Evidence conflicts
    """

    if not evidence_results:
        return {
            "evidence_valid": False,
            "status": "NO_EVIDENCE",
            "source_validation": [],
            "claim_support": None,
            "conflict_detection": None,
        }

    source_validation = [
        validate_evidence_source(
            evidence=evidence,
            reference_date=reference_date,
            source_type=source_type,
            freshness_period_months=freshness_period_months,
        )
        for evidence in evidence_results
    ]

    claim_support = None
    if claim:
        combined_evidence_text = "\n\n".join(
            evidence.get("text", "")
            for evidence in evidence_results
            if evidence.get("text")
        )
        claim_support = calculate_claim_support(
            claim=claim,
            evidence_text=combined_evidence_text,
        )

    conflict_detection = None
    if metric:
        conflict_detection = detect_evidence_conflicts(
            evidence_results=evidence_results,
            metric=metric,
        )

    has_conflict = (
        conflict_detection is not None
        and conflict_detection.get("has_conflict", False)
    )
    all_fresh = all(
        result.get("is_fresh", False)
        for result in source_validation
    )
    claim_supported = (
        claim_support is None
        or claim_support.get("claim_supported", False)
    )

    if has_conflict:
        status = "CONFLICTING_EVIDENCE"
        evidence_valid = False
    elif not claim_supported:
        status = "INSUFFICIENT_SUPPORT"
        evidence_valid = False
    elif not all_fresh:
        status = "LOW_EVIDENCE"
        evidence_valid = False
    else:
        status = "VALID"
        evidence_valid = True

    return {
        "evidence_valid": evidence_valid,
        "status": status,
        "source_validation": source_validation,
        "claim_support": claim_support,
        "conflict_detection": conflict_detection,
    }