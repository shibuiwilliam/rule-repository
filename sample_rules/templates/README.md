# Rule Template Packs

Pre-built rule sets for common regulatory, compliance, and operational domains. Each template provides 10-25 rules with full metadata including rationale, source references, preconditions, exceptions, and examples. Templates eliminate the cold-start problem: teams get useful, domain-accurate rules immediately.

**Important:** All templates are marked `expert_reviewed: false (reference only)`. They must be reviewed by qualified domain counsel before use for actual regulatory compliance.

---

## Business Domain Templates

### hr-attendance-jp

Japanese labor standards for attendance, working hours, overtime, breaks, leave, and worker protections.

- **Rules:** 25
- **Source authorities:** Labor Standards Act (労働基準法), Childcare and Family Care Leave Act (育児・介護休業法), 36-Agreement (三六協定), Work Style Reform Act
- **Target subject_kind:** `event`
- **Jurisdiction:** JP
- **Classification:** confidential (contains employee data references)

Covers statutory working-hour limits, overtime caps (general and special-clause), premium pay rates (25%, 35%, 50%), break requirements, annual paid leave, maternity protections, childcare accommodations, family care leave, record-keeping, and service overtime prohibition.

### contract-nda-standard

Mutual NDA review rules covering definition, scope, duration, exclusions, obligations, and remedies.

- **Rules:** 15
- **Source authorities:** Standard NDA drafting practice, trade secret statutes (Uniform Trade Secrets Act, Unfair Competition Prevention Act, EU Trade Secrets Directive)
- **Target subject_kind:** `clause_set`
- **Jurisdiction:** global
- **Classification:** confidential

Covers Confidential Information definition, standard exclusions, duration limits, symmetry in mutual NDAs, third-party disclosure restrictions, return-or-destroy obligations, non-compete scope creep, governing law, permitted recipients, notice provisions, residuals clauses, injunctive relief, auto-renewal, trade secret survival, and execution requirements.

### expense-policy-standard

Corporate expense policy rules covering travel, entertainment, receipts, approvals, tax compliance, and fraud prevention (Japan-focused with globally applicable controls).

- **Rules:** 20
- **Source authorities:** Corporation Tax Act (法人税法), Consumption Tax Act (消費税法), Rental Tax Special Measures Act (租税特別措置法), Penal Code (刑法), National Public Service Ethics Act (国家公務員倫理法), company expense policy
- **Target subject_kind:** `transaction`
- **Jurisdiction:** JP (some rules are global)
- **Classification:** internal

Covers submission timeliness, receipt requirements, personal expense prohibition, per-diem limits, travel class restrictions, international travel pre-approval, hotel rate caps, taxi justification, entertainment documentation, 5,000 JPY per-person threshold, government official entertainment, tiered approval authorities, qualified invoice compliance, foreign currency conversion, expense splitting prohibition, record retention (7 years), and credit card reconciliation.

---

## Engineering Templates

### python-fastapi

Type safety, Pydantic patterns, async conventions, logging, migrations, and CORS for Python FastAPI projects.

- **Rules:** 15
- **Target subject_kind:** `code_diff`
- **Jurisdiction:** global
- **Classification:** internal

### typescript-react

Strict TypeScript, React hooks, component conventions, state management, and error boundaries.

- **Rules:** 12
- **Target subject_kind:** `code_diff`
- **Jurisdiction:** global
- **Classification:** internal

### security-owasp

OWASP Top 10 coverage: injection, authentication, data exposure, CSRF, and rate limiting.

- **Rules:** 10
- **Target subject_kind:** `code_diff`
- **Jurisdiction:** global
- **Classification:** internal

### api-design

REST conventions, versioning, pagination, error responses, and status codes.

- **Rules:** 10
- **Target subject_kind:** `code_diff`
- **Jurisdiction:** global
- **Classification:** internal

### testing-standards

Coverage, test isolation, mocking, naming, and CI integration.

- **Rules:** 10
- **Target subject_kind:** `code_diff`
- **Jurisdiction:** global
- **Classification:** internal

---

## Compliance Templates

### bribery-anti-corruption

FCPA, UK Bribery Act, and JP Unfair Competition Prevention Act coverage -- gift thresholds, facilitation payments, third-party due diligence, government contract reviews, and whistleblowing.

- **Rules:** 18
- **Target subject_kind:** `transaction`
- **Jurisdiction:** global
- **Classification:** confidential

### data-privacy-jp

Japan APPI requirements: consent, purpose limitation, transfers, breach notification, and safety management measures.

- **Rules:** 18
- **Target subject_kind:** `document`
- **Jurisdiction:** JP
- **Classification:** confidential

### advertising-yakukiho

Japanese pharmaceutical advertising restrictions: cosmetics/supplements/devices claim restrictions, disclaimers, and endorsements.

- **Rules:** 20
- **Target subject_kind:** `creative`
- **Jurisdiction:** JP
- **Classification:** internal

---

## Importing Templates

Load a template pack via the bulk import endpoint:

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/rules/import \
  -H "Content-Type: application/yaml" \
  -d @sample_rules/templates/hr-attendance-jp.yaml

# Using the CLI
rulerepo-ingest --source template --file sample_rules/templates/hr-attendance-jp.yaml

# Load all templates at once
make seed
```

Each imported rule receives an `["imported"]` tag and starts in DRAFT status with experimental maturity (shadow mode).

## Template YAML Format

```yaml
version: 1
template:
  name: template-name
  description: "One-line description"
  tags: ["domain", "subdomain"]
rules:
  - statement: "The normative statement in RFC 2119 style"
    modality: MUST           # MUST | MUST_NOT | SHOULD | MAY | INFO
    severity: HIGH           # LOW | MEDIUM | HIGH | CRITICAL
    scope: ["domain/area"]
    tags: ["tag1", "tag2"]
    applicable_subject_types: ["event"]  # code_diff | event | clause_set | transaction | creative | decision | identity | document
    jurisdiction: JP         # JP | US | EU | global
    legal_force: statutory   # statutory | regulatory | contractual | policy | guideline
    classification: internal # public | internal | confidential | restricted
    rationale: "Why this rule exists"
    source_refs:
      - statute: "Name of law"
        article: "32"
    preconditions:
      - "Condition that must be true for the rule to apply"
    exceptions:
      - "Situation where the rule does not apply"
    following_examples:
      - "Concrete example of compliant behavior"
    violation_examples:
      - "Concrete example of non-compliant behavior"
```
