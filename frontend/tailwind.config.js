/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#f3ecdf',
        panel: 'rgba(255, 250, 241, 0.84)',
        'panel-strong': '#fff9ef',
        line: 'rgba(85, 54, 32, 0.18)',
        text: '#2f1f15',
        muted: '#7f6758',
        accent: '#9e4f2b',
        'accent-soft': '#e8b487',
        success: '#2f7d57',
        danger: '#b0493a',
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', '"Songti SC"', 'STSong', 'serif'],
        sans: ['"IBM Plex Sans"', '"PingFang SC"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        'custom': '0 18px 50px rgba(60, 35, 18, 0.10)',
      }
    },
  },
  plugins: [],
}
