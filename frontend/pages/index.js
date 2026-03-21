import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

import GlassCard from '../components/GlassCard';
import SectionTitle from '../components/SectionTitle';
import MetricDisplay from '../components/MetricDisplay';
import ScenarioCard from '../components/ScenarioCard';
import StockTable from '../components/StockTable';
import Charts from '../components/Charts';
import InputForm from '../components/InputForm';
import PortfolioUpload from '../components/PortfolioUpload';
import LoadingSkeleton from '../components/LoadingSkeleton';
import DCFPanel from '../components/DCFPanel';
import LearningPanel from '../components/LearningPanel';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Helpers ────────────────────────────────────────────────────────────────
const fmt = (n, prefix = '₹') =>
  n != null ? `${prefix}${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—';

const fmtPct = (n) => {
  if (n == null) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${Number(n).toFixed(1)}%`;
};

const recColor = (rec) => {
  if (!rec) return 'text-apple-secondary-text';
  if (rec.toLowerCase() === 'buy') return 'text-apple-green';
  if (rec.toLowerCase() === 'exit') return 'text-apple-red';
  return 'text-apple-orange';
};

const confBadge = (conf) => {
  const map = { High: 'pill-green', Medium: 'pill-orange', Low: 'pill-red' };
  return map[conf] || 'pill-blue';
};

// ─── Dark Mode Toggle ────────────────────────────────────────────────────────
function DarkModeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains('dark'));
  }, []);

  const toggle = () => {
    const newDark = !dark;
    setDark(newDark);
    document.documentElement.classList.toggle('dark', newDark);
    localStorage.setItem('theme', newDark ? 'dark' : 'light');
  };

  return (
    <button
      onClick={toggle}
      className="p-2 rounded-full hover:bg-apple-secondary-bg dark:hover:bg-apple-dark-elevated transition-colors"
      aria-label="Toggle dark mode"
    >
      {dark ? (
        <svg className="w-5 h-5 text-apple-dark-text" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-apple-text" fill="currentColor" viewBox="0 0 20 20">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
    </button>
  );
}

// ─── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-apple-dark/80 backdrop-blur-xl border-b border-apple-separator/30 dark:border-apple-dark-separator/30">
      <div className="max-w-content mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-apple-blue rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <span className="font-semibold text-apple-text dark:text-apple-dark-text text-[15px]">
            Valuation Engine
          </span>
        </div>
        <DarkModeToggle />
      </div>
    </nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────
function Hero({ onTabSelect }) {
  return (
    <section className="pt-20 pb-16 px-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <p className="text-footnote font-semibold text-apple-blue uppercase tracking-widest mb-4">
          AI-Powered Analysis
        </p>
        <h1 className="text-5xl sm:text-6xl font-bold text-apple-text dark:text-apple-dark-text mb-5 leading-tight tracking-tight">
          AI Valuation
          <br />
          <span className="text-apple-blue">Engine</span>
        </h1>
        <p className="text-xl text-apple-secondary-text dark:text-apple-dark-secondary max-w-xl mx-auto mb-10 font-light">
          Professional stock valuations powered by AI + financial models.
          Built for Indian equities.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button onClick={() => onTabSelect('single')} className="btn-primary gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Analyze Stock
          </button>
          <button onClick={() => onTabSelect('multiple')} className="btn-secondary gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            Multiple Stocks
          </button>
          <button onClick={() => onTabSelect('portfolio')} className="btn-secondary gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Upload Portfolio
          </button>
        </div>
      </motion.div>
    </section>
  );
}

// ─── Tab Bar ──────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'single', label: 'Single Stock' },
  { id: 'multiple', label: 'Multiple Stocks' },
  { id: 'portfolio', label: 'Portfolio Upload' },
  { id: 'learning', label: 'Learning' },
];

function TabBar({ active, onChange }) {
  return (
    <div className="flex justify-center px-4 mb-10">
      <div className="inline-flex bg-apple-secondary-bg dark:bg-apple-dark-elevated rounded-apple p-1 gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`relative px-5 py-2 rounded-[10px] text-subhead font-medium transition-all duration-200
              ${active === tab.id
                ? 'text-apple-text dark:text-apple-dark-text shadow-apple'
                : 'text-apple-secondary-text dark:text-apple-dark-secondary hover:text-apple-text dark:hover:text-apple-dark-text'
              }`}
          >
            {active === tab.id && (
              <motion.div
                layoutId="tab-bg"
                className="absolute inset-0 bg-white dark:bg-apple-dark-card rounded-[10px] shadow-apple"
                style={{ zIndex: -1 }}
              />
            )}
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Single Stock Result ──────────────────────────────────────────────────────
function SingleStockResult({ data }) {
  const { stock_data: sd, analysis: an, dcf_result: dcf } = data;
  const [showFull, setShowFull] = useState(false);

  // Detect empty scrape — all key financials null means the ticker wasn't found
  const hasFinancialData = sd.current_price != null || sd.revenue != null || sd.market_cap != null;
  if (!hasFinancialData) {
    return (
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <GlassCard className="p-6">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-apple-orange flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="font-semibold text-apple-text dark:text-apple-dark-text mb-1">
                No data found for <span className="font-mono text-apple-blue">{sd.ticker}</span>
              </p>
              <p className="text-subhead text-apple-secondary-text dark:text-apple-dark-secondary leading-relaxed">
                This usually means the symbol wasn&apos;t found on screener.in. Make sure you&apos;re entering the <strong>NSE/BSE trading symbol</strong>, not the company name.
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-footnote">
                {[['Ola Electric','OLAELEC'],['HDFC Bank','HDFCBANK'],['Reliance','RELIANCE'],['TCS','TCS'],['Zomato','ZOMATO']].map(([name, sym]) => (
                  <span key={sym} className="px-2 py-1 bg-apple-secondary-bg dark:bg-apple-dark-elevated rounded-md text-apple-secondary-text">
                    {name} → <span className="font-mono font-semibold text-apple-blue">{sym}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    );
  }

  const upside = an.upside_percentage;
  const upsideColor = upside >= 0 ? 'text-apple-green' : 'text-apple-red';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Overview Card */}
      <GlassCard className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary uppercase tracking-wider font-medium mb-1">
              {sd.ticker} · {sd.industry}
            </p>
            <h2 className="text-headline text-apple-text dark:text-apple-dark-text">
              {sd.company_name}
            </h2>
            {sd.competitors?.length > 0 && (
              <p className="text-footnote text-apple-secondary-text mt-1">
                Peers: {sd.competitors.slice(0, 3).join(', ')}
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-footnote text-apple-secondary-text mb-1">Current Price</p>
            <p className="text-3xl font-bold text-apple-text dark:text-apple-dark-text">
              {fmt(sd.current_price)}
            </p>
            <p className="text-footnote text-apple-secondary-text mt-1">
              MCap: {fmt(sd.market_cap, '₹')} Cr
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Fair Value + Recommendation */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricDisplay
          label="Current Price"
          value={fmt(sd.current_price)}
          secondary={`P/E ${sd.pe_ratio?.toFixed(1) || '—'}x`}
        />
        <MetricDisplay
          label="Fair Value"
          value={fmt(an.probability_weighted_value)}
          secondary="Probability Weighted"
          highlight
        />
        <MetricDisplay
          label="Upside"
          value={fmtPct(upside)}
          secondary={`${an.recommendation || '—'} · ${an.confidence_level || '—'} confidence`}
          color={upsideColor}
        />
      </div>

      {/* Scenario Cards */}
      <div>
        <SectionTitle title="Scenario Analysis" subtitle="Bull, Base, and Bear case valuations" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          <ScenarioCard
            type="bull"
            targetPrice={an.bull_case?.target_price}
            probability={an.bull_case?.probability}
            growthRate={an.bull_case?.growth_rate}
            assumptions={an.bull_case?.key_assumptions}
            currentPrice={sd.current_price}
          />
          <ScenarioCard
            type="base"
            targetPrice={an.base_case?.target_price}
            probability={an.base_case?.probability}
            growthRate={an.base_case?.growth_rate}
            assumptions={an.base_case?.key_assumptions}
            currentPrice={sd.current_price}
          />
          <ScenarioCard
            type="bear"
            targetPrice={an.bear_case?.target_price}
            probability={an.bear_case?.probability}
            growthRate={an.bear_case?.growth_rate}
            assumptions={an.bear_case?.key_assumptions}
            currentPrice={sd.current_price}
          />
        </div>
      </div>

      {/* Charts */}
      <Charts
        mode="single"
        currentPrice={sd.current_price}
        bullTarget={an.bull_case?.target_price}
        baseTarget={an.base_case?.target_price}
        bearTarget={an.bear_case?.target_price}
        pwv={an.probability_weighted_value}
      />

      {/* DCF Valuation Panel */}
      {dcf && <DCFPanel dcf={dcf} />}

      {/* Financial Snapshot */}
      <GlassCard className="p-6">
        <SectionTitle title="Financial Snapshot" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          {[
            { label: 'Revenue (TTM)', value: fmt(sd.revenue, '₹') + ' Cr' },
            { label: 'EBITDA', value: fmt(sd.ebitda, '₹') + ' Cr' },
            { label: 'Net Income', value: fmt(sd.net_income, '₹') + ' Cr' },
            { label: 'Free Cash Flow', value: fmt(sd.fcf, '₹') + ' Cr' },
            { label: 'Debt/Equity', value: sd.de_ratio?.toFixed(2) ?? '—' },
            { label: 'ROE', value: sd.roe ? sd.roe.toFixed(1) + '%' : '—' },
            { label: 'EBITDA Margin', value: sd.opm ? sd.opm.toFixed(1) + '%' : '—' },
            { label: 'Book Value', value: sd.book_value ? fmt(sd.book_value) : '—' },
          ].map((m) => (
            <div key={m.label} className="p-4 bg-apple-secondary-bg dark:bg-apple-dark-elevated rounded-apple">
              <p className="text-footnote text-apple-secondary-text mb-1">{m.label}</p>
              <p className="text-callout font-semibold text-apple-text dark:text-apple-dark-text">{m.value}</p>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Risk + Valuation Methods */}
      {(an.key_risks?.length > 0 || an.valuation_methods?.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {an.key_risks?.length > 0 && (
            <GlassCard className="p-6">
              <SectionTitle title="Key Risks" />
              <ul className="mt-3 space-y-2">
                {an.key_risks.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-subhead text-apple-secondary-text dark:text-apple-dark-secondary">
                    <span className="text-apple-red mt-0.5">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </GlassCard>
          )}
          {an.valuation_methods?.length > 0 && (
            <GlassCard className="p-6">
              <SectionTitle title="Valuation Methods Used" />
              <div className="mt-3 flex flex-wrap gap-2">
                {an.valuation_methods.map((m, i) => (
                  <span key={i} className="pill-blue">{m}</span>
                ))}
              </div>
              {an.executive_summary && (
                <p className="mt-4 text-subhead text-apple-secondary-text dark:text-apple-dark-secondary leading-relaxed">
                  {an.executive_summary}
                </p>
              )}
            </GlassCard>
          )}
        </div>
      )}

      {/* Full Analysis (expandable) */}
      {an.analysis_text && (
        <GlassCard className="p-6">
          <div className="flex items-center justify-between mb-4">
            <SectionTitle title="Full AI Analysis" />
            <button
              onClick={() => setShowFull(!showFull)}
              className="text-apple-blue text-footnote font-medium hover:underline"
            >
              {showFull ? 'Show less' : 'Read full analysis'}
            </button>
          </div>
          <div
            className={`overflow-hidden transition-all duration-500 ${showFull ? 'max-h-[9999px]' : 'max-h-40'}`}
          >
            <pre className="text-subhead text-apple-secondary-text dark:text-apple-dark-secondary whitespace-pre-wrap font-sans leading-relaxed">
              {an.analysis_text}
            </pre>
          </div>
          {!showFull && (
            <div className="h-12 bg-gradient-to-t from-white dark:from-apple-dark-card to-transparent -mt-12 relative pointer-events-none" />
          )}
        </GlassCard>
      )}
    </motion.div>
  );
}

// ─── Multiple Stocks Result ───────────────────────────────────────────────────
function MultipleStocksResult({ rows }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <SectionTitle
        title="Comparison Table"
        subtitle={`${rows.length} stocks analyzed`}
      />
      <StockTable rows={rows} />
      <Charts
        mode="portfolio"
        portfolioData={rows.map((r) => ({
          name: r.ticker,
          upside: r.upside_percentage,
          current: r.current_price,
          pwv: r.probability_weighted_value,
        }))}
      />
    </motion.div>
  );
}

// ─── Portfolio Result ─────────────────────────────────────────────────────────
function PortfolioResult({ data }) {
  const { holdings, analysis, portfolio = {} } = data;
  const summary = portfolio.summary || {};
  const rebalance = portfolio.rebalance || [];
  const allocation = portfolio.allocation || {};

  const total_invested = summary.total_invested || analysis.reduce((s, r) => s + (r.total_invested_value || 0), 0);
  const total_current = summary.total_current_value || analysis.reduce((s, r) => s + (r.total_current_value || 0), 0);
  const total_pnl = total_current - total_invested;
  const total_pnl_pct = total_invested > 0 ? (total_pnl / total_invested) * 100 : 0;

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Portfolio summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricDisplay label="Total Invested" value={fmt(total_invested)} />
        <MetricDisplay label="Current Value" value={fmt(total_current)} highlight />
        <MetricDisplay
          label="Total P&L"
          value={fmt(Math.abs(total_pnl))}
          secondary={fmtPct(total_pnl_pct)}
          color={total_pnl >= 0 ? 'text-apple-green' : 'text-apple-red'}
        />
        {summary.total_upside_pct != null && (
          <MetricDisplay
            label="Portfolio Upside"
            value={fmtPct(summary.total_upside_pct)}
            secondary={summary.diversification || ''}
            color={summary.total_upside_pct >= 0 ? 'text-apple-green' : 'text-apple-red'}
          />
        )}
      </div>

      {/* Rebalancing suggestions */}
      {rebalance.length > 0 && (
        <GlassCard className="p-6">
          <SectionTitle title="Rebalancing Suggestions" subtitle="Agent-generated action plan" />
          <div className="mt-4 space-y-3">
            {rebalance.map((r, i) => {
              const actionColor =
                r.action === 'Add' ? 'text-apple-green border-apple-green/30 bg-apple-green/5' :
                r.action === 'Exit' ? 'text-apple-red border-apple-red/30 bg-apple-red/5' :
                'text-apple-orange border-apple-orange/30 bg-apple-orange/5';
              return (
                <div key={i} className={`flex items-center justify-between p-3 rounded-apple border ${actionColor}`}>
                  <div>
                    <p className="font-semibold text-sm">{r.company_name || r.ticker}</p>
                    <p className="text-footnote opacity-70 mt-0.5">{r.rationale}</p>
                  </div>
                  <span className="ml-4 font-bold text-sm flex-shrink-0">{r.action}</span>
                </div>
              );
            })}
          </div>
        </GlassCard>
      )}

      {/* Sector allocation */}
      {Object.keys(allocation).length > 0 && (
        <GlassCard className="p-6">
          <SectionTitle title="Sector Allocation" />
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(allocation).map(([sector, pct]) => (
              <div key={sector} className="flex items-center gap-2 px-3 py-1.5 bg-apple-secondary-bg dark:bg-apple-dark-elevated rounded-full">
                <span className="text-footnote font-medium text-apple-text dark:text-apple-dark-text">{sector}</span>
                <span className="text-footnote text-apple-blue font-semibold">{pct}%</span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Extracted Holdings */}
      {holdings.length > 0 && (
        <GlassCard className="p-6">
          <SectionTitle title="Extracted Holdings" subtitle="From your portfolio screenshot via OCR" />
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary">
                  <th className="text-left py-2 px-3">Stock</th>
                  <th className="text-right py-2 px-3">Qty</th>
                  <th className="text-right py-2 px-3">Buy Price</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h, i) => (
                  <tr key={i} className="border-t border-apple-separator/30 dark:border-apple-dark-separator/30">
                    <td className="py-3 px-3">
                      <p className="font-medium text-apple-text dark:text-apple-dark-text">{h.ticker}</p>
                      <p className="text-footnote text-apple-secondary-text">{h.stock_name}</p>
                    </td>
                    <td className="py-3 px-3 text-right text-apple-text dark:text-apple-dark-text">{h.quantity.toLocaleString()}</td>
                    <td className="py-3 px-3 text-right text-apple-text dark:text-apple-dark-text">{fmt(h.buy_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* Portfolio Analysis */}
      <GlassCard className="p-6">
        <SectionTitle title="Portfolio Analysis" />
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary">
                <th className="text-left py-2 px-3">Stock</th>
                <th className="text-right py-2 px-3">Buy</th>
                <th className="text-right py-2 px-3">Current</th>
                <th className="text-right py-2 px-3">Fair Value</th>
                <th className="text-right py-2 px-3">↑ Current</th>
                <th className="text-right py-2 px-3">↑ Buy</th>
                <th className="text-center py-2 px-3">Signal</th>
              </tr>
            </thead>
            <tbody>
              {analysis.map((row, i) => (
                <tr key={i} className="border-t border-apple-separator/30 dark:border-apple-dark-separator/30">
                  <td className="py-3 px-3">
                    <p className="font-semibold text-apple-text dark:text-apple-dark-text">{row.ticker}</p>
                    <p className="text-footnote text-apple-secondary-text">{row.industry}</p>
                  </td>
                  <td className="py-3 px-3 text-right text-apple-text dark:text-apple-dark-text">{fmt(row.buy_price)}</td>
                  <td className="py-3 px-3 text-right text-apple-text dark:text-apple-dark-text">{fmt(row.current_price)}</td>
                  <td className="py-3 px-3 text-right font-semibold text-apple-blue">{fmt(row.probability_weighted_value)}</td>
                  <td className={`py-3 px-3 text-right font-semibold ${row.upside_from_current >= 0 ? 'text-apple-green' : 'text-apple-red'}`}>
                    {fmtPct(row.upside_from_current)}
                  </td>
                  <td className={`py-3 px-3 text-right font-semibold ${row.upside_from_buy >= 0 ? 'text-apple-green' : 'text-apple-red'}`}>
                    {fmtPct(row.upside_from_buy)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={`pill text-xs ${row.recommendation === 'Buy' ? 'pill-green' : row.recommendation === 'Exit' ? 'pill-red' : 'pill-orange'}`}>
                      {row.recommendation || '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Upside chart */}
      <Charts
        mode="portfolio"
        portfolioData={analysis.map((r) => ({
          name: r.ticker,
          upside: r.upside_from_current,
          current: r.current_price,
          pwv: r.probability_weighted_value,
        }))}
      />
    </motion.div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [activeTab, setActiveTab] = useState('single');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [singleResult, setSingleResult] = useState(null);
  const [multipleResult, setMultipleResult] = useState(null);
  const [portfolioResult, setPortfolioResult] = useState(null);

  const handleTabSelect = useCallback((tab) => {
    setActiveTab(tab);
    setError(null);
    // Scroll to analyzer section
    document.getElementById('analyzer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  // ─ Single stock ─
  const handleSingleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setSingleResult(null);
    try {
      const { data } = await axios.post(`${API}/analyze-stock`, formData);
      setSingleResult(data.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Analysis failed. Please check the ticker and try again.');
    } finally {
      setLoading(false);
    }
  };

  // ─ Multiple stocks ─
  const handleMultipleSubmit = async ({ tickers }) => {
    setLoading(true);
    setError(null);
    setMultipleResult(null);
    try {
      const tickerList = tickers.split(',').map((t) => t.trim()).filter(Boolean);
      const { data } = await axios.post(`${API}/analyze-multiple`, {
        tickers: tickerList,
      });
      setMultipleResult(data.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Analysis failed. Please check the tickers and try again.');
    } finally {
      setLoading(false);
    }
  };

  // ─ Portfolio upload ─
  const handlePortfolioUpload = async (file) => {
    setLoading(true);
    setError(null);
    setPortfolioResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const { data } = await axios.post(`${API}/upload-portfolio`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPortfolioResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Portfolio processing failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>AI Valuation Engine — Indian Stock Analysis</title>
        <meta name="description" content="AI-powered stock valuation for Indian equities using Screener.in and Gemini" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-apple-bg dark:bg-apple-dark transition-colors duration-300">
        <Navbar />

        <main className="max-w-content mx-auto">
          <Hero onTabSelect={handleTabSelect} />

          {/* ─── Analyzer Section ─── */}
          <section id="analyzer" className="px-4 pb-20">
            <TabBar active={activeTab} onChange={(t) => { setActiveTab(t); setError(null); }} />

            <AnimatePresence mode="wait">
              {activeTab === 'single' && (
                <motion.div key="single" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="max-w-2xl mx-auto">
                    <InputForm onSubmit={handleSingleSubmit} loading={loading} />
                  </div>
                  {loading && <LoadingSkeleton type="single" />}
                  {error && <ErrorBanner message={error} />}
                  {singleResult && !loading && <div className="mt-8"><SingleStockResult data={singleResult} /></div>}
                </motion.div>
              )}

              {activeTab === 'multiple' && (
                <motion.div key="multiple" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="max-w-2xl mx-auto">
                    <MultipleStocksInput onSubmit={handleMultipleSubmit} loading={loading} />
                  </div>
                  {loading && <LoadingSkeleton type="table" />}
                  {error && <ErrorBanner message={error} />}
                  {multipleResult && !loading && <div className="mt-8"><MultipleStocksResult rows={multipleResult} /></div>}
                </motion.div>
              )}

              {activeTab === 'portfolio' && (
                <motion.div key="portfolio" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="max-w-2xl mx-auto">
                    <PortfolioUpload onUpload={handlePortfolioUpload} loading={loading} />
                  </div>
                  {loading && <LoadingSkeleton type="portfolio" />}
                  {error && <ErrorBanner message={error} />}
                  {portfolioResult && !loading && (
                    <div className="mt-8">
                      {portfolioResult.message ? (
                        <GlassCard className="p-6 text-center">
                          <p className="text-apple-secondary-text">{portfolioResult.message}</p>
                        </GlassCard>
                      ) : (
                        <PortfolioResult data={portfolioResult} />
                      )}
                    </div>
                  )}
                </motion.div>
              )}

              {activeTab === 'learning' && (
                <motion.div key="learning" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="max-w-5xl mx-auto">
                    <LearningPanel />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>
        </main>

        {/* Footer */}
        <footer className="border-t border-apple-separator/30 dark:border-apple-dark-separator/30 py-8 px-6 text-center">
          <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary">
            Multi-agent system: Data · DCF · LLM · Portfolio · Memory · Evaluation · Learning agents · Data from screener.in · Not financial advice
          </p>
        </footer>
      </div>
    </>
  );
}

// ─── Multiple Stocks Input ────────────────────────────────────────────────────
function MultipleStocksInput({ onSubmit, loading }) {
  const [tickers, setTickers] = useState('');

  return (
    <GlassCard className="p-6">
      <SectionTitle
        title="Multiple Stock Analysis"
        subtitle="Enter up to 12 NSE tickers, comma-separated"
      />
      <div className="mt-5 space-y-4">
        <div>
          <label className="text-subhead font-medium text-apple-text dark:text-apple-dark-text block mb-2">
            Tickers
          </label>
          <textarea
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            placeholder="HDFCBANK, RELIANCE, TCS, INFY, ICICIBANK"
            rows={3}
            className="apple-input resize-none"
          />
          <p className="text-caption text-apple-secondary-text mt-1.5 ml-1">
            Example: HDFCBANK, RELIANCE, TCS, INFY
          </p>
        </div>
        <button
          onClick={() => onSubmit({ tickers })}
          disabled={!tickers.trim() || loading}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Spinner /> Analyzing {tickers.split(',').filter(Boolean).length} stocks…
            </span>
          ) : (
            'Analyze All Stocks'
          )}
        </button>
      </div>
    </GlassCard>
  );
}

// ─── Error Banner ─────────────────────────────────────────────────────────────
function ErrorBanner({ message }) {
  const isNetworkError = message.startsWith('Network Error') || message.includes('ERR_') || message.includes('ECONNREFUSED');
  const displayMessage = isNetworkError
    ? 'Could not reach the analysis server. The backend may be starting up (cold start ~30s on free plan) — please wait and try again.'
    : message;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 p-4 bg-apple-red/8 border border-apple-red/20 rounded-apple-lg"
    >
      <div className="flex items-start gap-3">
        <svg className="w-5 h-5 text-apple-red flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        <p className="text-subhead text-apple-red">{displayMessage}</p>
      </div>
    </motion.div>
  );
}

// ─── Inline Spinner ───────────────────────────────────────────────────────────
function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
