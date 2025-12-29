import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './styles/globals.css'
import { CardDatabaseProvider } from './context/CardDatabaseContext.tsx'
import { GameStateProvider } from './context/GameStateWebSocket.tsx'
import { CardScaleProvider } from './context/CardScaleContext.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CardScaleProvider>
      <CardDatabaseProvider>
        <GameStateProvider>
          <App />
        </GameStateProvider>
      </CardDatabaseProvider>
    </CardScaleProvider>
  </React.StrictMode>,
)
