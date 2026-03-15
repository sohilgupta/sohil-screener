import GlassCard from './GlassCard';

/**
 * Large metric display — Apple Stocks style.
 * Props: label, value, secondary, color (tailwind class), highlight (bool)
 */
export default function MetricDisplay({ label, value, secondary, color, highlight = false }) {
  return (
    <GlassCard
      className={`p-6 flex flex-col gap-1 ${highlight ? 'border-apple-blue/30 dark:border-apple-blue/30' : ''}`}
    >
      <p className="text-footnote font-medium text-apple-secondary-text dark:text-apple-dark-secondary uppercase tracking-wider">
        {label}
      </p>
      <p
        className={`text-[28px] font-bold leading-none tracking-tight mt-1 ${
          color || (highlight ? 'text-apple-blue' : 'text-apple-text dark:text-apple-dark-text')
        }`}
      >
        {value ?? '—'}
      </p>
      {secondary && (
        <p className="text-subhead text-apple-secondary-text dark:text-apple-dark-secondary mt-1">
          {secondary}
        </p>
      )}
    </GlassCard>
  );
}
