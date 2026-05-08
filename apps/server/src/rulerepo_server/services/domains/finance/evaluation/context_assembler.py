"""Finance context assembler — transforms financial artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class FinanceContextAssembler:
    """Assembles LLM-ready context from financial artifacts.

    Handles:
    - journal_entry: debit/credit accounts, amounts, description, preparer, approver
    - expense_request: employee, amount, category, receipts, date, purpose, approver
    - po_request: vendor, items, amounts, authority level, competitive bids
    - invoice: vendor, line items, tax calculations, invoice number, payment terms
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        """Assemble LLM-ready context from a financial evaluable artifact."""
        artifact_type = evaluable.get("artifact_type", "journal_entry")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        # Common metadata
        if department := metadata.get("department"):
            parts.append(f"Department: {department}")
        if fiscal_year := metadata.get("fiscal_year"):
            parts.append(f"Fiscal Year: {fiscal_year}")
        if currency := metadata.get("currency"):
            parts.append(f"Currency: {currency}")
        if entity := metadata.get("entity"):
            parts.append(f"Entity: {entity}")

        assembler = {
            "journal_entry": self._assemble_journal_entry,
            "expense_request": self._assemble_expense_request,
            "po_request": self._assemble_po_request,
            "invoice": self._assemble_invoice,
        }.get(artifact_type)

        if assembler:
            parts.extend(assembler(payload))
        else:
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug(
            "finance_context_assembled",
            artifact_type=artifact_type,
            length=len(context),
        )
        return context

    def _assemble_journal_entry(self, payload: dict[str, Any]) -> list[str]:
        """Assemble context for a journal entry."""
        parts: list[str] = []

        if date := payload.get("date"):
            parts.append(f"Date: {date}")
        if description := payload.get("description"):
            parts.append(f"Description: {description}")
        if preparer := payload.get("preparer"):
            parts.append(f"Preparer: {preparer}")
        if approver := payload.get("approver"):
            parts.append(f"Approver: {approver}")

        if lines := payload.get("lines"):
            parts.append("\n--- JOURNAL LINES ---")
            for i, line in enumerate(lines, 1):
                account = line.get("account", "N/A")
                debit = line.get("debit", 0)
                credit = line.get("credit", 0)
                desc = line.get("description", "")
                parts.append(f"  Line {i}: Account={account} Debit={debit} Credit={credit} {desc}")

        if total_amount := payload.get("total_amount"):
            parts.append(f"Total Amount: {total_amount}")

        return parts

    def _assemble_expense_request(self, payload: dict[str, Any]) -> list[str]:
        """Assemble context for an expense request."""
        parts: list[str] = []

        if employee := payload.get("employee"):
            parts.append(f"Employee: {employee}")
        if date := payload.get("date"):
            parts.append(f"Date: {date}")
        if amount := payload.get("amount"):
            parts.append(f"Amount: {amount}")
        if category := payload.get("category"):
            parts.append(f"Category: {category}")
        if purpose := payload.get("purpose"):
            parts.append(f"Purpose: {purpose}")
        if approver := payload.get("approver"):
            parts.append(f"Approver: {approver}")
        if receipts := payload.get("receipts"):
            if isinstance(receipts, list):
                parts.append(f"Receipts: {len(receipts)} attached")
                for r in receipts:
                    parts.append(f"  - {r}")
            else:
                parts.append(f"Receipts: {receipts}")
        else:
            parts.append("Receipts: none attached")

        return parts

    def _assemble_po_request(self, payload: dict[str, Any]) -> list[str]:
        """Assemble context for a purchase order request."""
        parts: list[str] = []

        if vendor := payload.get("vendor"):
            parts.append(f"Vendor: {vendor}")
        if requester := payload.get("requester"):
            parts.append(f"Requester: {requester}")
        if approver := payload.get("approver"):
            parts.append(f"Approver: {approver}")
        if authority_level := payload.get("authority_level"):
            parts.append(f"Authority Level: {authority_level}")
        if total_amount := payload.get("total_amount"):
            parts.append(f"Total Amount: {total_amount}")

        if items := payload.get("items"):
            parts.append("\n--- LINE ITEMS ---")
            for i, item in enumerate(items, 1):
                desc = item.get("description", "N/A")
                qty = item.get("quantity", 0)
                unit_price = item.get("unit_price", 0)
                parts.append(f"  Item {i}: {desc} qty={qty} unit_price={unit_price}")

        if competitive_bids := payload.get("competitive_bids"):
            parts.append(f"Competitive Bids: {len(competitive_bids)} submitted")
            for bid in competitive_bids:
                vendor_name = bid.get("vendor", "N/A")
                bid_amount = bid.get("amount", "N/A")
                parts.append(f"  - {vendor_name}: {bid_amount}")
        else:
            parts.append("Competitive Bids: none submitted")

        return parts

    def _assemble_invoice(self, payload: dict[str, Any]) -> list[str]:
        """Assemble context for an invoice."""
        parts: list[str] = []

        if invoice_number := payload.get("invoice_number"):
            parts.append(f"Invoice Number: {invoice_number}")
        if vendor := payload.get("vendor"):
            parts.append(f"Vendor: {vendor}")
        if date := payload.get("date"):
            parts.append(f"Date: {date}")
        if payment_terms := payload.get("payment_terms"):
            parts.append(f"Payment Terms: {payment_terms}")
        if tax_registration := payload.get("tax_registration"):
            parts.append(f"Tax Registration: {tax_registration}")

        if line_items := payload.get("line_items"):
            parts.append("\n--- LINE ITEMS ---")
            for i, item in enumerate(line_items, 1):
                desc = item.get("description", "N/A")
                amount = item.get("amount", 0)
                tax = item.get("tax", 0)
                parts.append(f"  Item {i}: {desc} amount={amount} tax={tax}")

        if subtotal := payload.get("subtotal"):
            parts.append(f"Subtotal: {subtotal}")
        if tax_amount := payload.get("tax_amount"):
            parts.append(f"Tax Amount: {tax_amount}")
        if total := payload.get("total"):
            parts.append(f"Total: {total}")

        return parts
