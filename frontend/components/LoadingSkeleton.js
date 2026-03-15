/**
 * Skeleton loaders for different result types.
 * Props: type ('single' | 'table' | 'portfolio')
 */
function SkeletonBlock({ className = '' }) {
  return <div className={`skeleton ${className}`} />;
}

function SingleSkeleton() {
  return (
    <div className="mt-8 space-y-4 animate-fade-in">
      {/* Overview card */}
      <div className="bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-6">
        <div className="flex justify-between">
          <div className="space-y-2">
            <SkeletonBlock className="h-3 w-24 rounded" />
            <SkeletonBlock className="h-7 w-56 rounded" />
          </div>
          <div className="space-y-2 items-end flex flex-col">
            <SkeletonBlock className="h-3 w-20 rounded" />
            <SkeletonBlock className="h-8 w-32 rounded" />
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-6 space-y-2">
            <SkeletonBlock className="h-3 w-20 rounded" />
            <SkeletonBlock className="h-8 w-28 rounded" />
            <SkeletonBlock className="h-3 w-16 rounded" />
          </div>
        ))}
      </div>

      {/* Scenario cards */}
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-5 space-y-3">
            <div className="flex justify-between">
              <SkeletonBlock className="h-4 w-20 rounded" />
              <SkeletonBlock className="h-6 w-6 rounded-full" />
            </div>
            <SkeletonBlock className="h-8 w-28 rounded" />
            <div className="flex gap-4">
              <SkeletonBlock className="h-4 w-16 rounded" />
              <SkeletonBlock className="h-4 w-16 rounded" />
            </div>
          </div>
        ))}
      </div>

      {/* Chart placeholder */}
      <div className="bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-6">
        <SkeletonBlock className="h-5 w-32 rounded mb-4" />
        <SkeletonBlock className="h-48 w-full rounded-apple" />
      </div>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="mt-8 bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-6 animate-fade-in">
      <SkeletonBlock className="h-5 w-40 rounded mb-6" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex gap-4">
            <SkeletonBlock className="h-5 w-24 rounded" />
            <SkeletonBlock className="h-5 w-20 rounded" />
            <SkeletonBlock className="h-5 w-20 rounded" />
            <SkeletonBlock className="h-5 w-20 rounded" />
            <SkeletonBlock className="h-5 w-20 rounded" />
            <SkeletonBlock className="h-5 w-16 rounded" />
            <SkeletonBlock className="h-5 w-16 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

function PortfolioSkeleton() {
  return (
    <div className="mt-8 space-y-4 animate-fade-in">
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white dark:bg-apple-dark-card rounded-apple-lg border border-apple-separator/30 p-6 space-y-2">
            <SkeletonBlock className="h-3 w-24 rounded" />
            <SkeletonBlock className="h-8 w-32 rounded" />
          </div>
        ))}
      </div>
      <TableSkeleton />
    </div>
  );
}

export default function LoadingSkeleton({ type = 'single' }) {
  if (type === 'table') return <TableSkeleton />;
  if (type === 'portfolio') return <PortfolioSkeleton />;
  return <SingleSkeleton />;
}
