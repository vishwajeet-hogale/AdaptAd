import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Evolution from './pages/Evolution'
import DecisionExplorer from './pages/DecisionExplorer'
import SessionSimulator from './pages/SessionSimulator'
import BatchResults from './pages/BatchResults'
import ABTesting from './pages/ABTesting'
import Settings from './pages/Settings'
import { useStore } from './store'

export default function App() {
  const darkMode = useStore((s) => s.settings.darkMode)

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="evolve" element={<Evolution />} />
          <Route path="decide" element={<DecisionExplorer />} />
          <Route path="simulate" element={<SessionSimulator />} />
          <Route path="batch" element={<BatchResults />} />
          <Route path="ab-test" element={<ABTesting />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
