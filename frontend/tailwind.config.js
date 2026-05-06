/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'p0': 'rgb(239, 68, 68)',    // red-500
        'p1': 'rgb(251, 146, 60)',   // orange-400
        'p2': 'rgb(250, 204, 21)',   // yellow-400
        'p3': 'rgb(59, 130, 246)',   // blue-500
      },
    },
  },
  plugins: [],
}
