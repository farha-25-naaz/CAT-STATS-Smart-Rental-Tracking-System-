"""
LLM-powered natural language summarizer for fleet alerts.

Takes structured data (telemetry + anomaly + risk + cost fields) and
produces a concise natural-language summary via the Claude API.

No ML training required — this is a thin prompt-template wrapper.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


class NLSummarizer:
    """Natural language summary generator using Claude API.

    Parameters
    ----------
    llm_client : anthropic.Anthropic, optional
        An ``anthropic.Anthropic()`` client instance. If ``None``,
        creates one from the ``ANTHROPIC_API_KEY`` environment variable.
    model : str
        Claude model identifier.
    """

    _PROMPT_TEMPLATE = """\
You are a fleet operations analyst. Given the following equipment data, \
produce a concise 1-2 sentence alert summary.

Asset: {asset_data}
Anomaly detected: {anomaly}
Maintenance risk: {risk}
Cost rates: rental=${rental_rate_per_day}/day, idle=${idle_cost_per_hour}/hr

Include specific dollar amounts when idle_hours or anomaly duration is \
available. Calculate dollar impact from the idle_hours and idle_cost_per_hour \
values provided.
Severity must be one of: LOW, MEDIUM, HIGH.
Respond ONLY with valid JSON: {{"summary": "...", "severity": "..."}}"""

    def __init__(
        self,
        llm_client: Any | None = None,
        model: str = "claude-sonnet-5",
    ) -> None:
        self.model = model

        if llm_client is not None:
            self._client = llm_client
        else:
            try:
                import anthropic

                self._client = anthropic.Anthropic()
            except Exception:
                self._client = None

    # ── Prompt building ──────────────────────────────────────────────────

    def _build_prompt(
        self,
        asset_data: dict[str, Any],
        anomaly: dict[str, Any] | None = None,
        risk: dict[str, Any] | None = None,
        cost_config: dict[str, float] | None = None,
    ) -> str:
        """Render the prompt template with structured data."""
        cost = cost_config or {}
        return self._PROMPT_TEMPLATE.format(
            asset_data=json.dumps(asset_data, default=str),
            anomaly=json.dumps(anomaly, default=str) if anomaly else "None",
            risk=json.dumps(risk, default=str) if risk else "None",
            rental_rate_per_day=cost.get("rental_rate_per_day", "N/A"),
            idle_cost_per_hour=cost.get("idle_cost_per_hour", "N/A"),
        )

    # ── LLM call ─────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> dict[str, str]:
        """Send prompt to Claude and parse JSON response."""
        if self._client is None:
            raise RuntimeError(
                "No LLM client available. Set ANTHROPIC_API_KEY or pass "
                "an anthropic.Anthropic() instance to the constructor."
            )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        text = response.content[0].text.strip()

        # Parse JSON from response (handle markdown code blocks)
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"summary": text, "severity": "MEDIUM"}

        return parsed

    # ── Public API ───────────────────────────────────────────────────────

    def summarize(
        self,
        asset_data: dict[str, Any],
        anomaly: dict[str, Any] | None = None,
        risk: dict[str, Any] | None = None,
        cost_config: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Generate a natural language summary for a single asset.

        Parameters
        ----------
        asset_data : dict
            Telemetry/asset metadata (e.g. asset_id, equipment_type, idle_hours).
        anomaly : dict, optional
            Anomaly detection output for this asset.
        risk : dict, optional
            Maintenance risk assessment for this asset.
        cost_config : dict, optional
            ``{rental_rate_per_day, idle_cost_per_hour}`` for the equipment type.

        Returns
        -------
        dict
            Summary dict matching the output contract.
        """
        prompt = self._build_prompt(asset_data, anomaly, risk, cost_config)
        llm_output = self._call_llm(prompt)

        asset_id = asset_data.get("asset_id", "UNKNOWN")

        # Validate severity
        severity = llm_output.get("severity", "MEDIUM").upper()
        if severity not in ("LOW", "MEDIUM", "HIGH"):
            severity = "MEDIUM"

        return {
            "asset_id": asset_id,
            "summary": llm_output.get("summary", ""),
            "severity": severity,
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

    def summarize_batch(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate summaries for multiple assets.

        Parameters
        ----------
        items : list[dict]
            Each item has keys: ``asset_data``, and optionally
            ``anomaly``, ``risk``, ``cost_config``.

        Returns
        -------
        list[dict]
            List of summary dicts.
        """
        return [
            self.summarize(
                asset_data=item["asset_data"],
                anomaly=item.get("anomaly"),
                risk=item.get("risk"),
                cost_config=item.get("cost_config"),
            )
            for item in items
        ]
