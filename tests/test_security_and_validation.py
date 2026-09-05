"""
Comprehensive security, validation, and reliability tests for synthetic-ehr-generator.
"""
import sys
import os
import tempfile
import pathlib
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import synthetic_ehr as sehr
from agents.base import AuditTrail, PHIGuard, AuditLogger, SecurityException, assert_no_phi


class TestPHIGuard:
    """Test PHI detection and redaction."""

    def test_mrn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-12345678 clinical note")

    def test_ssn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789 for patient")

    def test_phone_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call patient at 555-123-4567")

    def test_email_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@example.com results")

    def test_doe_john_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("John Doe admitted to ward 3")

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical specimen KEY-001 normal parameters")
        PHIGuard.assert_no_phi("Laboratory value within reference range")

    def test_empty_string_passes(self):
        PHIGuard.assert_no_phi("")

    def test_none_handled(self):
        assert_no_phi("")  # empty is fine

    def test_redaction_works(self):
        redacted = PHIGuard.redact_phi("Contact patient MRN-12345 at 555-123-4567")
        assert "REDACTED_IDENTIFIER" in redacted
        assert "MRN-12345" not in redacted
        assert "555-123-4567" not in redacted


class TestAuditTrail:
    """Test HMAC-SHA256 audit trail integrity."""

    def test_custom_key_works(self):
        trail = AuditTrail(secret_key="test-key-123")
        entry = trail.log("test", "unit", "TEST_EVENT", {"data": "value"})
        assert "current_hash" in entry
        assert entry["prev_hash"] == "GENESIS_BLOCK_0000000000000000"

    def test_chain_integrity(self):
        trail = AuditTrail(secret_key="test-key-456")
        trail.log("actor1", "tier1", "EVENT_1", {"k": "v1"})
        trail.log("actor2", "tier2", "EVENT_2", {"k": "v2"})
        trail.log("actor3", "tier3", "EVENT_3", {"k": "v3"})
        assert trail.verify_integrity() is True
        assert len(trail.get_trail()) == 3

    def test_chain_verification_after_tamper(self):
        trail = AuditTrail(secret_key="test-key-789")
        trail.log("actor1", "tier1", "EVENT_1", {"k": "v1"})
        trail.log("actor2", "tier2", "EVENT_2", {"k": "v2"})
        # Tamper with the first entry
        trail.logs[0]["current_hash"] = "TAMPERED_HASH"
        assert trail.verify_integrity() is False

    def test_phi_blocked_in_audit(self):
        trail = AuditTrail(secret_key="test-key-000")
        with pytest.raises(SecurityException):
            trail.log("actor", "tier", "EVENT", {"data": "MRN-12345 patient"})


class TestSyntheticEHRValidation:
    """Test input validation in synthetic_ehr module."""

    def test_process_csv_missing_file(self):
        with pytest.raises(FileNotFoundError):
            sehr.process_csv("nonexistent_file.csv", "output.csv")

    def test_process_csv_directory_input(self):
        with pytest.raises(ValueError, match="not a file"):
            sehr.process_csv(str(Path(__file__).parent), "output.csv")

    def test_process_csv_no_headers(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("\n")  # Empty content
            tmp = f.name
        try:
            with pytest.raises(ValueError, match="no headers"):
                sehr.process_csv(tmp, "output.csv")
        finally:
            os.unlink(tmp)

    def test_process_csv_creates_output_dir(self):
        """Test that output directory is created if it doesn't exist."""
        sample = Path(__file__).parent / "sample.csv"
        if sample.exists():
            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = Path(tmpdir) / "subdir" / "output.csv"
                rows = sehr.process_csv(str(sample), str(out_path))
                assert len(rows) >= 1
                assert out_path.exists()

    def test_lookup_returns_expected_fields(self):
        result = sehr.lookup("creatinine")
        assert "top_hit" in result
        assert "score" in result
        assert "all" in result
        assert "query" in result

    def test_lookup_case_insensitive(self):
        r1 = sehr.lookup("CREATININE")
        r2 = sehr.lookup("creatinine")
        assert r1["top_hit"] == r2["top_hit"]


class TestCLIErrorHandling:
    """Test CLI error handling for batch command."""

    def test_batch_missing_input_file(self, capsys):
        from cli import main
        result = main(["batch", "-i", "nonexistent_input_file_12345.csv"])
        assert result == 1

    def test_batch_directory_input(self, capsys):
        from cli import main
        result = main(["batch", "-i", str(Path(__file__).parent.parent)])
        assert result == 1
