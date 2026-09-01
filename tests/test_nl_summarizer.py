"""Tests for ml_engine.nl_summarizer.

Uses a mocked LLM client — no actual API calls. Integration tests against
the live API are gated behind the ANTHROPIC_API_KEY env var.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ml_engine.nl_summarizer import NLSummarizer

# ── Expected output contract keys ────────────────────────────────────────────

EXPECTED_KEYS = {"asset_id", "summary", "severity", "generated_at"}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}


class MockResponse:
    """Mimics an anthropic.types.Message response."""

    def __init__(self, text: str):
        self.content = [MagicMock(text=text)]


@pytest.fixture
def mock_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    client.messages.create.return_value = MockResponse(
        json.dumps({
            "summary": "Bulldozer EQX1005 has been idling for 8 hours at Site S006, "
                       "burning an estimated $210 in fuel.",
            "severity": "HIGH",
        })
    )
    return client


@pytest.fixture
def summarizer(mock_client):
    return NLSummarizer(llm_client=mock_client)


@pytest.fixture
def sample_asset_data():
    return {
        "asset_id": "EQX1005",
        "equipment_type": "Bulldozer",
        "site_id": "S006",
        "idle_hours": 8.0,
        "engine_hours": 120.0,
        "fuel_level_pct": 45.0,
    }


@pytest.fixture
def sample_anomaly():
    return {
        "asset_id": "EQX1005",
        "is_anomaly": True,
        "anomaly_type": "EXCESSIVE_IDLE",
        "anomaly_score": 1.0,
        "detected_at": "2026-09-01T12:00:03Z",
        "reason": "Engine idling for 480 minutes",
    }


@pytest.fixture
def sample_risk():
    return {
        "asset_id": "EQX1005",
        "risk_score": 0.72,
        "risk_tier": "HIGH",
        "predicted_failure_window_days": 5,
        "contributing_factors": ["excessive_idle_ratio"],
    }


@pytest.fixture
def sample_cost():
    return {"rental_rate_per_day": 950.0, "idle_cost_per_hour": 28.75}


class TestSummarize:
    def test_output_keys_match_contract(
        self, summarizer, sample_asset_data, sample_anomaly, sample_risk, sample_cost
    ):
        result = summarizer.summarize(
            sample_asset_data, sample_anomaly, sample_risk, sample_cost
        )
        assert set(result.keys()) == EXPECTED_KEYS

    def test_severity_is_valid(
        self, summarizer, sample_asset_data, sample_anomaly, sample_risk, sample_cost
    ):
        result = summarizer.summarize(
            sample_asset_data, sample_anomaly, sample_risk, sample_cost
        )
        assert result["severity"] in VALID_SEVERITIES

    def test_asset_id_preserved(self, summarizer, sample_asset_data):
        result = summarizer.summarize(sample_asset_data)
        assert result["asset_id"] == "EQX1005"

    def test_generated_at_is_iso_format(self, summarizer, sample_asset_data):
        result = summarizer.summarize(sample_asset_data)
        # Should parse without error
        datetime.strptime(result["generated_at"], "%Y-%m-%dT%H:%M:%SZ")


class TestPromptConstruction:
    def test_prompt_includes_cost_fields(
        self, summarizer, sample_asset_data, sample_cost
    ):
        prompt = summarizer._build_prompt(
            sample_asset_data, cost_config=sample_cost
        )
        assert "950.0" in prompt
        assert "28.75" in prompt

    def test_prompt_includes_anomaly_data(
        self, summarizer, sample_asset_data, sample_anomaly
    ):
        prompt = summarizer._build_prompt(
            sample_asset_data, anomaly=sample_anomaly
        )
        assert "EXCESSIVE_IDLE" in prompt

    def test_prompt_handles_none_anomaly(self, summarizer, sample_asset_data):
        prompt = summarizer._build_prompt(sample_asset_data, anomaly=None)
        assert "None" in prompt

    def test_prompt_handles_none_risk(self, summarizer, sample_asset_data):
        prompt = summarizer._build_prompt(sample_asset_data, risk=None)
        assert "None" in prompt


class TestGracefulHandling:
    def test_summarize_without_anomaly(self, summarizer, sample_asset_data):
        result = summarizer.summarize(sample_asset_data, anomaly=None)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_summarize_without_risk(self, summarizer, sample_asset_data):
        result = summarizer.summarize(sample_asset_data, risk=None)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_summarize_without_cost(self, summarizer, sample_asset_data):
        result = summarizer.summarize(sample_asset_data, cost_config=None)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_invalid_severity_defaults_to_medium(self, sample_asset_data):
        """If LLM returns invalid severity, it should default to MEDIUM."""
        client = MagicMock()
        client.messages.create.return_value = MockResponse(
            json.dumps({"summary": "Test", "severity": "CRITICAL"})
        )
        s = NLSummarizer(llm_client=client)
        result = s.summarize(sample_asset_data)
        assert result["severity"] == "MEDIUM"


class TestSummarizeBatch:
    def test_batch_returns_list(
        self, summarizer, sample_asset_data, sample_anomaly, sample_risk, sample_cost
    ):
        items = [
            {
                "asset_data": sample_asset_data,
                "anomaly": sample_anomaly,
                "risk": sample_risk,
                "cost_config": sample_cost,
            },
            {"asset_data": sample_asset_data},
        ]
        results = summarizer.summarize_batch(items)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_batch_all_match_contract(
        self, summarizer, sample_asset_data, sample_anomaly
    ):
        items = [
            {"asset_data": sample_asset_data, "anomaly": sample_anomaly},
            {"asset_data": sample_asset_data},
        ]
        for result in summarizer.summarize_batch(items):
            assert set(result.keys()) == EXPECTED_KEYS


class TestNoClient:
    def test_raises_without_client(self, sample_asset_data):
        s = NLSummarizer(llm_client=None)
        s._client = None  # Force no client
        with pytest.raises(RuntimeError, match="No LLM client"):
            s.summarize(sample_asset_data)
