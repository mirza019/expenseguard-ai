# Security and Responsible AI

- Financial tools are read-only and cannot issue payments or modify source systems.
- Upload types, sizes, ZIP expansion, rows, dates, amounts, and currencies are validated.
- Original data is retained separately from analytical normalization.
- Prompt text cannot grant authorization. Tool allowlists enforce execution boundaries.
- Retrieved policy evidence is filtered and citation-checked before explanation.
- Context changes and management reports require human review.
- Spreadsheet exports neutralize formula-leading text.
- Logs avoid raw model responses and sensitive record text where practical.

## Current limitations

The local Streamlit demo has no authentication, RBAC, tenant isolation, secret vault, or enterprise
retention policy. It should only be exposed on trusted systems. Source-level permissions, SSO,
SharePoint/Snowflake adapters, and durable audit storage are planned integration boundaries, not
implemented security controls.
