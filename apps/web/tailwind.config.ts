import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef4ff', 100: '#dbe6ff', 200: '#bccdff',
          500: '#3b6cff', 600: '#2952e6', 900: '#1a2b66',
        },
      },
    },
  },
}
export default config
