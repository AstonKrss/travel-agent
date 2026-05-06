"""RAG - Corporate travel policy knowledge base"""

from typing import List, Optional
from backend.config import settings


class PolicyDocument:
    """Represents a single policy document."""

    def __init__(self, title: str, content: str, category: str, priority: int = 0):
        self.title = title
        self.content = content
        self.category = category
        self.priority = priority

    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "priority": self.priority,
        }


class PolicyRetriever:
    """Retrieve relevant travel policies based on query."""

    def __init__(self):
        self.documents = self._load_default_policies()

    def _load_default_policies(self) -> List[PolicyDocument]:
        """Load default corporate travel policies."""
        return [
            PolicyDocument(
                title="Flight Booking Policy",
                content=(
                    "Employees must book economy class for domestic flights under 4 hours. "
                    "Business class is allowed for international flights or domestic flights over 4 hours. "
                    "Maximum domestic flight budget: 2000 CNY. "
                    "Book at least 3 days in advance when possible."
                ),
                category="flight",
                priority=1,
            ),
            PolicyDocument(
                title="Train Booking Policy",
                content=(
                    "Second class seat is the standard for high-speed trains. "
                    "First class is allowed for trips over 6 hours. "
                    "Business class requires manager approval. "
                    "Maximum train budget: 1000 CNY."
                ),
                category="train",
                priority=1,
            ),
            PolicyDocument(
                title="Hotel Booking Policy",
                content=(
                    "Tier-1 cities (Beijing, Shanghai, Guangzhou, Shenzhen): max 600 CNY/night. "
                    "Tier-2 cities: max 400 CNY/night. "
                    "Tier-3 cities: max 300 CNY/night. "
                    "Hotel must include breakfast and WiFi. "
                    "Book through approved TMC platform."
                ),
                category="hotel",
                priority=1,
            ),
            PolicyDocument(
                title="Trip Approval Policy",
                content=(
                    "Trips under 3000 CNY total: auto-approved. "
                    "Trips 3000-10000 CNY: manager approval required. "
                    "Trips over 10000 CNY: department head approval required. "
                    "International trips: VP approval required."
                ),
                category="approval",
                priority=2,
            ),
            PolicyDocument(
                title="Expense Reimbursement Policy",
                content=(
                    "Meals: 100 CNY/day for domestic, 50 USD/day for international. "
                    "Local transport: actual cost with receipts. "
                    "Submit expense report within 30 days of trip completion. "
                    "All receipts must be uploaded with expense report."
                ),
                category="expense",
                priority=1,
            ),
            PolicyDocument(
                title="Cancellation Policy",
                content=(
                    "Free cancellation up to 24 hours before departure for trains. "
                    "Flight cancellation fees apply per airline policy. "
                    "Hotel free cancellation up to 48 hours before check-in. "
                    "Cancellation reason must be documented."
                ),
                category="cancellation",
                priority=1,
            ),
        ]

    def retrieve(self, query: str, top_k: int = 3) -> List[PolicyDocument]:
        """Retrieve relevant policies for a query.

        Uses simple keyword matching. In production, replace with vector search.
        """
        query_lower = query.lower()
        scored = []
        for doc in self.documents:
            score = 0
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()

            # Title match is worth more
            if query_lower in title_lower:
                score += 10

            # Keyword matches
            keywords = query_lower.split()
            for kw in keywords:
                if kw in content_lower:
                    score += 1
                if kw in title_lower:
                    score += 2

            if score > 0:
                scored.append((score + doc.priority, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def check_policy(self, trip_info, recommendations=None) -> List[dict]:
        """Check trip against policies and return violations."""
        from backend.schemas.state import PolicyViolation

        violations = []

        # Flight budget check
        if recommendations:
            for rec in recommendations:
                if rec.get("type") == "flight" and rec.get("price", 0) > 2000:
                    violations.append(
                        PolicyViolation(
                            rule="flight_budget",
                            message=f"Flight price {rec['price']} CNY exceeds 2000 CNY limit",
                            severity="warning",
                            suggestion="Consider economy class or earlier booking",
                        ).model_dump()
                    )
                elif rec.get("type") == "train" and rec.get("price", 0) > 1000:
                    violations.append(
                        PolicyViolation(
                            rule="train_budget",
                            message=f"Train price {rec['price']} CNY exceeds 1000 CNY limit",
                            severity="warning",
                            suggestion="Consider second class seat",
                        ).model_dump()
                    )
                elif rec.get("type") == "hotel" and rec.get("price", 0) > 600:
                    violations.append(
                        PolicyViolation(
                            rule="hotel_budget",
                            message=f"Hotel price {rec['price']} CNY/night may exceed limit",
                            severity="warning",
                            suggestion="Consider tier-2 rate or different hotel",
                        ).model_dump()
                    )

        return violations


# Singleton
_policy_retriever: Optional[PolicyRetriever] = None


def get_policy_retriever() -> PolicyRetriever:
    global _policy_retriever
    if _policy_retriever is None:
        _policy_retriever = PolicyRetriever()
    return _policy_retriever
