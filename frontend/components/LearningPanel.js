/**
 * LearningPanel — displays model accuracy, learned parameters,
 * prediction history, and manual trigger controls.
 */
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import GlassCard from './GlassCard';
import SectionTitle from './SectionTitle';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const fmtPct = (n) => {
  if (n == null) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${Number(n).toFixed(2)}%`;
};
const fmt2 = (n) => (n == null ? '—' : Number(n).toFixed(2));

// ── Stat tile ─────────────────────────────────────────────────────────────────
function StatTile({ label, value, sub, color }) {
  return (
    <div className="rounded-apple bg-apple-secondary-bg dark:bg-apple-dark-elevated px-4 py-3">
      <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mb-1">{label}</p>
      <p className={`text-title3 font-semibold ${color || 'text-apple-text dark:text-apple-dark-text'}`}>{value}</p>
      {sub && <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Accuracy section ──────────────────────────────────────────────────────────
function AccuracySection({ report }) {
  if (!report) return null;
  const { overall, by_sector, recent_runs } = report;

  const total = overall?.evaluated ?? 0;
  const within10 = overall?.within_10pct ?? 0;
  const within20 = overall?.within_20pct ?? 0;
  const pct10 = total > 0 ? ((within10 / total) * 100).toFixed(1) : '—';
  const pct20 = total > 0 ? ((within20 / total) * 100).toFixed(1) : '—';

  return (
    <div className="space-y-6">
      {/* Overall stats */}
      <div>
        <h3 className="text-subhead font-semibold text-apple-text dark:text-apple-dark-text mb-3">
          Overall Accuracy
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatTile label="Predictions Evaluated" value={total || '0'} />
          <StatTile
            label="Avg Signed Error"
            value={fmtPct(overall?.avg_signed_error)}
            sub="positive = over-estimated"
            color={overall?.avg_signed_error > 0 ? 'text-apple-red' : 'text-apple-green'}
          />
          <StatTile label="Avg Abs Error" value={overall?.avg_abs_error != null ? `${Number(overall.avg_abs_error).toFixed(1)}%` : '—'} />
          <StatTile label="Median Abs Error" value={overall?.median_abs_error != null ? `${Number(overall.median_abs_error).toFixed(1)}%` : '—'} />
          <StatTile label="Within 10%" value={pct10 !== '—' ? `${pct10}%` : '—'} sub={`${within10} of ${total}`} color="text-apple-green" />
          <StatTile label="Within 20%" value={pct20 !== '—' ? `${pct20}%` : '—'} sub={`${within20} of ${total}`} color="text-apple-blue" />
        </div>
      </div>

      {/* By sector */}
      {by_sector && by_sector.length > 0 && (
        <div>
          <h3 className="text-subhead font-semibold text-apple-text dark:text-apple-dark-text mb-3">
            Accuracy by Sector
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-subhead">
              <thead>
                <tr className="text-left border-b border-apple-separator/30 dark:border-apple-dark-separator/30">
                  <th className="pb-2 font-medium text-apple-secondary-text dark:text-apple-dark-secondary">Sector</th>
                  <th className="pb-2 font-medium text-apple-secondary-text dark:text-apple-dark-secondary text-right">Samples</th>
                  <th className="pb-2 font-medium text-apple-secondary-text dark:text-apple-dark-secondary text-right">Avg Signed</th>
                  <th className="pb-2 font-medium text-apple-secondary-text dark:text-apple-dark-secondary text-right">Avg Abs</th>
                </tr>
              </thead>
              <tbody>
                {by_sector.map((row, i) => (
                  <tr key={i} className="border-b border-apple-separator/20 dark:border-apple-dark-separator/20">
                    <td className="py-2 text-apple-text dark:text-apple-dark-text">{row.sector}</td>
                    <td className="py-2 text-right text-apple-secondary-text dark:text-apple-dark-secondary">{row.count}</td>
                    <td className={`py-2 text-right font-mono ${row.avg_signed > 0 ? 'text-apple-red' : 'text-apple-green'}`}>
                      {fmtPct(row.avg_signed)}
                    </td>
                    <td className="py-2 text-right font-mono text-apple-text dark:text-apple-dark-text">
                      {row.avg_abs != null ? `${Number(row.avg_abs).toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent runs */}
      {recent_runs && recent_runs.length > 0 && (
        <div>
          <h3 className="text-subhead font-semibold text-apple-text dark:text-apple-dark-text mb-3">
            Recent Evaluation Runs
          </h3>
          <div className="space-y-2">
            {recent_runs.map((run, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 rounded-apple bg-apple-secondary-bg dark:bg-apple-dark-elevated text-subhead">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-apple-text dark:text-apple-dark-text capitalize">{run.run_type}</span>
                  <span className="text-apple-secondary-text dark:text-apple-dark-secondary">
                    {run.run_at ? new Date(run.run_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                  </span>
                </div>
                <div className="flex items-center gap-4 font-mono">
                  <span className="text-apple-secondary-text dark:text-apple-dark-secondary">{run.predictions_evaluated} evaluated</span>
                  {run.avg_abs_error != null && (
                    <span className="text-apple-text dark:text-apple-dark-text">{Number(run.avg_abs_error).toFixed(1)}% abs err</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Parameters section ────────────────────────────────────────────────────────
function ParametersSection({ params }) {
  if (!params || params.length === 0) return (
    <p className="text-apple-secondary-text dark:text-apple-dark-secondary text-subhead">
      No learned parameters yet. Parameters are generated by the Learning Agent after evaluating predictions.
    </p>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-subhead">
        <thead>
          <tr className="text-left border-b border-apple-separator/30 dark:border-apple-dark-separator/30">
            {['Sector', 'Condition', 'Bias Corr', 'Growth Adj', 'Conf Scale', 'Samples', 'Avg Abs Err', 'Updated'].map((h) => (
              <th key={h} className="pb-2 pr-4 font-medium text-apple-secondary-text dark:text-apple-dark-secondary whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {params.map((p, i) => (
            <tr key={i} className="border-b border-apple-separator/20 dark:border-apple-dark-separator/20 hover:bg-apple-secondary-bg/50 dark:hover:bg-apple-dark-elevated/50 transition-colors">
              <td className="py-2 pr-4 text-apple-text dark:text-apple-dark-text font-medium">{p.sector}</td>
              <td className="py-2 pr-4">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  p.market_condition === 'Bullish' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                  p.market_condition === 'Bearish' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                  'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                }`}>{p.market_condition}</span>
              </td>
              <td className={`py-2 pr-4 font-mono ${p.bias_correction > 0.1 ? 'text-apple-green' : p.bias_correction < -0.1 ? 'text-apple-red' : 'text-apple-secondary-text dark:text-apple-dark-secondary'}`}>
                {fmtPct(p.bias_correction)}
              </td>
              <td className="py-2 pr-4 font-mono text-apple-text dark:text-apple-dark-text">{fmtPct(p.base_growth_adj)}</td>
              <td className="py-2 pr-4 font-mono text-apple-text dark:text-apple-dark-text">{fmt2(p.confidence_scaling)}</td>
              <td className="py-2 pr-4 text-apple-secondary-text dark:text-apple-dark-secondary">{p.sample_size}</td>
              <td className="py-2 pr-4 font-mono text-apple-text dark:text-apple-dark-text">
                {p.avg_abs_error != null ? `${Number(p.avg_abs_error).toFixed(1)}%` : '—'}
              </td>
              <td className="py-2 text-apple-secondary-text dark:text-apple-dark-secondary whitespace-nowrap">
                {p.last_updated ? new Date(p.last_updated).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Prediction history section ────────────────────────────────────────────────
function PredictionHistory() {
  const [ticker, setTicker] = useState('');
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = async () => {
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.get(`${API}/predictions/${ticker.trim().toUpperCase()}`);
      setHistory(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase().replace(/\s/g, ''))}
          onKeyDown={(e) => e.key === 'Enter' && fetch()}
          placeholder="HDFCBANK"
          className="flex-1 input-field font-mono text-sm"
          maxLength={20}
        />
        <button onClick={fetch} disabled={loading || !ticker.trim()} className="btn-primary px-4 py-2 text-sm">
          {loading ? 'Loading…' : 'Fetch'}
        </button>
      </div>

      {error && <p className="text-apple-red text-subhead mb-3">{error}</p>}

      {history && history.predictions && (
        <div>
          <p className="text-subhead text-apple-secondary-text dark:text-apple-dark-secondary mb-3">
            {history.count} prediction{history.count !== 1 ? 's' : ''} for <span className="font-mono font-medium text-apple-blue">{history.ticker}</span>
          </p>
          {history.predictions.length === 0 ? (
            <p className="text-apple-secondary-text dark:text-apple-dark-secondary text-subhead">No predictions stored yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-subhead">
                <thead>
                  <tr className="text-left border-b border-apple-separator/30 dark:border-apple-dark-separator/30">
                    {['Date', 'Price at Pred', 'Predicted Value', 'Recommendation', 'Confidence', 'Actual Price', 'Error %', 'Sector'].map((h) => (
                      <th key={h} className="pb-2 pr-3 font-medium text-apple-secondary-text dark:text-apple-dark-secondary whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.predictions.map((p, i) => (
                    <tr key={i} className="border-b border-apple-separator/20 dark:border-apple-dark-separator/20">
                      <td className="py-2 pr-3 whitespace-nowrap text-apple-secondary-text dark:text-apple-dark-secondary">
                        {p.created_at ? new Date(p.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : '—'}
                      </td>
                      <td className="py-2 pr-3 font-mono text-apple-text dark:text-apple-dark-text">
                        {p.price_at_prediction != null ? `₹${Number(p.price_at_prediction).toFixed(2)}` : '—'}
                      </td>
                      <td className="py-2 pr-3 font-mono text-apple-text dark:text-apple-dark-text">
                        {p.predicted_value != null ? `₹${Number(p.predicted_value).toFixed(2)}` : '—'}
                      </td>
                      <td className={`py-2 pr-3 font-medium ${
                        p.recommendation === 'Buy' ? 'text-apple-green' :
                        p.recommendation === 'Exit' ? 'text-apple-red' :
                        'text-apple-orange'
                      }`}>{p.recommendation || '—'}</td>
                      <td className="py-2 pr-3 text-apple-secondary-text dark:text-apple-dark-secondary">{p.confidence || '—'}</td>
                      <td className="py-2 pr-3 font-mono text-apple-text dark:text-apple-dark-text">
                        {p.actual_price_30d != null ? `₹${Number(p.actual_price_30d).toFixed(2)}` : <span className="text-apple-secondary-text dark:text-apple-dark-secondary">Pending</span>}
                      </td>
                      <td className={`py-2 pr-3 font-mono ${
                        p.error_pct_30d == null ? '' :
                        Math.abs(p.error_pct_30d) <= 10 ? 'text-apple-green' :
                        Math.abs(p.error_pct_30d) <= 20 ? 'text-apple-orange' : 'text-apple-red'
                      }`}>
                        {fmtPct(p.error_pct_30d)}
                      </td>
                      <td className="py-2 text-apple-secondary-text dark:text-apple-dark-secondary">{p.sector || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Manual trigger panel ──────────────────────────────────────────────────────
function TriggerPanel() {
  const [status, setStatus] = useState({});
  const [running, setRunning] = useState({});

  const trigger = async (endpoint, key) => {
    setRunning((r) => ({ ...r, [key]: true }));
    setStatus((s) => ({ ...s, [key]: null }));
    try {
      const { data } = await axios.post(`${API}/${endpoint}`);
      setStatus((s) => ({ ...s, [key]: { ok: true, msg: JSON.stringify(data, null, 2) } }));
    } catch (e) {
      setStatus((s) => ({ ...s, [key]: { ok: false, msg: e.response?.data?.detail || e.message } }));
    } finally {
      setRunning((r) => ({ ...r, [key]: false }));
    }
  };

  const buttons = [
    { key: 'track', label: 'Track Prices', endpoint: 'learning/track', desc: 'Fetches latest prices for all tracked tickers' },
    { key: 'evaluate', label: 'Evaluate Predictions', endpoint: 'learning/evaluate', desc: 'Scores 30-day-old predictions against actual prices' },
    { key: 'learn', label: 'Run Learning Agent', endpoint: 'learning/run', desc: 'Updates DCF parameters from evaluated predictions' },
  ];

  return (
    <div className="space-y-4">
      {buttons.map(({ key, label, endpoint, desc }) => (
        <div key={key} className="flex flex-col sm:flex-row sm:items-start gap-3 p-4 rounded-apple bg-apple-secondary-bg dark:bg-apple-dark-elevated">
          <div className="flex-1">
            <p className="text-subhead font-medium text-apple-text dark:text-apple-dark-text">{label}</p>
            <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mt-0.5">{desc}</p>
            {status[key] && (
              <pre className={`mt-2 text-xs p-2 rounded bg-white/50 dark:bg-apple-dark/50 overflow-x-auto max-h-32 ${status[key].ok ? 'text-apple-green' : 'text-apple-red'}`}>
                {status[key].msg}
              </pre>
            )}
          </div>
          <button
            onClick={() => trigger(endpoint, key)}
            disabled={running[key]}
            className="btn-secondary text-sm px-4 py-2 whitespace-nowrap flex-shrink-0"
          >
            {running[key] ? 'Running…' : 'Trigger'}
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function LearningPanel() {
  const [section, setSection] = useState('accuracy');
  const [accuracy, setAccuracy] = useState(null);
  const [params, setParams] = useState(null);
  const [loadingAcc, setLoadingAcc] = useState(false);
  const [loadingParams, setLoadingParams] = useState(false);
  const [dbDisabled, setDbDisabled] = useState(false);

  const fetchAccuracy = useCallback(async () => {
    setLoadingAcc(true);
    try {
      const { data } = await axios.get(`${API}/learning/accuracy`);
      if (data.db === 'disabled') setDbDisabled(true);
      setAccuracy(data);
    } catch {
      // silently fail
    } finally {
      setLoadingAcc(false);
    }
  }, []);

  const fetchParams = useCallback(async () => {
    setLoadingParams(true);
    try {
      const { data } = await axios.get(`${API}/learning/parameters`);
      if (data.db === 'disabled') setDbDisabled(true);
      setParams(data.parameters);
    } catch {
      // silently fail
    } finally {
      setLoadingParams(false);
    }
  }, []);

  useEffect(() => {
    fetchAccuracy();
    fetchParams();
  }, [fetchAccuracy, fetchParams]);

  const SECTIONS = [
    { id: 'accuracy', label: 'Accuracy' },
    { id: 'parameters', label: 'Learned Parameters' },
    { id: 'history', label: 'Prediction History' },
    { id: 'triggers', label: 'Manual Triggers' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {dbDisabled && (
        <div className="flex items-start gap-2 p-3 rounded-apple bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40">
          <svg className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <p className="text-subhead text-amber-700 dark:text-amber-300">
            Database not connected — set <code className="font-mono text-xs bg-amber-100 dark:bg-amber-900/40 px-1 rounded">DATABASE_URL</code> in the Render dashboard to enable the learning loop.
          </p>
        </div>
      )}

      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-5">
          <SectionTitle
            title="Learning Performance"
            subtitle="Self-improving model accuracy and learned parameters"
          />
          <button
            onClick={() => { fetchAccuracy(); fetchParams(); }}
            className="btn-secondary text-sm px-3 py-1.5"
          >
            Refresh
          </button>
        </div>

        {/* Sub-nav */}
        <div className="flex flex-wrap gap-1 mb-6 p-1 bg-apple-secondary-bg dark:bg-apple-dark-elevated rounded-apple w-fit">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSection(s.id)}
              className={`px-4 py-1.5 rounded-[8px] text-subhead font-medium transition-all duration-150
                ${section === s.id
                  ? 'bg-white dark:bg-apple-dark-card text-apple-text dark:text-apple-dark-text shadow-apple'
                  : 'text-apple-secondary-text dark:text-apple-dark-secondary hover:text-apple-text dark:hover:text-apple-dark-text'
                }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {section === 'accuracy' && (
          loadingAcc
            ? <p className="text-apple-secondary-text dark:text-apple-dark-secondary text-subhead">Loading accuracy data…</p>
            : <AccuracySection report={accuracy} />
        )}
        {section === 'parameters' && (
          loadingParams
            ? <p className="text-apple-secondary-text dark:text-apple-dark-secondary text-subhead">Loading parameters…</p>
            : <ParametersSection params={params} />
        )}
        {section === 'history' && <PredictionHistory />}
        {section === 'triggers' && <TriggerPanel />}
      </GlassCard>
    </motion.div>
  );
}
