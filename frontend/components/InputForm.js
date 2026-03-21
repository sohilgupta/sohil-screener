import { useState } from 'react';
import GlassCard from './GlassCard';
import SectionTitle from './SectionTitle';

const MARKET_CONDITIONS = ['Bullish', 'Neutral', 'Bearish'];

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export default function InputForm({ onSubmit, loading = false }) {
  const [ticker, setTicker] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [allocation, setAllocation] = useState('');
  const [horizon, setHorizon] = useState('');
  const [marketCondition, setMarketCondition] = useState('');
  const [riskFreeRate, setRiskFreeRate] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    onSubmit({
      ticker: ticker.trim(),
      allocation: allocation ? parseFloat(allocation) : undefined,
      horizon: horizon ? parseInt(horizon) : undefined,
      market_condition: marketCondition || undefined,
      risk_free_rate: riskFreeRate ? parseFloat(riskFreeRate) : undefined,
    });
  };

  return (
    <GlassCard className="p-6">
      <SectionTitle
        title="Stock Analysis"
        subtitle="Enter a ticker symbol or company name — Indian &amp; US stocks supported"
      />

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        {/* Ticker input */}
        <div>
          <label className="text-subhead font-medium text-apple-text dark:text-apple-dark-text block mb-1.5">
            Stock <span className="text-apple-red">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="TCS · Apple · HDFCBANK · NVIDIA · Reliance"
              className="apple-input pr-10"
              required
              disabled={loading}
            />
            {ticker && (
              <button
                type="button"
                onClick={() => setTicker('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-apple-secondary-text hover:text-apple-text"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          <p className="mt-1.5 ml-1 text-caption text-apple-secondary-text dark:text-apple-dark-secondary">
            Type a <span className="font-semibold">ticker symbol</span> or <span className="font-semibold">company name</span> — AI resolves it automatically.
            {' '}Indian: <span className="font-mono">TCS</span>, <span className="font-mono">HDFCBANK</span> · US: <span className="font-mono">Apple</span>, <span className="font-mono">NVDA</span>
          </p>
        </div>

        {/* Advanced Options Toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1.5 text-apple-blue text-subhead font-medium"
        >
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${showAdvanced ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          {showAdvanced ? 'Hide' : 'Show'} optional parameters
        </button>

        {showAdvanced && (
          <div className="space-y-4 pt-1">
            <div className="grid grid-cols-2 gap-3">
              {/* Allocation */}
              <div>
                <label className="text-footnote font-medium text-apple-secondary-text dark:text-apple-dark-secondary block mb-1.5">
                  Portfolio Allocation (%)
                </label>
                <input
                  type="number"
                  value={allocation}
                  onChange={(e) => setAllocation(e.target.value)}
                  placeholder="e.g. 10"
                  min="0"
                  max="100"
                  className="apple-input"
                  disabled={loading}
                />
              </div>

              {/* Horizon */}
              <div>
                <label className="text-footnote font-medium text-apple-secondary-text dark:text-apple-dark-secondary block mb-1.5">
                  Investment Horizon (years)
                </label>
                <input
                  type="number"
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  placeholder="e.g. 3"
                  min="1"
                  max="30"
                  className="apple-input"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Market Condition */}
            <div>
              <label className="text-footnote font-medium text-apple-secondary-text dark:text-apple-dark-secondary block mb-1.5">
                Market Condition{' '}
                <span className="font-normal text-apple-secondary-text">(auto-detected if blank)</span>
              </label>
              <div className="flex gap-2">
                {MARKET_CONDITIONS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMarketCondition(marketCondition === m ? '' : m)}
                    className={`flex-1 py-2 rounded-apple text-subhead font-medium transition-all duration-150 border
                      ${marketCondition === m
                        ? m === 'Bullish'
                          ? 'bg-apple-green/10 border-apple-green/40 text-apple-green'
                          : m === 'Bearish'
                          ? 'bg-apple-red/10 border-apple-red/40 text-apple-red'
                          : 'bg-apple-blue/10 border-apple-blue/40 text-apple-blue'
                        : 'bg-apple-secondary-bg dark:bg-apple-dark-elevated border-transparent text-apple-secondary-text hover:text-apple-text dark:hover:text-apple-dark-text'
                      }`}
                    disabled={loading}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* Risk-free rate */}
            <div>
              <label className="text-footnote font-medium text-apple-secondary-text dark:text-apple-dark-secondary block mb-1.5">
                Risk-Free Rate (%) <span className="font-normal">(default: 7.2% India · 4.5% US)</span>
              </label>
              <input
                type="number"
                value={riskFreeRate}
                onChange={(e) => setRiskFreeRate(e.target.value)}
                placeholder="7.2"
                min="0"
                max="20"
                step="0.1"
                className="apple-input"
                disabled={loading}
              />
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={!ticker.trim() || loading}
          className="btn-primary w-full mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Spinner />
              Analyzing {ticker}…
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Run Valuation
            </span>
          )}
        </button>
      </form>
    </GlassCard>
  );
}
