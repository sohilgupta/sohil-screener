/**
 * Apple-style section header.
 * Props: title (required), subtitle (optional), size ('sm' | 'md' | 'lg')
 */
export default function SectionTitle({ title, subtitle, size = 'md' }) {
  const titleClass = {
    sm: 'text-[15px] font-semibold',
    md: 'text-title font-semibold',
    lg: 'text-headline font-bold',
  }[size];

  return (
    <div>
      <h3 className={`${titleClass} text-apple-text dark:text-apple-dark-text`}>{title}</h3>
      {subtitle && (
        <p className="text-footnote text-apple-secondary-text dark:text-apple-dark-secondary mt-0.5">
          {subtitle}
        </p>
      )}
    </div>
  );
}
