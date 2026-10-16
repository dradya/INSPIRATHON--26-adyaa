import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { AuthProvider } from './context/AuthContext.jsx'
import { FSProvider } from './context/FSContext.jsx'
import { ToastProvider } from './components/Toast.jsx'
import Navbar from './components/Navbar.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import AgentWidget from './components/AgentWidget.jsx'
import Landing from './pages/Landing.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Explorer from './pages/Explorer.jsx'
import Cleanup from './pages/Cleanup.jsx'
import Insights from './pages/Insights.jsx'
import Privacy from './pages/Privacy.jsx'
import Agent from './pages/Agent.jsx'
import Profile from './pages/Profile.jsx'
import Settings, { initAccent } from './pages/Settings.jsx'
import NotFound from './pages/NotFound.jsx'
import { ArjunOpeningAnimation } from './ArjunTheme.jsx'

function Footer() {
  return (
    <footer className="border-t border-[#d4af37]/20 py-8 text-center text-xs text-white/40">
      Built for INSPIRATHON &apos;26 · <span className="font-semibold text-[#f3e5ab]">ARJUN</span> · The Astral Shield &amp; Precision Engine · On-device first, private by design
    </footer>
  )
}

// Auth parked for now (backend not ready): all pages open, no login gate.
// To restore: wrap app routes in RequireAuth + re-add /login + /reset-password.
function RequireAuth({ children }) {
  return children
}

function Shell() {
  const location = useLocation()
  useEffect(() => { initAccent() }, [])
  return (
    <div className="flex min-h-full flex-col bg-[#090a0f] text-[#f4f1ea]">
      <ArjunOpeningAnimation />
      <Navbar />
      <main className="flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            <Routes location={location}>
              <Route path="/" element={<Landing />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/explorer" element={<Explorer />} />
              <Route path="/cleanup" element={<Cleanup />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/agent" element={<Agent />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <Footer />
      <CommandPalette />
      <AgentWidget />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <FSProvider>
          <BrowserRouter>
            <Shell />
          </BrowserRouter>
        </FSProvider>
      </ToastProvider>
    </AuthProvider>
  )
}
