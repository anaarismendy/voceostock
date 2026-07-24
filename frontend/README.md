# VoceoStock — frontend (PWA)

## Arranque

```bash
npm install
npm run dev          # modo MOCK (por defecto): la API la sirve el propio vite
```

## Mock vs backend real (I2)

El dev server tiene dos modos, controlados por `VITE_API`:

| Modo | Comando | Qué pasa |
|------|---------|----------|
| Mock (default) | `npm run dev` | El plugin `mock-server/` responde `/api/v1/*` con el contrato y los ejemplos de `docs/contrato/ejemplos/`. Sin backend, sin BD. |
| Real | `VITE_API=real npm run dev` | Vite hace proxy de `/api`, `/health` y `/ws` (WebSocket de progreso) al backend. |

El backend destino del proxy se cambia con `VITE_API_PROXY` (default
`http://localhost:8010`, el contenedor de docker-compose):

```bash
# backend local en el puerto 8020:
VITE_API=real VITE_API_PROXY=http://localhost:8020 npm run dev
```

En Windows (PowerShell):

```powershell
$env:VITE_API='real'; $env:VITE_API_PROXY='http://localhost:8020'; npm run dev
```

Como el navegador siempre habla con el origen de vite (proxy), no hay CORS
en dev. El backend igual restringe orígenes vía `ALLOWED_ORIGINS` (nunca
`*`) para despliegues donde el frontend se sirva desde otro origen.

## Pruebas y lint

```bash
npm test         # vitest
npm run lint     # eslint
```
