/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html', // 扫描根目录下的 templates 文件夹和所有子目录中的 HTML 文件
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
    require('@tailwindcss/line-clamp'),
    require('@tailwindcss/container-queries'),
    require('daisyui'),
  ],
}

