import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useStore } from '../store'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/evolve', label: 'Evolution' },
  { to: '/decide', label: 'Decisions' },
  { to: '/simulate', label: 'Simulator' },
  { to: '/batch', label: 'Batch' },
  { to: '/ab-test', label: 'A/B Test' },
  { to: '/settings', label: 'Settings' },
]

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? 'bg-slate-800 text-sky-400 ring-1 ring-sky-500/25'
      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
  }`

export default function NavBar() {
  const fitness = useStore((s) => s.chromosomeFitness)
  const [open, setOpen] = useState(false)

  return (
    <nav className="bg-slate-950 border-b border-slate-800/80 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center h-14 gap-2">
          {/* Brand */}
          <span className="font-semibold text-sky-400 mr-4 text-sm tracking-widest uppercase shrink-0">
            AdaptAd
          </span>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-0.5 flex-1 overflow-x-auto">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.to === '/'} className={linkClass}>
                {l.label}
              </NavLink>
            ))}
          </div>

          {/* Fitness pill — desktop */}
          {fitness != null && (
            <div className="hidden md:flex items-center gap-1.5 ml-auto shrink-0 bg-slate-900 border border-slate-800 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="text-xs text-slate-400 font-mono">
                {fitness.toFixed(4)}
              </span>
            </div>
          )}

          {/* Hamburger — mobile */}
          <button
            className="md:hidden ml-auto p-2 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            onClick={() => setOpen((o) => !o)}
            aria-label="Toggle navigation"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              {open
                ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950 px-4 py-3 space-y-0.5">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-800 text-sky-400'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`
              }
              onClick={() => setOpen(false)}
            >
              {l.label}
            </NavLink>
          ))}
          {fitness != null && (
            <p className="px-3 pt-2 text-xs text-slate-500 font-mono border-t border-slate-800 mt-2">
              Fitness: <span className="text-sky-400">{fitness.toFixed(4)}</span>
            </p>
          )}
        </div>
      )}
    </nav>
  )
}
