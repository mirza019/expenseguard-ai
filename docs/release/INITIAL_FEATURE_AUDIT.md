# Initial implementation audit

Inspected source and tests on the active docs/project-documentation branch; main remains a scaffold.

| Feature | Initial status | Evidence / gap |
|---|---|---|
| CSV/XLSX validation | Implemented and tested | services/ingestion.py, validation.py; ingestion tests |
| Four financial tools | Implemented and tested | tools/*; deterministic and workflow tests |
| DuckDB analytics | Implemented and tested | database/duckdb_service.py; workflow reconciliation |
| LangGraph + ChatOllama | Implemented and tested with mocks | agents/*; live Qwen not verified |
| Explicit Ollama setup | Implemented and tested with mocks | model_manager.py, startup tests |
| Policy extraction and citations | Partially implemented | policy_rag.py: page chunks, lexical retrieval, limited rules |
| Hierarchical metadata/index | Missing | no parent-child corpus index or applicability store |
| SentenceTransformer / FAISS / BM25 | Missing | no implementation or benchmark |
| Synthetic policy/evaluation corpus | Missing | only one fictional example policy; no RAG labels |
| Financial synthetic fixture | Implemented and tested | 1,200 rows; no broad policy-linked corpus |
| RAG metrics / evaluation UI | Missing | no measured retrieval/answer benchmarks |
| Financial scenarios / forecast | Missing | only spending and budget charts |
| PDF reports | Implemented and tested | ReportLab, validation, rendered layout tests |
| Enterprise navigation / green theme | Missing | five tabs, burgundy styling |
| Startup / CI | Implemented and tested | start.sh, matrix CI |
| Browser visual verification | Not yet verified | previous pass used AppTest and PDF rendering only |

README descriptions were not treated as proof. Final evidence is recorded in ENGINEERING_REPORT.md.
