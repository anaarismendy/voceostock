import js from '@eslint/js'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  // vite.config.ts.timestamp-*: residuo temporal de vite que rompía el lint (I1/H10).
  { ignores: ['dist', 'dev-dist', 'vite.config.ts.timestamp-*'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
)
