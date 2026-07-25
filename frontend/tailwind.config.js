/** @type {import('tailwindcss').Config} */
// Los VALORES viven en src/index.css (:root). Aquí solo se mapean a clases.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        fondo: 'var(--fondo)',
        superficie1: 'var(--superficie-1)',
        superficie2: 'var(--superficie-2)',
        'borde-sutil': 'var(--borde-sutil)',
        'borde-fuerte': 'var(--borde-fuerte)',
        primario: 'var(--primario)',
        'primario-hover': 'var(--primario-hover)',
        acento: 'var(--acento-texto)',
        tinte: 'var(--tinte-primario)',
        texto: 'var(--texto)',
        'texto-sec': 'var(--texto-sec)',
        'texto-tenue': 'var(--texto-tenue)',
        exito: 'var(--exito)',
        alerta: 'var(--alerta)',
        critico: 'var(--critico)',
        'tinte-alerta': 'var(--tinte-alerta)',
        'tinte-exito': 'var(--tinte-exito)',
      },
      // Escala tipográfica del sistema: 12/14/16/20/32/56. Dos pesos: 400/600.
      fontSize: {
        xs: ['12px', '16px'],
        sm: ['14px', '20px'],
        base: ['16px', '24px'],
        lg: ['20px', '28px'],
        xl: ['32px', '40px'],
        '2xl': ['56px', '60px'],
      },
      borderRadius: {
        control: '8px',
        tarjeta: '16px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
