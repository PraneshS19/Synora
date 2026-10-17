import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles.css'
import './prototype.css'
import './fidelity.css'
import './reveal.css'
import './hero-paths.css'
import './workflow.css'
import './workspace.css'
import './workflow-visuals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
