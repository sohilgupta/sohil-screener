import '../styles/globals.css';
import { useState, useEffect } from 'react';

export default function App({ Component, pageProps }) {
  // Sync dark mode from localStorage / OS preference
  useEffect(() => {
    const stored = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (stored === 'dark' || (!stored && prefersDark)) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  return <Component {...pageProps} />;
}
