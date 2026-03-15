import { motion } from 'framer-motion';
import clsx from 'clsx';

/**
 * Apple-style card component with optional hover elevation.
 * Props:
 *   children, className, hover (bool), as (element tag), onClick
 */
export default function GlassCard({
  children,
  className = '',
  hover = false,
  as: Tag = 'div',
  onClick,
}) {
  const base = clsx(
    'bg-white dark:bg-apple-dark-card',
    'border border-apple-separator/30 dark:border-apple-dark-separator/40',
    'rounded-apple-lg shadow-apple',
    hover && 'transition-all duration-200 hover:shadow-apple-hover hover:-translate-y-0.5 cursor-pointer',
    className
  );

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={base}
      onClick={onClick}
    >
      {children}
    </motion.div>
  );
}
