/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan all Django templates and static JS for class usage
  content: [
    './templates/**/*.html',
    './accounts/templates/**/*.html',
    './lands/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        primary:        '#1a5c38',
        'primary-dark': '#134428',
        'primary-light':'#d4e8da',
        available:      '#059669',
        reserved:       '#f59e0b',
        sold:           '#dc2626',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        xl:  '0.75rem',
        '2xl': '1rem',
      },
    },
  },
  plugins: [],
}
