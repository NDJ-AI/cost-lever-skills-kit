"""Model configurations and pricing for the cost-lever eval harness.

⏱ VERIFY BEFORE TRUSTING: model IDs and per-token prices change. The cost
column in the report is only as accurate as the PRICING table below. Model IDs
are env-overridable so you can point at whatever is current without editing code.
"""

import os
from dataclasses import dataclass


# --- Model IDs (override via env; fill in whatever's current for your provider) -

HAIKU = os.environ.get("EVAL_HAIKU_MODEL", "claude-haiku-4-5-20251001")
SONNET = os.environ.get("EVAL_SONNET_MODEL", "claude-sonnet-5")
OPUS = os.environ.get("EVAL_OPUS_MODEL", "claude-opus-4-8")
FABLE = os.environ.get("EVAL_FABLE_MODEL", "claude-fable-5")


@dataclass(frozen=True)
class Config:
    """One row in the comparison. advisor_model=None means the executor runs solo."""
    name: str
    executor_model: str
    advisor_model: str | None = None


# The configs to compare. Edit freely per task; this is the default triplet the
# advisor-lever question is really about (cheap-solo vs. cheap+advisor vs. stronger).
CONFIGS = [
    Config("haiku-solo", HAIKU, None),
    Config("haiku+opus", HAIKU, OPUS),
    Config("sonnet-solo", SONNET, None),
]


# --- Pricing: US dollars per 1,000,000 tokens, (input, output) -----------------
# ⚠ PLACEHOLDERS. Fill in from your provider's current price list before quoting
# any cost number. A model with no entry shows cost as "n/a" rather than a guess.
PRICING = {
    HAIKU: None,   # e.g. (1.00, 5.00)
    SONNET: None,  # e.g. (3.00, 15.00)
    OPUS: None,    # e.g. (15.00, 75.00)
    FABLE: None,   # e.g. (20.00, 100.00)
}


def cost_for(model: str, input_tokens: int, output_tokens: int):
    """Return dollar cost, or None if pricing for the model isn't set."""
    price = PRICING.get(model)
    if not price:
        return None
    pin, pout = price
    return (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout
