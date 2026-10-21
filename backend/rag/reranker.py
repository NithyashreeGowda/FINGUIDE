import re


class EvidenceReranker:
    """
    Second-stage reranker for financial evidence.

    Combines:
    1. FAISS semantic similarity
    2. Query keyword overlap
    3. Financial concept matching
    4. Query-intent matching
    5. Strong-evidence matching
    6. Noise penalty for weak evidence
    """

    INTENT_TERMS = {
        "financial_performance": {
            "revenue",
            "profit",
            "net profit",
            "ebitda",
            "ebit",
            "earnings",
            "income",
            "growth",
            "margin",
            "sales",
            "turnover",
            "operating performance",
            "financial performance",
            "profitability",
        },
        "profitability": {
            "profit",
            "net profit",
            "profitability",
            "margin",
            "ebitda",
            "ebit",
            "earnings",
            "income",
        },
        "revenue": {
            "revenue",
            "sales",
            "turnover",
            "income",
            "operating revenue",
        },
        "cash_flow": {
            "cash flow",
            "cashflow",
            "operating cash flow",
            "investing cash flow",
            "financing cash flow",
            "cash generated",
        },
        "debt": {
            "debt",
            "borrowings",
            "loans",
            "liabilities",
            "net debt",
            "leverage",
        },
        "investment": {
            "investment",
            "investments",
            "capital expenditure",
            "capex",
            "acquisition",
            "assets",
        },
        "dividend": {
            "dividend",
            "dividends",
            "payout",
            "distribution",
        },
    }

    # Strong evidence terms are more specific than generic
    # words such as "growth", "income", or "revenue".
    EVIDENCE_TERMS = {
        "financial_performance": {
            "revenue from operations",
            "total revenue from operations",
            "profit before tax",
            "profit after tax",
            "profit after tax after nci",
            "consolidated financial statements",
            "consolidated statement of profit and loss",
            "segment revenue",
            "segment result",
            "segment results",
            "ebitda",
            "ebit",
            "financial performance and review",
        },
        "profitability": {
            "profit before tax",
            "profit after tax",
            "net profit",
            "profit margin",
            "net profit margin",
            "return on equity",
            "roce",
            "return on capital employed",
            "ebitda",
        },
        "revenue": {
            "revenue from operations",
            "total revenue from operations",
            "operating revenue",
            "segment revenue",
            "revenue growth",
            "sales revenue",
        },
        "cash_flow": {
            "cash flow from operating activities",
            "cash flow from investing activities",
            "cash flow from financing activities",
            "net cash generated",
            "operating cash flow",
        },
        "debt": {
            "total debt",
            "net debt",
            "borrowings",
            "debt equity ratio",
            "debt-equity ratio",
            "financial liabilities",
        },
        "investment": {
            "capital expenditure",
            "capital expenditures",
            "capex",
            "acquisition",
            "investments",
            "investment in subsidiaries",
        },
        "dividend": {
            "dividend per share",
            "dividend paid",
            "dividend proposed",
            "dividend payout",
        },
    }

    NOISE_PHRASES = {
        "approval of financial statements",
        "independent auditor",
        "auditor's report",
        "auditors report",
        "basis for opinion",
        "opinion",
        "secretarial auditor",
        "statutory auditor",
        "related party disclosures",
        "accounting policies",
        "notes forming part",
        "corporate governance",
        "shareholding pattern",
    }

    STOP_WORDS = {
        "what",
        "was",
        "were",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "and",
        "or",
        "for",
        "to",
        "in",
        "on",
        "with",
        "how",
        "did",
        "does",
        "this",
        "that",
        "their",
        "its",
        "company",
        "reliance",
    }

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _tokenize(self, text: str) -> list[str]:
        text = self._normalize_text(text)

        tokens = re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9-]*\b",
            text,
        )

        return [
            token
            for token in tokens
            if token not in self.STOP_WORDS
        ]

    def _detect_intent(self, query: str) -> str:
        """
        Detect the dominant financial intent from the query.
        """

        query_text = self._normalize_text(query)

        if any(
            phrase in query_text
            for phrase in [
                "financial performance",
                "financial results",
                "business performance",
            ]
        ):
            return "financial_performance"

        if any(
            phrase in query_text
            for phrase in [
                "cash flow",
                "cashflow",
            ]
        ):
            return "cash_flow"

        if any(
            phrase in query_text
            for phrase in [
                "net profit",
                "profitability",
                "profit margin",
            ]
        ):
            return "profitability"

        if any(
            phrase in query_text
            for phrase in [
                "revenue",
                "sales",
                "turnover",
            ]
        ):
            return "revenue"

        if any(
            phrase in query_text
            for phrase in [
                "debt",
                "borrowings",
                "leverage",
            ]
        ):
            return "debt"

        if any(
            phrase in query_text
            for phrase in [
                "investment",
                "investments",
                "capital expenditure",
                "capex",
                "acquisition",
            ]
        ):
            return "investment"

        if "dividend" in query_text:
            return "dividend"

        return "financial_performance"

    def _keyword_score(
        self,
        query: str,
        evidence_text: str,
    ) -> float:

        query_tokens = set(self._tokenize(query))
        evidence_tokens = set(self._tokenize(evidence_text))

        if not query_tokens:
            return 0.0

        overlap = query_tokens.intersection(evidence_tokens)

        return len(overlap) / len(query_tokens)

    def _intent_score(
        self,
        query: str,
        evidence_text: str,
    ) -> float:

        intent = self._detect_intent(query)
        evidence_text = self._normalize_text(evidence_text)

        expected_terms = self.INTENT_TERMS[intent]

        matched_terms = 0

        for term in expected_terms:
            if term in evidence_text:
                matched_terms += 1

        if not expected_terms:
            return 0.0

        score = matched_terms / min(
            max(len(expected_terms) * 0.30, 1),
            len(expected_terms),
        )

        return min(score, 1.0)

    def _evidence_score(
        self,
        query: str,
        evidence_text: str,
    ) -> float:
        """
        Measures whether the evidence contains specific
        financial-result phrases relevant to the query intent.
        """

        intent = self._detect_intent(query)
        evidence_text = self._normalize_text(evidence_text)

        expected_terms = self.EVIDENCE_TERMS.get(
            intent,
            set(),
        )

        if not expected_terms:
            return 0.0

        matched_terms = [
            term
            for term in expected_terms
            if term in evidence_text
        ]

        # Strong evidence is capped at 1.0.
        # Multiple specific financial phrases increase confidence.
        return min(len(matched_terms) / 3.0, 1.0)

    def _noise_score(
        self,
        evidence_text: str,
    ) -> float:

        evidence_text = self._normalize_text(evidence_text)

        if not evidence_text:
            return 1.0

        matches = 0

        for phrase in self.NOISE_PHRASES:
            if phrase in evidence_text:
                matches += 1

        return min(matches / 3.0, 1.0)

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
        semantic_weight: float = 0.45,
        keyword_weight: float = 0.10,
        intent_weight: float = 0.20,
        evidence_weight: float = 0.20,
        noise_penalty_weight: float = 0.05,
    ) -> list[dict]:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if not candidates:
            return []

        total_weight = (
            semantic_weight
            + keyword_weight
            + intent_weight
            + evidence_weight
            + noise_penalty_weight
        )

        if abs(total_weight - 1.0) > 0.0001:
            raise ValueError(
                "Reranker weights must add up to 1.0."
            )

        reranked = []

        for candidate in candidates:

            semantic_score = float(
                candidate.get("score", 0.0)
            )

            evidence_text = candidate.get(
                "text",
                "",
            )

            keyword_score = self._keyword_score(
                query,
                evidence_text,
            )

            intent_score = self._intent_score(
                query,
                evidence_text,
            )

            evidence_score = self._evidence_score(
                query,
                evidence_text,
            )

            noise_score = self._noise_score(
                evidence_text,
            )

            rerank_score = (
                semantic_weight * semantic_score
                + keyword_weight * keyword_score
                + intent_weight * intent_score
                + evidence_weight * evidence_score
                - noise_penalty_weight * noise_score
            )

            result = candidate.copy()

            result["semantic_score"] = semantic_score
            result["keyword_score"] = keyword_score
            result["intent_score"] = intent_score
            result["evidence_score"] = evidence_score
            result["noise_score"] = noise_score
            result["rerank_score"] = rerank_score
            result["detected_intent"] = self._detect_intent(
                query
            )

            reranked.append(result)

        reranked.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return reranked[:top_k]