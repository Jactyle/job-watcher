"""The title rule: decides whether a posting is in the watched role."""
import re

ROLE = "financial analyst"

# A title is in role when it names an analyst AND a finance topic, or is an FP&A analyst.
ANALYST = re.compile(r"\banalyst\b", re.I)
FINANCE = re.compile(
    r"\b(financ\w*|fp\s*(?:&|&amp;|and)\s*a|accounting|treasury|credit|investment|"
    r"revenue|pricing|budget\w*|forecast\w*|controller|audit\w*|equity|portfolio|"
    r"valuation|capital markets|corporate development|business planning)\b",
    re.I,
)
EXCLUDE = re.compile(r"\b(intern|internship|sales|recruit\w*|support|engineer\w*)\b", re.I)


def in_role(title: str) -> bool:
    title = title or ""
    return bool(ANALYST.search(title) and FINANCE.search(title) and not EXCLUDE.search(title))
