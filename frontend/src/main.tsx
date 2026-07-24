import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { OperarioProvider } from './state/OperarioContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <OperarioProvider>
      <App />
    </OperarioProvider>
  </React.StrictMode>,
)
