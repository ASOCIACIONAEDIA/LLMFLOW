/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Modern color palette with light, sophisticated tones
        primary: {
          DEFAULT: '#6366F1', // Indigo
          light: '#818CF8',
          dark: '#4F46E5',
        },
        secondary: {
          DEFAULT: '#10B981', // Emerald
          light: '#34D399',
          dark: '#059669',
        },
        accent: {
          DEFAULT: '#F43F5E', // Rose
          light: '#FB7185',
          dark: '#E11D48',
        },
        background: {
          DEFAULT: '#F8FAFC', // Very light slate
          light: '#F1F5F9',
          lighter: '#E2E8F0',
        },
        surface: {
          DEFAULT: '#FFFFFF', // White surface
          light: '#F8FAFC',
          dark: '#F1F5F9',
        },
        'text-primary': '#1E293B', // Dark slate for text
        'text-secondary': '#64748B', // Medium slate for secondary text
        border: '#E2E8F0', // Light border
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 0 20px -5px rgba(99, 102, 241, 0.2)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}