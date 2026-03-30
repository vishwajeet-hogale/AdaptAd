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
  `px-3.5 py-2 rounded-lg text-sm font-semibold tracking-wide transition-all duration-200 touch-manipulation ${
    isActive
      ? 'bg-violet-600/20 text-violet-600 dark:text-violet-300 ring-1 ring-violet-500/40 shadow-sm shadow-violet-900/30'
      : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-slate-100 dark:hover:bg-white/5 active:bg-slate-200 dark:active:bg-white/10'
  }`

export default function NavBar() {
  const fitness = useStore((s) => s.chromosomeFitness)
  const [open, setOpen] = useState(false)

  return (
    <nav className="bg-white/80 dark:bg-[#090914]/80 backdrop-blur-md border-b border-slate-200 dark:border-violet-900/30 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center h-14 gap-2">
          {/* Brand */}
          <span className="font-bold text-sm tracking-widest uppercase shrink-0 mr-4 bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
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
            <div className="hidden md:flex items-center gap-2 ml-auto shrink-0 bg-violet-900/20 border border-violet-700/30 rounded-full px-3.5 py-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shadow-sm shadow-cyan-400/50" />
              <span className="text-xs text-cyan-300 font-mono font-medium">
                {fitness.toFixed(4)}
              </span>
            </div>
          )}

          {/* Hamburger — mobile */}
          <button
            className="md:hidden ml-auto p-2.5 rounded-lg text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-slate-100 dark:hover:bg-white/5 active:bg-slate-200 dark:active:bg-white/10 transition-colors touch-manipulation min-h-[44px] min-w-[44px] flex items-center justify-center"
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
        <div className="md:hidden border-t border-slate-200 dark:border-violet-900/30 bg-white/95 dark:bg-[#090914]/95 px-4 py-3 space-y-0.5">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `block px-3.5 py-3 rounded-lg text-sm font-semibold tracking-wide transition-all duration-200 touch-manipulation min-h-[44px] ${
                  isActive
                    ? 'bg-violet-600/20 text-violet-600 dark:text-violet-300 ring-1 ring-violet-500/30'
                    : 'text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-slate-100 dark:hover:bg-white/5 active:bg-slate-200 dark:active:bg-white/10'
                }`
              }
              onClick={() => setOpen(false)}
            >
              {l.label}
            </NavLink>
          ))}
          {fitness != null && (
            <p className="px-3 pt-2.5 text-xs text-zinc-500 font-mono border-t border-violet-900/30 mt-2">
              Fitness: <span className="text-cyan-400">{fitness.toFixed(4)}</span>
            </p>
          )}
        </div>
      )}
    </nav>
  )
}
