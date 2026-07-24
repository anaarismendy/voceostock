import LoginPin from './screens/LoginPin'
import PantallaConteo from './screens/PantallaConteo'
import SeleccionBodega from './screens/SeleccionBodega'
import { useOperario } from './state/OperarioContext'

export default function App() {
  const { operario, bodega } = useOperario()

  if (!operario) return <LoginPin />
  if (!bodega) return <SeleccionBodega />
  return <PantallaConteo />
}
