-- ============================================================
-- Migration 001: Learning Loop — Predictions, Actuals, Parameters
-- Run once against your PostgreSQL database.
-- ============================================================

-- ── predictions ──────────────────────────────────────────────
-- One row per valuation run. Both LLM and DCF outputs captured.
CREATE TABLE IF NOT EXISTS predictions (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(20)  NOT NULL,
    company_name            VARCHAR(200),
    sector                  VARCHAR(100) DEFAULT 'Indian Equity',
    predicted_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    market_condition        VARCHAR(20)  DEFAULT 'Neutral',
    risk_free_rate          FLOAT        DEFAULT 7.2,

    -- Price context at prediction time
    price_at_prediction     FLOAT,

    -- LLM scenario outputs
    predicted_value         FLOAT,   -- probability-weighted value
    price_target            FLOAT,   -- 12-month target
    recommendation          VARCHAR(20),
    confidence              VARCHAR(20),

    bull_target             FLOAT,
    bull_probability        FLOAT,
    bull_growth_rate        FLOAT,
    base_target             FLOAT,
    base_probability        FLOAT,
    base_growth_rate        FLOAT,
    bear_target             FLOAT,
    bear_probability        FLOAT,
    bear_growth_rate        FLOAT,

    -- DCF outputs
    dcf_intrinsic           FLOAT,
    wacc_pct                FLOAT,
    dcf_margin_of_safety    FLOAT,

    -- Learning adjustments applied at generation time
    bias_correction_applied FLOAT   DEFAULT 0,
    growth_adj_applied      FLOAT   DEFAULT 0,

    -- Evaluation (filled later by EvaluationAgent)
    evaluated               BOOLEAN DEFAULT FALSE,
    evaluation_date         TIMESTAMPTZ,
    actual_price_30d        FLOAT,
    error_pct_30d           FLOAT,   -- signed: positive = overestimate
    abs_error_pct_30d       FLOAT
);

CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at);
CREATE INDEX IF NOT EXISTS idx_predictions_evaluated ON predictions(evaluated);
CREATE INDEX IF NOT EXISTS idx_predictions_sector ON predictions(sector);


-- ── price_snapshots ──────────────────────────────────────────
-- One row per (ticker, date). Populated nightly by MarketTrackingAgent.
CREATE TABLE IF NOT EXISTS price_snapshots (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(20)  NOT NULL,
    price_date  DATE         NOT NULL,
    price       FLOAT        NOT NULL,
    fetched_at  TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE(ticker, price_date)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_date ON price_snapshots(ticker, price_date);


-- ── model_parameters ─────────────────────────────────────────
-- Learned adjustments, keyed by (sector, market_condition).
-- The learning agent writes here; DCFAgent reads here.
CREATE TABLE IF NOT EXISTS model_parameters (
    id                  SERIAL PRIMARY KEY,
    sector              VARCHAR(100) NOT NULL,
    market_condition    VARCHAR(20)  NOT NULL DEFAULT 'Neutral',

    -- Additive % adjustments to FCF growth rates
    bull_growth_adj     FLOAT   DEFAULT 0.0,
    base_growth_adj     FLOAT   DEFAULT 0.0,
    bear_growth_adj     FLOAT   DEFAULT 0.0,

    -- Additive probability shifts (e.g. +0.05 means bull gets +5%)
    bull_prob_adj       FLOAT   DEFAULT 0.0,
    bear_prob_adj       FLOAT   DEFAULT 0.0,

    -- Bias correction: % to scale predicted_value by (e.g. -0.10 = reduce by 10%)
    bias_correction     FLOAT   DEFAULT 0.0,

    -- Confidence scaling: multiply confidence thresholds
    confidence_scaling  FLOAT   DEFAULT 1.0,

    -- Diagnostics
    sample_size         INTEGER DEFAULT 0,
    avg_signed_error    FLOAT,      -- positive = model overestimates
    avg_abs_error       FLOAT,
    median_abs_error    FLOAT,
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    update_notes        TEXT,

    UNIQUE(sector, market_condition)
);

-- Seed defaults for common sectors + conditions
INSERT INTO model_parameters (sector, market_condition)
VALUES
    ('Indian Equity', 'Neutral'),
    ('Indian Equity', 'Bullish'),
    ('Indian Equity', 'Bearish'),
    ('Software & IT Services', 'Neutral'),
    ('Automobile', 'Neutral'),
    ('Banking & Finance', 'Neutral'),
    ('Pharmaceuticals', 'Neutral'),
    ('Consumer Goods', 'Neutral'),
    ('Energy', 'Neutral'),
    ('Infrastructure', 'Neutral')
ON CONFLICT (sector, market_condition) DO NOTHING;


-- ── evaluation_runs ──────────────────────────────────────────
-- Audit log of every EvaluationAgent + LearningAgent run.
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id                      SERIAL PRIMARY KEY,
    run_at                  TIMESTAMPTZ DEFAULT NOW(),
    run_type                VARCHAR(30) DEFAULT 'evaluation',  -- 'evaluation' | 'learning'
    tickers_evaluated       INTEGER     DEFAULT 0,
    predictions_evaluated   INTEGER     DEFAULT 0,
    avg_signed_error        FLOAT,
    avg_abs_error           FLOAT,
    median_abs_error        FLOAT,
    within_10pct            INTEGER     DEFAULT 0,
    within_20pct            INTEGER     DEFAULT 0,
    adjustments_made        JSONB,
    run_notes               TEXT
);
