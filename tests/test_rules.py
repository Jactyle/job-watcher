import pytest
from pipeline.rules import in_role

@pytest.mark.parametrize("title", [
    "Financial Analyst", "Senior Financial Analyst - Graphics Finance", "FP&A Analyst",
    "Finance Data Analyst", "Credit Risk Analyst II", "Investment Analyst", "Treasury Analyst",
    "Revenue Accounting Analyst", "Strategic Finance & FP&A Analyst",
])
def test_in_role(title):
    assert in_role(title)

@pytest.mark.parametrize("title", [
    "Software Engineer", "Data Analyst", "Finance Manager", "Financial Analyst Intern",
    "Sales Analyst, Financial Services", "Customer Support Analyst, Credit", "", None,
])
def test_not_in_role(title):
    assert not in_role(title)
