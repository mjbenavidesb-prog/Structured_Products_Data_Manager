import streamlit as st
import backend.config as cfg


def render():
    primary = cfg.get("primary_color") or "#2563EB"

    st.markdown(f"""
<style>
.home-hero {{
    padding: 48px 0 36px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 40px;
}}
.home-badge {{
    display: inline-block;
    background: rgba(37,99,235,0.15);
    border: 1px solid rgba(37,99,235,0.3);
    color: #93C5FD;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 20px;
}}
.home-title {{
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.04em !important;
    color: #F8FAFC !important;
    line-height: 1.15 !important;
    margin: 0 0 16px 0 !important;
}}
.home-title span {{ color: {primary}; }}
.home-subtitle {{
    font-size: 15px;
    color: #64748B;
    line-height: 1.75;
    max-width: 640px;
    margin: 0;
}}

.section-label {{
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #334155;
    margin-bottom: 20px;
    margin-top: 48px;
}}

.module-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 48px;
}}
.module-card {{
    background: #0F1C30;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 24px 24px 20px;
}}
.module-num {{
    font-size: 10px;
    font-weight: 700;
    color: {primary};
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
}}
.module-title {{
    font-size: 13.5px;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 8px;
}}
.module-desc {{
    font-size: 12px;
    color: #475569;
    line-height: 1.65;
}}
.module-tag {{
    display: inline-block;
    margin-top: 12px;
    background: rgba(37,99,235,0.1);
    color: #60A5FA;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.05em;
    padding: 3px 9px;
    border-radius: 4px;
}}

.steps-row {{
    display: flex;
    gap: 0;
    margin-bottom: 48px;
}}
.step-card {{
    flex: 1;
    padding: 24px 24px 24px 0;
}}
.step-num {{
    font-size: 10.5px;
    font-weight: 700;
    color: {primary};
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
}}
.step-title {{
    font-size: 13.5px;
    font-weight: 700;
    color: #E2E8F0;
    margin-bottom: 6px;
}}
.step-desc {{
    font-size: 12px;
    color: #475569;
    line-height: 1.6;
}}
.step-divider {{
    width: 1px;
    background: rgba(255,255,255,0.06);
    margin: 0 0 0 24px;
    align-self: stretch;
    flex-shrink: 0;
}}

.tip-box {{
    background: rgba(37,99,235,0.06);
    border: 1px solid rgba(37,99,235,0.15);
    border-radius: 8px;
    padding: 16px 20px;
    font-size: 13px;
    color: #93C5FD;
    margin-bottom: 12px;
}}
.tip-box b {{ color: #BFDBFE; }}
</style>

<div class="home-hero">
    <div class="home-badge">Structured Products Platform</div>
    <h1 class="home-title">
        Lifecycle management<br>for <span>structured products</span>
    </h1>
    <p class="home-subtitle">
        One platform to ingest termsheets with AI, monitor your portfolio in real time,
        and deliver professional client factsheets — for every product, at every stage of its lifecycle.
    </p>
</div>

<div class="section-label">Platform Modules</div>

<div class="module-grid">
    <div class="module-card">
        <div class="module-num">01 — Ingest</div>
        <div class="module-title">AI Termsheet Extraction</div>
        <div class="module-desc">
            Upload any PDF termsheet. Claude AI reads the document and
            extracts 50+ fields automatically — underlyings, barriers,
            coupon schedules, autocall triggers — in seconds.
        </div>
        <span class="module-tag">Load Product tab</span>
    </div>
    <div class="module-card">
        <div class="module-num">02 — Monitor</div>
        <div class="module-title">Portfolio Analytics</div>
        <div class="module-desc">
            AUM breakdown by asset class, strategy, counterparty, and risk
            profile. Track upcoming autocall dates, maturities, and coupon
            payment schedules across the full book.
        </div>
        <span class="module-tag">Portfolio tab</span>
    </div>
    <div class="module-card">
        <div class="module-num">03 — Alert</div>
        <div class="module-title">Event Calendar</div>
        <div class="module-desc">
            Upcoming autocall observation dates, maturity events, and coupon
            payment dates across your entire portfolio — sorted by
            proximity to today.
        </div>
        <span class="module-tag">Maturities tab</span>
    </div>
    <div class="module-card">
        <div class="module-num">04 — Deliver</div>
        <div class="module-title">Client Factsheet Generation</div>
        <div class="module-desc">
            One-click branded A4 PPTX factsheets for Autocall, Vencimiento,
            and Ejecutado events — with performance charts, Range Accrual
            coupon overlay, and payment schedules.
        </div>
        <span class="module-tag">Factsheet tab</span>
    </div>
    <div class="module-card">
        <div class="module-num">05 — Export</div>
        <div class="module-title">Excel Portfolio Reports</div>
        <div class="module-desc">
            Styled, grouped Excel reports by asset class, strategy, or
            counterparty — ready to share with compliance, management,
            or clients.
        </div>
        <span class="module-tag">Reports tab</span>
    </div>
    <div class="module-card">
        <div class="module-num">06 — Brand</div>
        <div class="module-title">Custom Branding</div>
        <div class="module-desc">
            Configure your company name, logo, and primary color.
            Every factsheet and report is generated with your
            firm's visual identity.
        </div>
        <span class="module-tag">Settings tab</span>
    </div>
</div>

<div class="section-label">How It Works</div>

<div class="steps-row">
    <div class="step-card">
        <div class="step-num">01 — Upload</div>
        <div class="step-title">Add a product</div>
        <div class="step-desc">
            Go to <b>Load Product</b>, drop a PDF termsheet,
            and Claude populates every field automatically.
            Review and save.
        </div>
    </div>
    <div class="step-divider"></div>
    <div class="step-card" style="padding-left:24px">
        <div class="step-num">02 — Track</div>
        <div class="step-title">Monitor the portfolio</div>
        <div class="step-desc">
            <b>Portfolio</b> shows live AUM analytics.
            <b>Maturities</b> shows upcoming events and
            underlying performance since inception.
        </div>
    </div>
    <div class="step-divider"></div>
    <div class="step-card" style="padding-left:24px">
        <div class="step-num">03 — Deliver</div>
        <div class="step-title">Generate the factsheet</div>
        <div class="step-desc">
            When a product autocalls or matures, go to
            <b>Factsheet</b>, select the event type, and download
            a branded PPTX ready to send to the client.
        </div>
    </div>
</div>

<div class="section-label">Quick Start</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="tip-box">
    <b>New here?</b> Start with <b>Settings</b> — upload your company logo and set your primary color.
    Then head to <b>Load Product</b> to add your first structured product via PDF termsheet.
</div>
<div class="tip-box">
    <b>Ready to generate a factsheet?</b> Make sure the product has a termsheet (underlyings + start date)
    and that the relevant observation date is in the past, then go to the <b>Factsheet</b> tab.
</div>
""", unsafe_allow_html=True)
