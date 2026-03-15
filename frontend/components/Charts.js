import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  Legend,
} from 'recharts';
import GlassCard from './GlassCard';
import SectionTitle from './SectionTitle';

// ─── Custom Tooltip ───────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-apple-dark-card rounded-apple border border-apple-separator/30 dark:border-apple-dark-separator/30 shadow-apple-lg p-3 text-sm">
      <p className="font-semibold text-apple-text dark:text-apple-dark-text mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.fill || p.color }} className="font-medium">
          {p.name}: {typeof p.value === 'number'
            ? p.value > 1000
              ? `₹${p.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
              : `${p.value.toFixed(1)}%`
            : p.value}
        </p>
      ))}
    </div>
  );
}

// ─── Single Stock Scenario Chart ─────────────────────────────────────────────
function ScenarioBarChart({ currentPrice, bullTarget, baseTarget, bearTarget, pwv }) {
  const data = [
    { name: 'Current Price', value: currentPrice, fill: '#6E6E73' },
    { name: 'Bear Case', value: bearTarget, fill: '#FF3B30' },
    { name: 'Base Case', value: baseTarget, fill: '#0071E3' },
    { name: 'Bull Case', value: bullTarget, fill: '#34C759' },
    { name: 'Fair Value (PWV)', value: pwv, fill: '#FF9500' },
  ].filter((d) => d.value != null);

  if (data.length < 2) return null;

  return (
    <GlassCard className="p-6">
      <SectionTitle title="Scenario Price Targets" subtitle="Current price vs. scenario targets" />
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#6E6E73' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6E6E73' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,113,227,0.04)' }} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={56}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

// ─── Portfolio Upside Chart ───────────────────────────────────────────────────
function PortfolioUpsideChart({ portfolioData }) {
  if (!portfolioData?.length) return null;

  const data = portfolioData
    .filter((d) => d.upside != null)
    .sort((a, b) => b.upside - a.upside)
    .slice(0, 12);

  return (
    <GlassCard className="p-6">
      <SectionTitle title="Upside Potential" subtitle="Probability-weighted upside from current price" />
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: '#6E6E73' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v.toFixed(0)}%`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12, fill: '#6E6E73', fontWeight: 500 }}
              axisLine={false}
              tickLine={false}
              width={64}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,113,227,0.04)' }} />
            <ReferenceLine x={0} stroke="#6E6E73" strokeWidth={1} strokeDasharray="4 4" />
            <Bar dataKey="upside" name="Upside %" radius={[0, 6, 6, 0]} maxBarSize={24}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.upside >= 0 ? '#34C759' : '#FF3B30'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

// ─── Current vs Fair Value Comparison ────────────────────────────────────────
function FairValueComparison({ portfolioData }) {
  if (!portfolioData?.length) return null;

  const data = portfolioData
    .filter((d) => d.current != null && d.pwv != null)
    .slice(0, 8);

  if (data.length < 2) return null;

  return (
    <GlassCard className="p-6">
      <SectionTitle title="Current vs Fair Value" subtitle="CMP compared to probability-weighted target" />
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#6E6E73' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6E6E73' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,113,227,0.04)' }} />
            <Legend
              formatter={(v) => <span className="text-footnote text-apple-secondary-text">{v}</span>}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="current" name="Current Price" fill="#6E6E73" radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="pwv" name="Fair Value" fill="#0071E3" radius={[4, 4, 0, 0]} maxBarSize={32} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

// ─── Main Charts Wrapper ──────────────────────────────────────────────────────
/**
 * mode: 'single' | 'portfolio'
 * Single mode props: currentPrice, bullTarget, baseTarget, bearTarget, pwv
 * Portfolio mode props: portfolioData = [{ name, upside, current, pwv }]
 */
export default function Charts({ mode, ...props }) {
  if (mode === 'single') {
    return (
      <div className="space-y-4">
        <ScenarioBarChart
          currentPrice={props.currentPrice}
          bullTarget={props.bullTarget}
          baseTarget={props.baseTarget}
          bearTarget={props.bearTarget}
          pwv={props.pwv}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PortfolioUpsideChart portfolioData={props.portfolioData} />
      <FairValueComparison portfolioData={props.portfolioData} />
    </div>
  );
}
