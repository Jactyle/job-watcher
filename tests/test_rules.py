import pytest
from pipeline.rules import in_role

@pytest.mark.parametrize("title", [
    "Financial Analyst", "Senior Financial Analyst - Graphics Finance", "FP&A Analyst",
    "Finance Data Analyst", "Credit Risk Analyst II", "Investment Analyst", "Treasury Analyst",
    "Revenue Accounting Analyst", "Strategic Finance & FP&A Analyst",
    "Data Analyst", "Senior Data Analyst, Game Analytics", "BI Analyst", "Business Intelligence Analyst",
    "Product Analyst", "Analyst, Player Insights", "Gameplay Data Analyst",
])
def test_in_role(title):
    assert in_role(title)

@pytest.mark.parametrize("title", [
    "Software Engineer", "Data Scientist", "Finance Manager", "Data Center Analyst", "Security Analyst",
    "Data Analyst Intern", "Sales Data Analyst", "Financial Analyst Intern",
    "Sales Analyst, Financial Services", "Customer Support Analyst, Credit", "", None,
])
def test_not_in_role(title):
    assert not in_role(title)
