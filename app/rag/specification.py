"""Fictional structured source of truth used ONLY by reproducible dataset generators."""

SEED = 202511
TITLES = [
    ("travel", "Employee Travel and Expense Policy", "Travel", 40),
    ("meals", "Meal and Entertainment Expenses", "Meals", 40),
    ("hotel", "Hotel and Accommodation Policy", "Hotel", 180),
    ("transport", "Transportation and Mileage Reimbursement", "Transport", 80),
    ("procurement", "Procurement and Purchase Approval", "Procurement", 500),
    ("cards", "Corporate Credit Card Usage", "Corporate Card", 1000),
    ("invoices", "Invoice Processing and Duplicate Prevention", "Invoice", 10000),
    ("budgets", "Departmental Budget Control", "Budget", 5000),
    ("vendors", "Vendor Payments and Payment Terms", "Vendor Payment", 3000),
    ("reimbursement", "Expense Reimbursement and Supporting Documents", "Reimbursement", 150),
    ("authority", "Financial Delegation of Authority", "Procurement", 1000),
    ("audit", "Internal Audit and Expense Compliance", "Audit", 2500),
]


def policy_specification() -> list[dict]:
    """Rules have explicit countries/departments, dates, exceptions and ambiguous cases."""
    documents = []
    for slug, title, category, amount in TITLES:
        for version in [1, 2] if slug in {"travel", "meals"} else [1]:
            limit = 60 if slug in {"travel", "meals"} and version == 2 else amount
            documents.append(
                dict(
                    document_id=f"{slug}-policy-v{version}",
                    title=title,
                    version=str(version),
                    effective_from="2026-01-01" if version == 2 else "2025-01-01",
                    effective_to="2025-12-31"
                    if slug in {"travel", "meals"} and version == 1
                    else None,
                    department="ALL",
                    country="DE",
                    category=category,
                    status="superseded"
                    if slug in {"travel", "meals"} and version == 1
                    else "active",
                    provenance="synthetic ReportLab source; fictional company Sagebridge Demo Ltd",
                    rules=[
                        dict(
                            section_id="2.1",
                            page=2,
                            category=category,
                            country="DE",
                            department="ALL",
                            limit_eur=limit,
                            unit="per day" if slug in {"travel", "meals"} else "per transaction",
                            approval="manager",
                            receipt_required=True,
                            statement=f"{category} expenses in Germany are limited to EUR {limit:.2f} "
                            + ("per day." if slug in {"travel", "meals"} else "per transaction."),
                        ),
                        dict(
                            section_id="2.2",
                            page=2,
                            category=category,
                            country="FR",
                            department="Engineering",
                            limit_eur=limit + 25,
                            unit="per transaction",
                            approval="director",
                            receipt_required=True,
                            statement=f"Engineering {category.lower()} expenses in France have a EUR "
                            f"{limit + 25:.2f} per transaction limit and require director approval.",
                        ),
                    ],
                    exception=dict(
                        section_id="3.1",
                        page=3,
                        country="DE",
                        department="Engineering",
                        limit_eur=limit * 2,
                        approval="director",
                        statement=f"Engineering emergency {category.lower()} expenses in Germany may "
                        f"use a EUR {limit * 2:.2f} limit only with documented director approval. "
                        "Without proof of the emergency and approval, escalate for human review.",
                    ),
                    cross_reference="Financial Delegation of Authority, section 2.1; "
                    "Expense Reimbursement and Supporting Documents, section 3.1",
                )
            )
    # Missing applicability is explicitly UNKNOWN and is excluded from authoritative answers.
    documents.append(
        dict(
            documents[0],
            document_id="travel-guidance-unknown",
            title="Employee Travel Expense Guidance",
            version="UNKNOWN",
            effective_from=None,
            effective_to=None,
            department="UNKNOWN",
            country="UNKNOWN",
            status="unknown",
        )
    )
    return documents
