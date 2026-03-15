/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#0071E3',
          'blue-hover': '#0077ED',
          text: '#1D1D1F',
          'secondary-text': '#6E6E73',
          bg: '#FFFFFF',
          'secondary-bg': '#F5F5F7',
          green: '#34C759',
          red: '#FF3B30',
          orange: '#FF9500',
          separator: '#D2D2D7',
          dark: '#000000',
          'dark-card': '#1C1C1E',
          'dark-elevated': '#2C2C2E',
          'dark-text': '#F5F5F7',
          'dark-secondary': '#8E8E93',
          'dark-separator': '#38383A',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
      fontSize: {
        'hero': ['56px', { lineHeight: '1.07', fontWeight: '700', letterSpacing: '-0.005em' }],
        'display': ['40px', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.003em' }],
        'headline': ['28px', { lineHeight: '1.14', fontWeight: '600', letterSpacing: '-0.002em' }],
        'title': ['22px', { lineHeight: '1.2', fontWeight: '600' }],
        'body': ['17px', { lineHeight: '1.47' }],
        'callout': ['16px', { lineHeight: '1.5' }],
        'subhead': ['15px', { lineHeight: '1.47' }],
        'footnote': ['13px', { lineHeight: '1.38' }],
        'caption': ['11px', { lineHeight: '1.36' }],
      },
      borderRadius: {
        'apple': '12px',
        'apple-lg': '18px',
        'apple-xl': '24px',
      },
      boxShadow: {
        'apple': '0 4px 16px rgba(0,0,0,0.06)',
        'apple-md': '0 8px 24px rgba(0,0,0,0.08)',
        'apple-lg': '0 16px 48px rgba(0,0,0,0.10)',
        'apple-hover': '0 12px 32px rgba(0,0,0,0.12)',
        'apple-dark': '0 8px 32px rgba(0,0,0,0.4)',
      },
      maxWidth: {
        'content': '1080px',
      },
      animation: {
        'shimmer': 'shimmer 1.5s infinite',
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
