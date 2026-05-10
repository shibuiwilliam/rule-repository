"""Unit tests for surface-aware location and remediation schemas."""

from rulerepo_server.domain.evaluation import (
    CodeLocation,
    ContractLocation,
    DocumentLocation,
    HumanActionLocation,
    MessageLocation,
    Surface,
    TransactionLocation,
)
from rulerepo_server.services.evaluation.schemas import (
    build_batch_verdict_schema,
    build_verdict_schema,
    parse_location,
    validate_location_fields,
)
from rulerepo_server.services.evaluation.schemas.location_schemas import (
    CODE_LOCATION,
    CONTRACT_LOCATION,
    DOCUMENT_LOCATION,
    GENERIC_LOCATION,
    HUMAN_ACTION_LOCATION,
    MESSAGE_LOCATION,
    TRANSACTION_LOCATION,
    get_location_schema,
    get_valid_location_fields,
)
from rulerepo_server.services.evaluation.schemas.remediation_schemas import (
    CODE_REMEDIATION,
    CONTRACT_REMEDIATION,
    DOCUMENT_REMEDIATION,
    GENERIC_REMEDIATION,
    HUMAN_ACTION_REMEDIATION,
    MESSAGE_REMEDIATION,
    TRANSACTION_REMEDIATION,
    get_remediation_schema,
)


class TestLocationSchemaLookup:
    def test_code_surface_returns_code_schema(self) -> None:
        assert get_location_schema(Surface.CODE) is CODE_LOCATION

    def test_contract_surface_returns_contract_schema(self) -> None:
        assert get_location_schema(Surface.CONTRACT) is CONTRACT_LOCATION

    def test_transaction_surface_returns_transaction_schema(self) -> None:
        assert get_location_schema(Surface.TRANSACTION) is TRANSACTION_LOCATION

    def test_document_surface_returns_document_schema(self) -> None:
        assert get_location_schema(Surface.DOCUMENT) is DOCUMENT_LOCATION

    def test_message_surface_returns_message_schema(self) -> None:
        assert get_location_schema(Surface.MESSAGE) is MESSAGE_LOCATION

    def test_human_action_surface_returns_human_action_schema(self) -> None:
        assert get_location_schema(Surface.HUMAN_ACTION) is HUMAN_ACTION_LOCATION

    def test_generic_surface_returns_generic_schema(self) -> None:
        assert get_location_schema(Surface.GENERIC) is GENERIC_LOCATION

    def test_none_surface_returns_generic_schema(self) -> None:
        assert get_location_schema(None) is GENERIC_LOCATION


class TestRemediationSchemaLookup:
    def test_code_surface(self) -> None:
        assert get_remediation_schema(Surface.CODE) is CODE_REMEDIATION

    def test_contract_surface(self) -> None:
        assert get_remediation_schema(Surface.CONTRACT) is CONTRACT_REMEDIATION

    def test_transaction_surface(self) -> None:
        assert get_remediation_schema(Surface.TRANSACTION) is TRANSACTION_REMEDIATION

    def test_document_surface(self) -> None:
        assert get_remediation_schema(Surface.DOCUMENT) is DOCUMENT_REMEDIATION

    def test_message_surface(self) -> None:
        assert get_remediation_schema(Surface.MESSAGE) is MESSAGE_REMEDIATION

    def test_human_action_surface(self) -> None:
        assert get_remediation_schema(Surface.HUMAN_ACTION) is HUMAN_ACTION_REMEDIATION

    def test_none_surface(self) -> None:
        assert get_remediation_schema(None) is GENERIC_REMEDIATION


class TestBuildVerdictSchema:
    def test_code_schema_has_file_path_in_locations(self) -> None:
        schema = build_verdict_schema(Surface.CODE)
        loc_props = schema["properties"]["locations"]["items"]["properties"]
        assert "file_path" in loc_props
        assert "start_line" in loc_props
        assert "clause_ref" not in loc_props

    def test_contract_schema_has_clause_ref_in_locations(self) -> None:
        schema = build_verdict_schema(Surface.CONTRACT)
        loc_props = schema["properties"]["locations"]["items"]["properties"]
        assert "clause_ref" in loc_props
        assert "offset_start" in loc_props
        assert "file_path" not in loc_props

    def test_transaction_schema_has_json_path_in_locations(self) -> None:
        schema = build_verdict_schema(Surface.TRANSACTION)
        loc_props = schema["properties"]["locations"]["items"]["properties"]
        assert "json_path" in loc_props
        assert "field_name" in loc_props
        assert "file_path" not in loc_props

    def test_none_surface_uses_generic_schema(self) -> None:
        schema = build_verdict_schema(None)
        loc_props = schema["properties"]["locations"]["items"]["properties"]
        # Generic has all fields
        assert "file_path" in loc_props
        assert "clause_ref" in loc_props
        assert "json_path" in loc_props

    def test_schema_always_has_required_verdict_fields(self) -> None:
        for surface in Surface:
            schema = build_verdict_schema(surface)
            assert "verdict" in schema["properties"]
            assert "confidence" in schema["properties"]
            assert "reasoning" in schema["properties"]
            assert schema["required"] == ["verdict", "confidence", "reasoning"]

    def test_code_remediation_has_code_types(self) -> None:
        schema = build_verdict_schema(Surface.CODE)
        rem_props = schema["properties"]["remediations"]["items"]["properties"]
        assert "file_path" in rem_props
        assert "start_line" in rem_props
        assert set(rem_props["type"]["enum"]) == {
            "replace",
            "insert",
            "delete",
            "add_import",
            "rename",
        }

    def test_contract_remediation_has_text_rewrite_type(self) -> None:
        schema = build_verdict_schema(Surface.CONTRACT)
        rem_props = schema["properties"]["remediations"]["items"]["properties"]
        assert "clause_ref" in rem_props
        assert "requires_counterparty_consent" in rem_props
        assert "text_rewrite" in rem_props["type"]["enum"]

    def test_transaction_remediation_has_field_change_type(self) -> None:
        schema = build_verdict_schema(Surface.TRANSACTION)
        rem_props = schema["properties"]["remediations"]["items"]["properties"]
        assert "json_path" in rem_props
        assert "field_change" in rem_props["type"]["enum"]
        assert "approval_add" in rem_props["type"]["enum"]
        assert "process_reroute" in rem_props["type"]["enum"]


class TestBuildBatchVerdictSchema:
    def test_batch_schema_wraps_verdict_in_array(self) -> None:
        schema = build_batch_verdict_schema(Surface.CODE)
        assert schema["required"] == ["verdicts"]
        items = schema["properties"]["verdicts"]["items"]
        assert "rule_index" in items["properties"]
        assert "rule_id" in items["properties"]

    def test_batch_schema_inherits_surface_locations(self) -> None:
        schema = build_batch_verdict_schema(Surface.CONTRACT)
        item = schema["properties"]["verdicts"]["items"]
        loc_props = item["properties"]["locations"]["items"]["properties"]
        assert "clause_ref" in loc_props
        assert "file_path" not in loc_props


class TestParseLocation:
    def test_code_surface_returns_code_location(self) -> None:
        data = {
            "file_path": "src/main.py",
            "start_line": 10,
            "end_line": 15,
            "function_name": "handle_request",
            "snippet": "if x > 0:",
        }
        loc = parse_location(data, Surface.CODE)
        assert isinstance(loc, CodeLocation)
        assert loc.file_path == "src/main.py"
        assert loc.start_line == 10

    def test_contract_surface_returns_contract_location(self) -> None:
        data = {
            "clause_ref": "Article 3, Section 2",
            "offset_start": 100,
            "offset_end": 200,
            "span_text": "The party shall...",
        }
        loc = parse_location(data, Surface.CONTRACT)
        assert isinstance(loc, ContractLocation)
        assert loc.clause_ref == "Article 3, Section 2"
        assert loc.offset_start == 100

    def test_transaction_surface_returns_transaction_location(self) -> None:
        data = {
            "json_path": "$.amount_jpy",
            "field_name": "amount_jpy",
            "current_value": "30000",
        }
        loc = parse_location(data, Surface.TRANSACTION)
        assert isinstance(loc, TransactionLocation)
        assert loc.json_path == "$.amount_jpy"

    def test_document_surface_returns_document_location(self) -> None:
        data = {
            "section": "1.2 Scope",
            "offset_start": 50,
            "offset_end": 100,
            "span_text": "This policy applies to...",
        }
        loc = parse_location(data, Surface.DOCUMENT)
        assert isinstance(loc, DocumentLocation)
        assert loc.section == "1.2 Scope"

    def test_message_surface_returns_message_location(self) -> None:
        data = {
            "segment": "body",
            "offset_start": 0,
            "offset_end": 50,
            "span_text": "Please find attached...",
        }
        loc = parse_location(data, Surface.MESSAGE)
        assert isinstance(loc, MessageLocation)
        assert loc.segment == "body"

    def test_human_action_surface_returns_human_action_location(self) -> None:
        data = {
            "step": "overtime_submission",
            "field": "hours",
            "context": "Employee submitted 60 hours",
        }
        loc = parse_location(data, Surface.HUMAN_ACTION)
        assert isinstance(loc, HumanActionLocation)
        assert loc.step == "overtime_submission"

    def test_none_surface_returns_code_location_for_backward_compat(self) -> None:
        data = {"file_path": "test.py", "start_line": 1}
        loc = parse_location(data, None)
        assert isinstance(loc, CodeLocation)

    def test_generic_surface_returns_code_location(self) -> None:
        data = {"file_path": "test.py", "start_line": 1}
        loc = parse_location(data, Surface.GENERIC)
        assert isinstance(loc, CodeLocation)

    def test_missing_fields_use_defaults(self) -> None:
        loc = parse_location({}, Surface.CODE)
        assert isinstance(loc, CodeLocation)
        assert loc.file_path == ""
        assert loc.start_line is None


class TestValidateLocationFields:
    def test_valid_code_fields_pass_through(self) -> None:
        data = {"file_path": "test.py", "start_line": 1, "snippet": "x = 1"}
        result = validate_location_fields(data, Surface.CODE)
        assert result == data

    def test_invalid_fields_stripped_for_contract(self) -> None:
        data = {
            "clause_ref": "Article 1",
            "file_path": "contract.pdf",  # Invalid for contract
            "start_line": 5,  # Invalid for contract
        }
        result = validate_location_fields(data, Surface.CONTRACT)
        assert "clause_ref" in result
        assert "file_path" not in result
        assert "start_line" not in result

    def test_invalid_fields_stripped_for_transaction(self) -> None:
        data = {
            "json_path": "$.amount",
            "file_path": "data.json",  # Invalid for transaction
        }
        result = validate_location_fields(data, Surface.TRANSACTION)
        assert "json_path" in result
        assert "file_path" not in result

    def test_generic_surface_keeps_all_fields(self) -> None:
        data = {
            "file_path": "test.py",
            "clause_ref": "Article 1",
            "json_path": "$.x",
        }
        result = validate_location_fields(data, Surface.GENERIC)
        assert result == data

    def test_none_surface_keeps_all_fields(self) -> None:
        data = {"file_path": "test.py", "clause_ref": "Article 1"}
        result = validate_location_fields(data, None)
        assert result == data

    def test_empty_data_passes_through(self) -> None:
        result = validate_location_fields({}, Surface.CODE)
        assert result == {}


class TestValidLocationFields:
    def test_code_fields(self) -> None:
        fields = get_valid_location_fields(Surface.CODE)
        assert fields == {"file_path", "start_line", "end_line", "function_name", "snippet"}

    def test_contract_fields(self) -> None:
        fields = get_valid_location_fields(Surface.CONTRACT)
        assert fields == {"clause_ref", "offset_start", "offset_end", "span_text"}

    def test_transaction_fields(self) -> None:
        fields = get_valid_location_fields(Surface.TRANSACTION)
        assert fields == {"json_path", "field_name", "current_value"}

    def test_document_fields(self) -> None:
        fields = get_valid_location_fields(Surface.DOCUMENT)
        assert fields == {"section", "offset_start", "offset_end", "span_text"}

    def test_message_fields(self) -> None:
        fields = get_valid_location_fields(Surface.MESSAGE)
        assert fields == {"segment", "offset_start", "offset_end", "span_text"}

    def test_human_action_fields(self) -> None:
        fields = get_valid_location_fields(Surface.HUMAN_ACTION)
        assert fields == {"step", "field", "context"}

    def test_generic_has_all_fields(self) -> None:
        fields = get_valid_location_fields(Surface.GENERIC)
        # Generic should be a superset of all surface-specific fields
        for surface in Surface:
            if surface == Surface.GENERIC:
                continue
            surface_fields = get_valid_location_fields(surface)
            assert surface_fields.issubset(fields), f"{surface.value} fields {surface_fields - fields} not in generic"

    def test_none_returns_generic_fields(self) -> None:
        assert get_valid_location_fields(None) == get_valid_location_fields(Surface.GENERIC)
