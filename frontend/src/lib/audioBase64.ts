export function extraerBase64DeDataUrl(dataUrl: string): string {
  const idx = dataUrl.indexOf(',')
  return idx === -1 ? dataUrl : dataUrl.slice(idx + 1)
}

export function blobABase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(extraerBase64DeDataUrl(String(reader.result)))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}
