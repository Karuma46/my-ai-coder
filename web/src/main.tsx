import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import './index.css'
import App from './App.tsx'
import { AlertsProvider } from './utilities/alerts'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AlertsProvider>
        <App />
      </AlertsProvider>
    </BrowserRouter>
  </StrictMode>,
)
