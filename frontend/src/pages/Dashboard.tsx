import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { dataApi } from '../api/client'
import { useStore } from '../store'

export default function Dashboard() {
  const navigate = useNavigate()
  const fitness = useStore((s) => s.chromosomeFitness)
  const genes = useStore((s) => s.chromosomeGenes)
  const totalDecisions = useStore((s) => s.totalDecisions)
  const [health, setHealth] = useState<{ users: number; ads: number; content: number } | null>(null)

  useEffect(() => {
    dataApi.health().then((r) => setHealth(r.data)).catch(() => {})
  }, [])

  const cards = [
    { label: 'Chromosome Fitness', value: fitness != null ? fitness.toFixed(4) : 'None', sub: fitness != null ? 'Evolved chromosome loaded' : 'Run evolution first', color: 'text-sky-400' },
    { label: 'Total Decisions', value: totalDecisions.toString(), sub: 'This session', color: 'text-show' },
    { label: 'Users', value: health?.users ?? '—', sub: 'Synthetic profiles', color: 'text-slate-300' },
    { label: 'Ads', value: health?.ads ?? '—', sub: '8 categories', color: 'text-slate-300' },
  ]

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Human-centered ad decision system powered by genetic algorithms</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <p className="label mb-2">{c.label}</p>
            <p className={`text-2xl font-bold font-mono ${c.color}`}>{c.value}</p>
            <p className="text-xs text-slate-500 mt-1.5">{c.sub}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" onClick={() => navigate('/evolve')}>Run Evolution</button>
          <button className="btn-secondary" onClick={() => navigate('/decide')}>Try a Decision</button>
          <button className="btn-secondary" onClick={() => navigate('/simulate')}>Simulate Session</button>
          <button className="btn-secondary" onClick={() => navigate('/batch')}>Batch Decisions</button>
          <button className="btn-secondary" onClick={() => navigate('/ab-test')}>Start A/B Test</button>
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Decision States</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {(['SHOW', 'SOFTEN', 'DELAY', 'SUPPRESS'] as const).map((d) => (
            <div key={d} className={`rounded-lg px-3 py-2 border text-xs font-medium ${
              d === 'SHOW'     ? 'bg-show/10 border-show/20 text-show' :
              d === 'SOFTEN'   ? 'bg-soften/10 border-soften/20 text-soften' :
              d === 'DELAY'    ? 'bg-delay/10 border-delay/20 text-delay' :
                                 'bg-suppress/10 border-suppress/20 text-suppress'
            }`}>
              <p className="font-semibold tracking-wide">{d}</p>
              <p className="text-xs opacity-70 mt-0.5 font-normal">
                {d === 'SHOW' ? 'Favorable conditions' :
                 d === 'SOFTEN' ? 'Show shorter version' :
                 d === 'DELAY' ? 'Wait for better moment' :
                 'Skip entirely'}
              </p>
            </div>
          ))}
        </div>
      </div>

      {genes && (
        <div className="card">
          <h2 className="text-sm font-medium text-slate-300 mb-2">Active Chromosome</h2>
          <p className="text-xs font-mono text-slate-500 break-all">[{genes.map((g) => g.toFixed(3)).join(', ')}]</p>
        </div>
      )}
    </div>
  )
}
