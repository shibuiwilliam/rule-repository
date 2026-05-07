# Invoice Processing Rules

Standard operating procedures for accounts payable invoice handling.

## Qualified Invoice Requirements (インボイス制度)

Since October 2023, invoices must meet qualified invoice requirements to claim input tax credits:

1. Registered invoice issuer number (T + 13-digit number)
2. Name of the supplier
3. Transaction date
4. Description of goods/services
5. Amount (tax-exclusive), applicable tax rate(s), and tax amount
6. Name of the recipient

Invoices without a valid registered issuer number receive reduced tax-credit treatment under transitional rules.

## Processing Steps

1. **Receipt** — Log invoice in AP system on date of receipt
2. **Verification** — Three-way match: PO, goods receipt/service confirmation, invoice
3. **Coding** — Assign correct GL account, cost center, and project code
4. **Approval** — Route for approval per the authority matrix
5. **Payment** — Schedule payment per agreed terms (standard: 60 days EOM)
6. **Filing** — Archive original and digital copy; retain for 7 years

## Controls

- Segregation of duties: the person approving the PO must not approve the invoice
- Duplicate invoice detection: system must flag same vendor + same amount + same date
- Vendor master changes (bank account) require dual approval and vendor confirmation
- Invoices exceeding the PO amount by more than 5% require re-authorization

## Payment Terms

- Standard: 60 days end-of-month
- Early payment discount: 2% if paid within 10 days (where offered)
- International wire transfers: schedule 5 business days before due date
- Late payment interest: as specified in contract, or statutory default rate
