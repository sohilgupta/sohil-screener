import { motion } from 'framer-motion';
import GlassCard from './GlassCard';

/**
 * Generic upload card with icon, title, description, and slot for content.
 * Props: icon (JSX), title, description, children, className
 */
export default function UploadCard({ icon, title, description, children, className = '' }) {
  return (
    <GlassCard className={`p-6 ${className}`}>
      <div className="flex items-start gap-4 mb-4">
        {icon && (
          <div className="w-10 h-10 rounded-apple bg-apple-secondary-bg dark:bg-apple-dark-elevated flex items-center justify-center flex-shrink-0">
            {icon}
          </div>
        )}
        <div>
          <h3 className="text-[15px] font-semibold text-apple-text dark:text-apple-dark-text">{title}</h3>
          {description && (
            <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mt-0.5 leading-snug">
              {description}
            </p>
          )}
        </div>
      </div>
      {children}
    </GlassCard>
  );
}
