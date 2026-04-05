/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      keyframes: {
        progress: {
          '0%':   { width: '0%',   marginLeft: '0%' },
          '50%':  { width: '60%',  marginLeft: '20%' },
          '100%': { width: '0%',   marginLeft: '100%' },
        },
      },
      animation: {
        progress: 'progress 1.8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

