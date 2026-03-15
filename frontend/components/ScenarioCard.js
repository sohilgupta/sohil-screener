import { motion } from 'framer-motion';

const CONFIG = {
  bull: {
    label: 'Bull Case',
    emoji: '🐂',
    bg: 'bg-apple-green/6 dark:bg-apple-green/10',
    border: 'border-apple-green/20 dark:border-apple-green/20',
    titleColor: 'text-apple-green',
    dotColor: 'bg-apple-green',
  },
  base: {
    label: 'Base Case',
    emoji: '📊',
    bg: 'bg-apple-blue/6 dark:bg-apple-blue/10',
    border: 'border-apple-blue/20 dark:border-apple-blue/20',
    titleColor: 'text-apple-blue',
    dotColor: 'bg-apple-blue',
  },
  bear: {
    label: 'Bear Case',
    emoji: '🐻',
    bg: 'bg-apple-red/6 dark:bg-apple-red/10',
    border: 'border-apple-red/20 dark:border-apple-red/20',
    titleColor: 'text-apple-red',
    dotColor: 'bg-apple-red',
  },
};

const fmt = (n) =>
  n != null ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—';

const fmtPct = (n) => (n != null ? `${Number(n).toFixed(1)}%` : '—');

export default function ScenarioCard({
  type = 'base',
  targetPrice,
  probability,
  growthRate,
  assumptions = [],
  currentPrice,
}) {
  const c = CONFIG[type] || CONFIG.base;
  const upside =
    targetPrice && currentPrice && currentPrice > 0
      ? ((targetPrice - currentPrice) / currentPrice) * 100
      : null;

  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: '0 12px 32px rgba(0,0,0,0.08)' }}
      transition={{ duration: 0.15 }}
      className={`rounded-apple-lg border p-5 ${c.bg} ${c.border} flex flex-col gap-3`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className={`text-subhead font-semibold ${c.titleColor}`}>{c.label}</span>
        <span className="text-xl">{c.emoji}</span>
      </div>

      {/* Target Price */}
      <div>
        <p className="text-caption text-apple-secondary-text dark:text-apple-dark-secondary">Target Price</p>
        <p className={`text-2xl font-bold tracking-tight ${c.titleColor}`}>{fmt(targetPrice)}</p>
        {upside != null && (
          <p className="text-caption text-apple-secondary-text mt-0.5">
            {upside >= 0 ? '+' : ''}{upside.toFixed(1)}% from current
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-4">
        <div>
          <p className="text-caption text-apple-secondary-text dark:text-apple-dark-secondary">Probability</p>
          <p className="text-callout font-semibold text-apple-text dark:text-apple-dark-text">
            {probability != null ? `${(probability * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
        <div>
          <p className="text-caption text-apple-secondary-text dark:text-apple-dark-secondary">Growth Rate</p>
          <p className="text-callout font-semibold text-apple-text dark:text-apple-dark-text">
            {growthRate != null ? `${growthRate}%` : '—'}
          </p>
        </div>
      </div>

      {/* Key Assumptions */}
      {assumptions?.length > 0 && (
        <div className="space-y-1.5 pt-1 border-t border-black/5 dark:border-white/5">
          {assumptions.slice(0, 3).map((a, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${c.dotColor}`} />
              <p className="text-caption text-apple-secondary-text dark:text-apple-dark-secondary leading-snug">{a}</p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
