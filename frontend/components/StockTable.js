import { useState } from 'react';
import { motion } from 'framer-motion';
import GlassCard from './GlassCard';

const fmt = (n) =>
  n != null ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—';

const fmtPct = (n) => {
  if (n == null) return '—';
  return `${n >= 0 ? '+' : ''}${Number(n).toFixed(1)}%`;
};

const recPill = (rec) => {
  const map = {
    Buy: 'pill-green',
    Hold: 'pill-orange',
    Exit: 'pill-red',
  };
  return map[rec] || 'pill-blue';
};

const COLUMNS = [
  { key: 'ticker', label: 'Stock', sortable: true },
  { key: 'current_price', label: 'CMP', sortable: true, align: 'right' },
  { key: 'bull_target', label: 'Bull', sortable: false, align: 'right' },
  { key: 'base_target', label: 'Base', sortable: false, align: 'right' },
  { key: 'bear_target', label: 'Bear', sortable: false, align: 'right' },
  { key: 'probability_weighted_value', label: 'Fair Value', sortable: true, align: 'right' },
  { key: 'upside_percentage', label: 'Upside', sortable: true, align: 'right' },
  { key: 'recommendation', label: 'Signal', sortable: false, align: 'center' },
];

export default function StockTable({ rows = [] }) {
  const [sortKey, setSortKey] = useState('upside_percentage');
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
    return sortAsc ? cmp : -cmp;
  });

  return (
    <GlassCard className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-apple-secondary-bg/60 dark:bg-apple-dark-elevated/60">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && handleSort(col.key)}
                  className={`py-3 px-4 text-footnote font-semibold text-apple-secondary-text dark:text-apple-dark-secondary select-none
                    text-${col.align || 'left'}
                    ${col.sortable ? 'cursor-pointer hover:text-apple-text dark:hover:text-apple-dark-text' : ''}
                  `}
                >
                  {col.label}
                  {col.sortable && sortKey === col.key && (
                    <span className="ml-1">{sortAsc ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <motion.tr
                key={row.ticker || i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="border-t border-apple-separator/20 dark:border-apple-dark-separator/20 hover:bg-apple-secondary-bg/40 dark:hover:bg-apple-dark-elevated/40 transition-colors"
              >
                {/* Stock name */}
                <td className="py-3.5 px-4">
                  <div>
                    <p className="font-semibold text-apple-text dark:text-apple-dark-text">{row.ticker}</p>
                    {row.company_name && row.company_name !== row.ticker && (
                      <p className="text-caption text-apple-secondary-text truncate max-w-[140px]">
                        {row.company_name}
                      </p>
                    )}
                    {row.error && <p className="text-caption text-apple-red">Error</p>}
                  </div>
                </td>

                {/* CMP */}
                <td className="py-3.5 px-4 text-right text-apple-text dark:text-apple-dark-text">
                  {fmt(row.current_price)}
                </td>

                {/* Bull */}
                <td className="py-3.5 px-4 text-right text-apple-green font-medium">
                  {fmt(row.bull_target)}
                </td>

                {/* Base */}
                <td className="py-3.5 px-4 text-right text-apple-blue font-medium">
                  {fmt(row.base_target)}
                </td>

                {/* Bear */}
                <td className="py-3.5 px-4 text-right text-apple-red font-medium">
                  {fmt(row.bear_target)}
                </td>

                {/* Fair Value */}
                <td className="py-3.5 px-4 text-right font-semibold text-apple-text dark:text-apple-dark-text">
                  {fmt(row.probability_weighted_value)}
                </td>

                {/* Upside */}
                <td
                  className={`py-3.5 px-4 text-right font-semibold ${
                    row.upside_percentage >= 0 ? 'text-apple-green' : 'text-apple-red'
                  }`}
                >
                  {fmtPct(row.upside_percentage)}
                </td>

                {/* Signal */}
                <td className="py-3.5 px-4 text-center">
                  {row.recommendation ? (
                    <span className={`pill text-xs ${recPill(row.recommendation)}`}>
                      {row.recommendation}
                    </span>
                  ) : (
                    <span className="text-apple-secondary-text">—</span>
                  )}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}
