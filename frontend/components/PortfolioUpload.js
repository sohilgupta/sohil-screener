import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import GlassCard from './GlassCard';
import SectionTitle from './SectionTitle';

function Spinner() {
  return (
    <svg className="animate-spin w-5 h-5 text-apple-blue" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export default function PortfolioUpload({ onUpload, loading = false }) {
  const onDrop = useCallback(
    (accepted) => {
      if (accepted.length > 0) {
        onUpload(accepted[0]);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.bmp'] },
    maxFiles: 1,
    disabled: loading,
  });

  const hasFile = acceptedFiles.length > 0;
  const fileName = hasFile ? acceptedFiles[0].name : null;

  return (
    <GlassCard className="p-6">
      <SectionTitle
        title="Portfolio Screenshot Upload"
        subtitle="Upload a screenshot from Zerodha, Groww, Angel, or Upstox"
      />

      <div className="mt-5">
        <div
          {...getRootProps()}
          className={`
            relative rounded-apple-lg border-2 border-dashed transition-all duration-200 cursor-pointer
            ${isDragActive
              ? 'border-apple-blue bg-apple-blue/5 scale-[1.01]'
              : hasFile
              ? 'border-apple-green/40 bg-apple-green/5'
              : 'border-apple-separator/60 dark:border-apple-dark-separator/60 hover:border-apple-blue/50 hover:bg-apple-secondary-bg/60'
            }
            ${loading ? 'pointer-events-none opacity-60' : ''}
          `}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            {loading ? (
              <>
                <Spinner />
                <p className="text-callout font-medium text-apple-blue">Processing portfolio…</p>
                <p className="text-footnote text-apple-secondary-text">
                  Running OCR and AI analysis
                </p>
              </>
            ) : hasFile ? (
              <>
                <div className="w-12 h-12 rounded-apple-lg bg-apple-green/10 flex items-center justify-center">
                  <svg className="w-6 h-6 text-apple-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-callout font-semibold text-apple-text dark:text-apple-dark-text">{fileName}</p>
                  <p className="text-footnote text-apple-secondary-text mt-1">
                    Click to change file
                  </p>
                </div>
              </>
            ) : isDragActive ? (
              <>
                <div className="w-12 h-12 rounded-apple-lg bg-apple-blue/10 flex items-center justify-center">
                  <svg className="w-6 h-6 text-apple-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-callout font-semibold text-apple-blue">Drop it here</p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-apple-lg bg-apple-secondary-bg dark:bg-apple-dark-elevated flex items-center justify-center">
                  <svg className="w-6 h-6 text-apple-secondary-text" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-callout font-semibold text-apple-text dark:text-apple-dark-text">
                    Drop portfolio screenshot
                  </p>
                  <p className="text-footnote text-apple-secondary-text mt-1">
                    PNG, JPG, WebP · or{' '}
                    <span className="text-apple-blue">browse files</span>
                  </p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Supported brokers */}
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {['Zerodha', 'Groww', 'Angel', 'Upstox', 'ICICI Direct', '5Paisa'].map((broker) => (
            <span
              key={broker}
              className="px-2.5 py-1 rounded-full bg-apple-secondary-bg dark:bg-apple-dark-elevated text-caption text-apple-secondary-text font-medium"
            >
              {broker}
            </span>
          ))}
        </div>

        {/* Tip */}
        <div className="mt-4 p-3 bg-apple-blue/5 dark:bg-apple-blue/10 rounded-apple border border-apple-blue/15">
          <p className="text-caption text-apple-blue leading-relaxed">
            <strong>Tip:</strong> Ensure your screenshot clearly shows stock names, quantities, and average buy prices for best OCR accuracy.
          </p>
        </div>
      </div>
    </GlassCard>
  );
}
