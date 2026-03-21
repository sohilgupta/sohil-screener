/**
 * DCFPanel — displays DCF Agent output inline in the single-stock result.
 * Shows WACC, FCF scenario projections, intrinsic values, and margin of safety.
 */
import { motion } from 'framer-motion';
import GlassCard from './GlassCard';
import SectionTitle from './SectionTitle';

const fmt = (n, prefix = '₹') =>
  n != null ? `${prefix}${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—';

const fmtPct = (n) => {
  if (n == null) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${Number(n).toFixed(1)}%`;
};

function ScenarioBadge({ label, color, intrinsic, growthPct, terminalPct, probability }) {
  return (
    <div className={`flex-1 rounded-apple p-4 border ${color}`}>
      <p className="text-footnote font-semibold uppercase tracking-widest mb-2 opacity-70">{label}</p>
      <p className="text-title3 font-bold mb-1">{fmt(intrinsic)}</p>
      <div className="text-footnote opacity-70 space-y-0.5">
        <p>FCF CAGR: {growthPct != null ? `${growthPct}%` : '—'}</p>
        <p>Terminal g: {terminalPct != null ? `${terminalPct}%` : '—'}</p>
        <p>Probability: {probability != null ? `${(probability * 100).toFixed(0)}%` : '—'}</p>
      </div>
    </div>
  );
}

function MosBadge({ mosPct }) {
  if (mosPct == null) return null;
  const positive = mosPct >= 0;
  const bg = positive ? 'bg-apple-green/10 border-apple-green/30 text-apple-green' : 'bg-apple-red/10 border-apple-red/30 text-apple-red';
  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border text-subhead font-semibold ${bg}`}>
      <span>{positive ? '↑' : '↓'}</span>
      <span>Margin of Safety: {fmtPct(mosPct)}</span>
    </div>
  );
}

export default function DCFPanel({ dcf }) {
  if (!dcf || !dcf.available) {
    return (
      <GlassCard className="p-6">
        <SectionTitle title="DCF Valuation" subtitle="Discounted Cash Flow analysis" />
        <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mt-3">
          {dcf?.reason || 'Insufficient financial data for DCF analysis.'}
        </p>
      </GlassCard>
    );
  }

  const { scenarios = {}, wacc_pct, base_fcf_cr, probability_weighted_intrinsic, margin_of_safety_pct, dcf_recommendation } = dcf;
  const bull = scenarios.bull || {};
  const base = scenarios.base || {};
  const bear = scenarios.bear || {};

  const recColor =
    dcf_recommendation === 'Buy' ? 'text-apple-green' :
    dcf_recommendation === 'Exit' ? 'text-apple-red' : 'text-apple-orange';

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <GlassCard className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
          <SectionTitle
            title="DCF Valuation"
            subtitle={`WACC ${wacc_pct != null ? wacc_pct + '%' : '—'} · Base FCF ₹${base_fcf_cr != null ? Number(base_fcf_cr).toLocaleString('en-IN') : '—'} Cr`}
          />
          <div className="flex flex-col items-start sm:items-end gap-2">
            <MosBadge mosPct={margin_of_safety_pct} />
            {dcf_recommendation && (
              <p className={`text-subhead font-semibold ${recColor}`}>
                DCF Signal: {dcf_recommendation}
              </p>
            )}
          </div>
        </div>

        {/* PWV */}
        <div className="mb-5 p-4 bg-apple-blue/5 dark:bg-apple-blue/10 border border-apple-blue/20 rounded-apple">
          <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mb-1">
            Probability-Weighted DCF Intrinsic Value
          </p>
          <p className="text-3xl font-bold text-apple-blue">
            {fmt(probability_weighted_intrinsic)}
          </p>
        </div>

        {/* Scenario columns */}
        <div className="flex flex-col sm:flex-row gap-3">
          <ScenarioBadge
            label="Bull"
            color="border-apple-green/30 text-apple-green bg-apple-green/5 dark:bg-apple-green/10"
            intrinsic={bull.intrinsic_per_share}
            growthPct={bull.fcf_growth_pct}
            terminalPct={bull.terminal_growth_pct}
            probability={bull.probability}
          />
          <ScenarioBadge
            label="Base"
            color="border-apple-blue/30 text-apple-blue bg-apple-blue/5 dark:bg-apple-blue/10"
            intrinsic={base.intrinsic_per_share}
            growthPct={base.fcf_growth_pct}
            terminalPct={base.terminal_growth_pct}
            probability={base.probability}
          />
          <ScenarioBadge
            label="Bear"
            color="border-apple-red/30 text-apple-red bg-apple-red/5 dark:bg-apple-red/10"
            intrinsic={bear.intrinsic_per_share}
            growthPct={bear.fcf_growth_pct}
            terminalPct={bear.terminal_growth_pct}
            probability={bear.probability}
          />
        </div>

        {/* FCF projection table for base case */}
        {base.fcf_projections && base.fcf_projections.length > 0 && (
          <div className="mt-5">
            <p className="text-footnote font-semibold text-apple-secondary-text dark:text-apple-dark-secondary uppercase tracking-wider mb-2">
              Base-Case FCF Projections (₹ Cr)
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-footnote">
                <thead>
                  <tr className="text-apple-secondary-text dark:text-apple-dark-secondary border-b border-apple-separator/30">
                    <th className="text-left py-1.5 pr-4">Year</th>
                    <th className="text-right py-1.5 pr-4">FCF (Cr)</th>
                    <th className="text-right py-1.5">PV (Cr)</th>
                  </tr>
                </thead>
                <tbody>
                  {base.fcf_projections.map((row) => (
                    <tr key={row.year} className="border-b border-apple-separator/10 text-apple-text dark:text-apple-dark-text">
                      <td className="py-1.5 pr-4">Year {row.year}</td>
                      <td className="text-right py-1.5 pr-4">
                        {Number(row.fcf_cr).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="text-right py-1.5">
                        {Number(row.pv_cr).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </GlassCard>
    </motion.div>
  );
}
