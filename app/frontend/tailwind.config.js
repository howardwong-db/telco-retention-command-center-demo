/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#050f1d',
          900: '#0a1a2f',
          850: '#0d2138',
          800: '#102a45',
          700: '#163557',
          600: '#1d4370',
        },
        spectrum: {
          blue: '#0099d8',
          sky: '#34c3f0',
          light: '#7fd8f5',
        },
        accent: {
          teal: '#22c1b3',
          amber: '#f5a623',
          red: '#ef4b5c',
          green: '#2dce89',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.25)',
        glow: '0 0 0 1px rgba(52,195,240,0.2), 0 4px 20px rgba(0,153,216,0.15)',
      },
    },
  },
  plugins: [],
}
