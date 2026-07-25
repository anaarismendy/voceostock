// F3: cliente de los endpoints de configuración (E2). El líder edita umbrales y
// revisa sinónimos aprendidos sin tocar código. No maneja SD (conteo ciego).

export interface Umbrales {
  auto: number
  rapida: number
  aclaracion: number
}

export interface Sinonimo {
  id: number
  sede_id: number | null
  articulo_id: number
  texto_sinonimo: string
  origen: string
}

export async function getUmbrales(): Promise<Umbrales> {
  const r = await fetch('/api/v1/config/umbrales')
  if (!r.ok) throw new Error(`Error ${r.status} al cargar umbrales`)
  return r.json()
}

export async function putUmbrales(u: Umbrales): Promise<Umbrales> {
  const r = await fetch('/api/v1/config/umbrales', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(u),
  })
  if (!r.ok) throw new Error(`Error ${r.status} al guardar umbrales`)
  return r.json()
}

export async function getSinonimos(): Promise<Sinonimo[]> {
  const r = await fetch('/api/v1/config/sinonimos')
  if (!r.ok) throw new Error(`Error ${r.status} al listar sinónimos`)
  return r.json()
}

/** Mismo orden que D1: 0 <= aclaracion <= rapida <= auto <= 1. */
export function umbralesValidos(u: Umbrales): boolean {
  const enRango = [u.auto, u.rapida, u.aclaracion].every((x) => x >= 0 && x <= 1)
  return enRango && u.aclaracion <= u.rapida && u.rapida <= u.auto
}
