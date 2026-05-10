# Rule Client (Python SDK)

The Rule Client is a Python SDK that provides a typed, async wrapper over the Rule Repository REST API. It lives in `packages/rule-client`.

## Installation

```bash
cd packages/rule-client
uv sync
```

Or add it as a dependency in your project:

```bash
uv add rulerepo --path /path/to/packages/rule-client
```

## Initialization

```python
from rulerepo import RuleClient

# As an async context manager (recommended)
async with RuleClient("http://localhost:8000", api_key="your-key") as client:
    status = await client.health()
    print(status)  # {"status": "ok"}

# Manual lifecycle
client = RuleClient("http://localhost:8000")
# ... use client ...
await client.close()
```

Constructor parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `server_url` | str | `"http://localhost:8000"` | Base URL of the Rule Repository server. |
| `api_key` | str or None | None | API key sent via `X-API-Key` header. |
| `timeout` | float | 30.0 | Request timeout in seconds. |

## Resources

The client exposes seven resource groups: `rules`, `search`, `intent`, `documents`, `contracts`, `transactions`, and `communications`.

### Rules (CRUD)

```python
async with RuleClient("http://localhost:8000") as client:
    # Create a rule
    rule = await client.rules.create(
        statement="All API endpoints must return structured JSON errors.",
        modality="MUST",
        severity="HIGH",
        scope=["engineering/backend"],
        tags=["api", "error-handling"],
        rationale="Consistent error responses improve client integration.",
    )
    print(rule.id)

    # Get a rule by ID
    rule = await client.rules.get("a1b2c3d4-...")

    # List rules with filters
    result = await client.rules.list(page=1, page_size=10, severity="HIGH")
    for r in result.items:
        print(r.statement)

    # Update a rule
    updated = await client.rules.update(rule.id, statement="Updated statement...", revision_note="Clarified wording")

    # Retire a rule (soft-delete)
    retired = await client.rules.retire(rule.id)
```

### Revisions and Relationships

```python
    # Get revision history
    revisions = await client.rules.revisions(rule.id)
    for rev in revisions:
        print(rev.version, rev.changed_at)

    # Get relationships
    rels = await client.rules.relationships(rule.id)
    for rel in rels:
        print(rel.relationship_type, rel.target_id)
```

### Search

Five search modes are available:

```python
    # Full-text search (BM25)
    result = await client.search.fulltext("overtime monthly limit")

    # Semantic vector search
    result = await client.search.vector("rules about working hours")

    # Hybrid search (BM25 + vector)
    result = await client.search.hybrid("overtime limit", scope="hr/attendance")

    # Category search (filter only, no free-text query)
    result = await client.search.category(modality="MUST", severity="CRITICAL")
```

All search methods accept optional keyword arguments for filtering (`scope`, `modality`, `severity`, `tags`) and pagination (`page`, `page_size`).

### Intent

```python
    # Ask a natural-language question
    result = await client.intent.ask("What are the rules for refunding orders over $500?")
    print(result.intent)       # e.g., "search_rules"
    print(result.result)       # intent-specific result data
    print(result.explanation)  # human-readable explanation

    # With optional context
    result = await client.intent.ask(
        "Can we deploy on Friday?",
        context={"team": "platform", "environment": "production"},
    )
```

### Documents (Upload and Extraction)

```python
    # Upload a document
    upload = await client.documents.upload("path/to/policy.pdf")
    print(upload.document_id)

    # Upload from bytes
    upload = await client.documents.upload(pdf_bytes, filename="policy.pdf")

    # Trigger rule extraction
    extraction = await client.documents.extract(upload.document_id)
    print(extraction.candidates)  # list of candidate rules

    # Get extraction results later
    extraction = await client.documents.get_extraction(extraction.extraction_id)

    # Review extraction: approve candidates by index
    result = await client.documents.review(
        extraction.extraction_id,
        approved_indices=[0, 2, 3],
    )
    print(result["rules_created"])

    # Review with edits
    result = await client.documents.review(
        extraction.extraction_id,
        edits={
            1: {
                "statement": "Edited rule statement...",
                "modality": "SHOULD",
                "severity": "MEDIUM",
            }
        },
    )
```

### Contracts

```python
    # List contract-applicable rules
    rules = await client.contracts.list_rules(contract_type="nda")

    # Search for contract rules
    results = await client.contracts.search("indemnity clause")

    # Evaluate a contract clause
    result = await client.contracts.evaluate(
        "The Receiving Party shall protect...",
        clause_type="confidentiality",
        parties=["Acme Corp", "Beta Inc"],
    )
```

### Transactions

```python
    # List transaction-applicable rules
    rules = await client.transactions.list_rules(transaction_type="expense")

    # Search for transaction rules
    results = await client.transactions.search("expense limit")

    # Evaluate a transaction
    result = await client.transactions.evaluate(
        {"amount_jpy": 30000, "category": "entertainment"},
        transaction_type="expense",
        actor_role="manager",
    )
```

### Communications

```python
    # List communication rules
    rules = await client.communications.list_rules(channel="email")

    # Search for communication rules
    results = await client.communications.search("PII disclosure")

    # Evaluate a message
    result = await client.communications.evaluate(
        "Dear Customer, please find attached...",
        channel="email",
        audience="external",
    )
```

## Error Handling

The SDK raises typed exceptions mapped from HTTP status codes:

| Exception | HTTP Status | When |
|---|---|---|
| `NotFoundError` | 404 | Rule, document, or extraction not found. |
| `ValidationError` | 422 | Request failed validation. |
| `AuthenticationError` | 401 | Missing or invalid API key. |
| `AuthorizationError` | 403 | Insufficient permissions. |
| `ServerError` | 5xx | Server-side error. |
| `RuleRepoError` | other | Base exception for any other non-2xx response. |

All exceptions inherit from `RuleRepoError` and include `message`, `status_code`, and `code` attributes.

```python
from rulerepo.errors import NotFoundError, RuleRepoError

try:
    rule = await client.rules.get("nonexistent-id")
except NotFoundError as e:
    print(f"Rule not found: {e.message}")
except RuleRepoError as e:
    print(f"API error ({e.status_code}): {e.message}")
```

## Async Context Manager Pattern

The client uses `httpx.AsyncClient` internally. Always close the client when done, either via the context manager or by calling `await client.close()` explicitly:

```python
# Recommended
async with RuleClient("http://localhost:8000") as client:
    rules = await client.rules.list()

# Also valid
client = RuleClient("http://localhost:8000")
try:
    rules = await client.rules.list()
finally:
    await client.close()
```
