# Phase 8 Demo — Domain Engines and Discovery

> A walkthrough showing how non-engineering departments use the system.

---

## Demo 1: Contract Review (Legal Department)

### Setup
The NDA template pack from Phase 7 is already loaded with ~10 standard NDA clause rules.

### Steps

1. **Parse a contract draft:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluate/contract \
     -H "Content-Type: application/json" \
     -d '{
       "contract_text": "Article 1. Confidentiality\nAll information shared between parties is confidential for 5 years.\n\nArticle 2. Non-compete\nThe receiving party shall not compete for 10 years worldwide.\n\nArticle 3. Governing Law\nThis agreement is governed by the laws of Japan.",
       "contract_type": "nda",
       "governing_law": "japan",
       "party_role": "receiving",
       "review_type": "self_conformance"
     }'
   ```

2. **Expected response:**
   - Contract is parsed into 3 clauses (Confidentiality, Non-compete, Governing Law)
   - Each clause is evaluated against NDA rules
   - The non-compete clause (10 years worldwide) should trigger a warning
   - Per-clause verdicts with risk levels and suggested revisions are returned

3. **Frontend view:**
   - Navigate to `/contracts/review/{id}`
   - Two-pane layout: clauses on left, verdicts on right
   - Critical clauses highlighted in red, warnings in yellow

---

## Demo 2: HR Attendance Event (HR Department)

### Setup
The HR attendance template pack from Phase 7 is loaded with ~20 attendance rules.

### Steps

1. **Single event evaluation:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluate/event \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "overtime_register",
       "employee_id": "E001",
       "date": "2026-04-25",
       "overtime_hours": 10,
       "location": "jp",
       "evaluation_mode": "single"
     }'
   ```

2. **Sequence mode (monthly accumulation):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluate/event \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "overtime_register",
       "employee_id": "E001",
       "date": "2026-04-25",
       "overtime_hours": 10,
       "location": "jp",
       "evaluation_mode": "sequence",
       "event_window": {
         "start_date": "2026-04-01",
         "end_date": "2026-04-30",
         "events": [
           {"event_type": "overtime", "hours": 15},
           {"event_type": "overtime", "hours": 12},
           {"event_type": "overtime", "hours": 10}
         ],
         "aggregates": {"total_overtime_hours": 37}
       }
     }'
   ```

   With this event (10 hours), the cumulative total becomes 47 hours — exceeding the standard 45-hour monthly limit under the 36-Agreement.

3. **Calendar mode (annual ceiling):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluate/event \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "overtime_register",
       "employee_id": "E001",
       "overtime_hours": 10,
       "location": "jp",
       "evaluation_mode": "calendar",
       "calendar_context": {
         "fiscal_year": 2026,
         "ytd_overtime_hours": 690,
         "monthly_overtime": {
           "2026-04": 45, "2026-05": 50, "2026-06": 45,
           "2026-07": 50, "2026-08": 45, "2026-09": 50,
           "2026-10": 45, "2026-11": 50, "2026-12": 45,
           "2027-01": 50, "2027-02": 45, "2027-03": 0
         },
         "special_clause_active": true,
         "special_clause_limit": 100,
         "agreements": ["36-Agreement"]
       }
     }'
   ```

   YTD is 690 + 10 = 700 hours — approaching the 720-hour annual cap. Should trigger NEEDS_CONFIRMATION warning.

4. **Frontend view:**
   - Navigate to `/events/{id}`
   - Shows overall verdict, rule violations, and recommended actions

---

## Demo 3: Document Discovery (Contract Corpus Mining)

### Steps

1. **Upload historical contracts for analysis:**
   The contract corpus analyzer examines multiple contracts to extract de facto standard clauses.

2. **Discovery scan via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/discover \
     -H "Content-Type: application/json" \
     -d '{
       "source_type": "contract_corpus",
       "file_contents": {
         "contracts/nda_acme.txt": "Article 1. Confidentiality\n...",
         "contracts/nda_globex.txt": "Article 1. Confidentiality\n...",
         "contracts/nda_initech.txt": "Article 1. Confidentiality\n..."
       }
     }'
   ```

3. **Expected result:**
   - Identifies high-frequency clause types across the corpus
   - Proposes candidate standard-clause rules for Legal review
   - e.g., "Confidentiality clause present in 100% of contracts — propose as standard"

---

## Key API Endpoints Added in Phase 8

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/evaluate/contract` | Contract clause evaluation with per-clause verdicts |
| `POST /api/v1/evaluate/event` | Event evaluation with single/sequence/calendar modes |

## New Frontend Routes

| Route | Department | Purpose |
|---|---|---|
| `/contracts/review/[id]` | Legal | Clause-by-clause contract verdict view |
| `/events/[id]` | HR | Event compliance result view |
| `/transactions/[id]` | Finance | Transaction review (Phase 10 placeholder) |
| `/creatives/review/[id]` | Marketing | Creative review (Phase 10 placeholder) |
