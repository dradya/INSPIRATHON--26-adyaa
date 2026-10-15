/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif']
      },
      colors: {
        ink: '#0a0a1b',
        panel: '#12122b',
        neon: '#7c6cff',
        mint: '#3ddc97',
        peach: '#ffb86b'
      },
      boxShadow: {
        glow: '0 0 40px -8px rgba(124,108,255,.55)',
        card: '0 20px 60px -20px rgba(0,0,0,.6)'
      }
    }
  },
  plugins: []
}
