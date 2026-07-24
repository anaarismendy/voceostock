import LoginPin from './screens/LoginPin'
import PantallaConteo from './screens/PantallaConteo'
import PanelLider from './screens/PanelLider'
import SeleccionBodega from './screens/SeleccionBodega'
import { useOperario } from './state/OperarioContext'

export default function App() {
  const { operario, bodega } = useOperario()

  if (!operario) return <LoginPin />
  if (!bodega) return <SeleccionBodega />
  // El líder va a su panel (dashboard en vivo + cierre); el operario, a capturar.
  if (operario.rol === 'lider') return <PanelLider />
  return <PantallaConteo />
}
