/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        btc: '#F7931A',
        base: '#0d1117',
        surface: '#161b22',
        border: '#30363d',
      },
    },
  },
  plugins: [],
};
