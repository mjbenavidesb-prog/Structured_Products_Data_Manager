"""
crewAI agents for the Investment Products Data Manager.
Used to satisfy the course requirement of ≥2 AI tools (Claude API + crewAI).

Agents:
  1. TermsheetAnalyst  — reads raw extracted JSON and validates / enriches it
  2. MarketDataAgent   — maps underlyings to tickers and summarises current levels
  3. ReportWriter      — generates a natural-language summary for a product event
"""

from __future__ import annotations

import json
from typing import Any

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

from backend.market_data import get_current_price, TICKER_MAP


# ── Custom tools ──────────────────────────────────────────────────────────────

if CREWAI_AVAILABLE:
    @tool("get_underlying_price")
    def get_underlying_price(ticker: str) -> str:
        """Fetch the latest price for a given underlying ticker or index name."""
        price = get_current_price(ticker)
        if price is None:
            return f"Price not available for {ticker}"
        return f"{ticker}: {price:.4f}"

    @tool("list_known_tickers")
    def list_known_tickers(dummy: str = "") -> str:
        """Return all known ticker mappings."""
        return json.dumps(TICKER_MAP, indent=2)


# ── Agent factory ─────────────────────────────────────────────────────────────

def build_crew(llm_model: str = "claude-sonnet-4-6") -> "Crew | None":
    """Build a 3-agent crew. Returns None if crewAI is not installed."""
    if not CREWAI_AVAILABLE:
        return None

    termsheet_analyst = Agent(
        role="Termsheet Analyst",
        goal=(
            "Review raw JSON extracted from a termsheet and flag any missing or "
            "inconsistent fields. Enrich the record with inferred values where possible."
        ),
        backstory=(
            "You are a senior structurer at a Latin American investment bank with 10 years "
            "of experience reading derivative termsheets across equity, rates, and credit."
        ),
        tools=[list_known_tickers],
        llm=llm_model,
        verbose=False,
        allow_delegation=False,
    )

    market_agent = Agent(
        role="Market Data Specialist",
        goal=(
            "Fetch current prices for all underlyings listed in the product record and "
            "compute the performance of each underlying relative to its strike."
        ),
        backstory=(
            "You specialise in real-time market data for equity indices, ETFs, and single "
            "stocks across US and European markets."
        ),
        tools=[get_underlying_price, list_known_tickers],
        llm=llm_model,
        verbose=False,
        allow_delegation=False,
    )

    report_writer = Agent(
        role="Client Report Writer",
        goal=(
            "Write a concise, professional English summary of a structured product event "
            "(maturity, autocall, or execution) suitable for inclusion in a client factsheet."
        ),
        backstory=(
            "You are a wealth management writer who translates complex financial data into "
            "clear, client-friendly language for high-net-worth investors."
        ),
        tools=[],
        llm=llm_model,
        verbose=False,
        allow_delegation=False,
    )

    return Crew(
        agents=[termsheet_analyst, market_agent, report_writer],
        process=Process.sequential,
        verbose=False,
    )


def validate_and_enrich(extracted_json: dict[str, Any], llm_model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    """
    Run the crewAI pipeline on an extracted termsheet JSON.
    Returns the original dict if crewAI is unavailable or fails.
    """
    if not CREWAI_AVAILABLE:
        return extracted_json

    crew = build_crew(llm_model)
    if crew is None:
        return extracted_json

    analyst_task = Task(
        description=(
            f"Review this extracted termsheet JSON and identify any missing critical fields "
            f"(underlyings, strike, maturity date, barrier, autocall trigger). "
            f"Return the corrected JSON.\n\nExtracted JSON:\n{json.dumps(extracted_json, indent=2)}"
        ),
        agent=crew.agents[0],
        expected_output="Corrected JSON object with all available fields populated",
    )

    underlyings = [
        extracted_json.get(f"underlying_{i}") for i in range(1, 5)
        if extracted_json.get(f"underlying_{i}")
    ]
    market_task = Task(
        description=(
            f"Fetch current prices for these underlyings: {underlyings}. "
            f"For each, compute performance vs strike if strike is available in the JSON. "
            f"Return a summary dict with ticker, price, strike, and performance."
        ),
        agent=crew.agents[1],
        expected_output="JSON dict with current prices and performances per underlying",
    )

    event_type = "maturity" if extracted_json.get("fecha_vencimiento") else "autocall"
    report_task = Task(
        description=(
            f"Write a 3-sentence client-ready summary for this structured product event "
            f"({event_type}). Use the corrected JSON and market data provided by the previous agents. "
            f"Tone: professional, factual, concise."
        ),
        agent=crew.agents[2],
        expected_output="A 3-sentence English summary paragraph",
    )

    crew.tasks = [analyst_task, market_task, report_task]

    try:
        result = crew.kickoff()
        enriched = extracted_json.copy()
        enriched["_crew_summary"] = str(result)
        return enriched
    except Exception:
        return extracted_json
