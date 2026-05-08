"""Sales context assembler — transforms sales artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class SalesContextAssembler:
    """Assembles LLM-ready context from sales artifacts.

    Handles:
    - ad_copy: advertising/marketing copy with claims, disclaimers, and medium
    - discount_request: pricing discount requests with authority and justification
    - quote: customer quotes with line items, terms, and validity
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        """Transform a sales evaluable into structured context for the LLM."""
        artifact_type = evaluable.get("artifact_type", "ad_copy")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        # Common metadata
        if department := metadata.get("department"):
            parts.append(f"Department: {department}")
        if region := metadata.get("region"):
            parts.append(f"Region: {region}")

        if artifact_type == "ad_copy":
            parts.extend(self._assemble_ad_copy(payload))
        elif artifact_type == "discount_request":
            parts.extend(self._assemble_discount_request(payload))
        elif artifact_type == "quote":
            parts.extend(self._assemble_quote(payload))
        else:
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug(
            "sales_context_assembled",
            artifact_type=artifact_type,
            length=len(context),
        )
        return context

    def _assemble_ad_copy(self, payload: dict[str, Any]) -> list[str]:
        """Build context lines for an ad_copy artifact."""
        lines: list[str] = []
        if product := payload.get("product_name"):
            lines.append(f"Product/Service: {product}")
        if audience := payload.get("target_audience"):
            lines.append(f"Target Audience: {audience}")
        if medium := payload.get("medium"):
            lines.append(f"Medium: {medium}")
        if claims := payload.get("claims"):
            if isinstance(claims, list):
                lines.append(f"Claims Made: {'; '.join(claims)}")
            else:
                lines.append(f"Claims Made: {claims}")
        if disclaimers := payload.get("disclaimers"):
            if isinstance(disclaimers, list):
                lines.append(f"Disclaimers: {'; '.join(disclaimers)}")
            else:
                lines.append(f"Disclaimers: {disclaimers}")
        if copy_text := payload.get("copy_text"):
            lines.append(f"\n--- AD COPY ---\n{copy_text}")
        return lines

    def _assemble_discount_request(self, payload: dict[str, Any]) -> list[str]:
        """Build context lines for a discount_request artifact."""
        lines: list[str] = []
        if customer := payload.get("customer"):
            lines.append(f"Customer: {customer}")
        if product := payload.get("product"):
            lines.append(f"Product: {product}")
        if standard_price := payload.get("standard_price"):
            lines.append(f"Standard Price: {standard_price}")
        if discount_pct := payload.get("discount_percent"):
            lines.append(f"Requested Discount: {discount_pct}%")
        if justification := payload.get("justification"):
            lines.append(f"Justification: {justification}")
        if authority := payload.get("authority_level"):
            lines.append(f"Authority Level: {authority}")
        return lines

    def _assemble_quote(self, payload: dict[str, Any]) -> list[str]:
        """Build context lines for a quote artifact."""
        lines: list[str] = []
        if customer := payload.get("customer"):
            lines.append(f"Customer: {customer}")
        if line_items := payload.get("line_items"):
            items_str = "\n".join(f"  - {item.get('name', 'N/A')}: {item.get('price', 'N/A')}" for item in line_items)
            lines.append(f"Line Items:\n{items_str}")
        if total := payload.get("total_price"):
            lines.append(f"Total Price: {total}")
        if terms := payload.get("terms"):
            lines.append(f"Terms: {terms}")
        if validity := payload.get("validity_period"):
            lines.append(f"Validity Period: {validity}")
        if conditions := payload.get("special_conditions"):
            lines.append(f"Special Conditions: {conditions}")
        return lines
