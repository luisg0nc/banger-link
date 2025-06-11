/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{html,js,svelte,ts}",
    "./node_modules/flowbite-svelte/**/*.{html,js,svelte,ts}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#8b5cf6',
          dark: '#7c3aed',
        },
        accent: '#ec4899',
        background: '#111827',
        surface: '#1f2937',
        text: '#f9fafb',
        textSecondary: '#9ca3af',
      },
      fontFamily: {
        sans: ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
