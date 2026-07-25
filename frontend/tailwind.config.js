/** @type {import('tailwindcss').Config} */
// Los VALORES viven en src/index.css (:root). Aquí solo se mapean a clases.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        fondo: 'var(--fondo)',
        pantalla: 'var(--pantalla)',
        superficie1: 'var(--superficie-1)',
        superficie2: 'var(--superficie-2)',
        lateral: 'var(--lateral)',
        borde: 'var(--borde)',
        grafito: 'var(--grafito)',
        accion: 'var(--accion)',
        'accion-claro': 'var(--accion-claro)',
        'azul-texto': 'var(--azul-texto)',
        'azul-suave': 'var(--azul-suave)',
        'tinte-azul': 'var(--tinte-azul)',
        marca: 'var(--marca)',
        'marca-hover': 'var(--marca-hover)',
        'sobre-marca': 'var(--sobre-marca)',
        'sobre-marca-suave': 'var(--sobre-marca-suave)',
        texto: 'var(--texto)',
        'texto-sec': 'var(--texto-sec)',
        'texto-tenue': 'var(--texto-tenue)',
        exito: 'var(--exito)',
        'exito-claro': 'var(--exito-claro)',
        critico: 'var(--critico)',
        'critico-claro': 'var(--critico-claro)',
        'tinte-critico': 'var(--tinte-critico)',
      },
      // Escala del design doc: 12/14/16/20/32/56, pesos 400/600.
      fontSize: {
        xs: ['12px', '16px'],
        sm: ['14px', '20px'],
        base: ['16px', '24px'],
        lg: ['20px', '28px'],
        xl: ['32px', '40px'],
        '2xl': ['56px', '60px'],
      },
      // Radios clay: 20-24 controles, 28-32 tarjetas/pantallas.
      borderRadius: {
        control: '24px',
        chip: '20px',
        tarjeta: '32px',
        pantalla: '28px',
      },
      fontFamily: {
        sans: ['Open Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
