# Context engineering

The context registry represents financial meaning separately from vector search. Each asset has a
stable ID, type, version, definition, source, effective dates, business scope, owner, approval state,
precedence, validation timestamp, and content hash.

## Governance lifecycle

1. A user or extractor proposes a context asset as a draft.
2. A finance owner reviews its definition, scope, source, and effective period.
3. Explicit approval makes that version eligible for workflow use.
4. Conflicting equal-precedence definitions are flagged for human resolution.
5. Historical analysis selects the approved version applicable to its reporting date and scope.

LLM extraction never grants authority. Unknown metadata is left unknown, and conflicting sources are
not silently blended.

Implemented locally: typed assets, persistence, approval, applicability lookup, hashes, and conflict
detection. Planned: authenticated ownership, granular permissions, signed approvals, and enterprise
catalog adapters.
