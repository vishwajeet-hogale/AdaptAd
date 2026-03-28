import { useEffect, useState } from 'react'
import { dataApi, decideApi, type Ad } from '../api/client'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import DecisionBadge from '../components/DecisionBadge'

const DECISION_COLORS: Record<string, string> = {
  SHOW: '#22c55e', SOFTEN: '#f59e0b', DELAY: '#f97316', SUPPRESS: '#ef4444',
}

interface BatchRow {
  user_id: number; user_name: string; age_group: string
  decision: string; combined_score: number
}

export default function BatchResults() {
  const [ads, setAds] = useState<Ad[]>([])
  const [adId, setAdId] = useState('')
  const [time, setTime] = useState('evening')
  const [season, setSeason] = useState('Fall')
  const [adsShown, setAdsShown] = useState(0)
  const [fatigue, setFatigue] = useState(0.2)
  const [rows, setRows] = useState<BatchRow[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [filter, setFilter] = useState<string>('ALL')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dataApi.getAds(80).then((r) => { setAds(r.data.ads); if (r.data.ads[0]) setAdId(r.data.ads[0].id) }).catch(() => {})
  }, [])

  async function runBatch() {
    setLoading(true); setError(null)
    try {
      const r = await decideApi.batch({ ad_id: adId, time_of_day: time, season, ads_shown_this_session: adsShown, session_fatigue: fatigue })
      setRows(r.data.results)
      setCounts(r.data.decision_counts)
    } catch { setError('Batch failed. Is the server running?') }
    finally { setLoading(false) }
  }

  const pieData = Object.entries(counts).map(([name, value]) => ({ name, value })).filter((d) => d.value > 0)
  const filtered = filter === 'ALL' ? rows : rows.filter((r) => r.decision === filter)

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-xl font-semibold text-slate-100">Batch Results</h1>
        <p className="text-sm text-slate-500 mt-1">Run decisions for all 200 users simultaneously</p>
      </div>

      <div className="card">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="label">Ad</label>
            <select className="select-input w-full mt-1" value={adId} onChange={(e) => setAdId(e.target.value)}>
              {ads.map((a) => <option key={a.id} value={a.id}>{a.id} — {a.category}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Time</label>
            <select className="select-input w-full mt-1" value={time} onChange={(e) => setTime(e.target.value)}>
              {['morning','afternoon','evening','latenight'].map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Season</label>
            <select className="select-input w-full mt-1" value={season} onChange={(e) => setSeason(e.target.value)}>
              {['Spring','Summer','Fall','Winter'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Ads shown — {adsShown}</label>
              <input type="range" min={0} max={5} value={adsShown} onChange={(e) => setAdsShown(Number(e.target.value))} className="w-full mt-2 accent-sky-500" />
            </div>
            <div>
              <label className="label">Fatigue — {fatigue.toFixed(2)}</label>
              <input type="range" min={0} max={1} step={0.05} value={fatigue} onChange={(e) => setFatigue(Number(e.target.value))} className="w-full mt-2 accent-sky-500" />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-primary" onClick={runBatch} disabled={loading || !adId}>
            {loading ? 'Running…' : 'Run Batch'}
          </button>
          {error && <span className="text-suppress text-sm">{error}</span>}
        </div>
      </div>

      {rows.length > 0 && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-sm font-medium text-slate-300 mb-3">Decision Distribution</h2>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                    {pieData.map((entry) => <Cell key={entry.name} fill={DECISION_COLORS[entry.name] ?? '#64748b'} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b' }} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h2 className="text-sm font-medium text-slate-300 mb-3">Counts</h2>
              <div className="space-y-2.5">
                {Object.entries(counts).map(([d, n]) => (
                  <div key={d} className="flex items-center gap-3">
                    <DecisionBadge decision={d} size="sm" />
                    <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                      <div className="h-full rounded-full transition-all" style={{ width: `${(n / rows.length) * 100}%`, background: DECISION_COLORS[d] }} />
                    </div>
                    <span className="font-mono text-sm w-8 text-right text-slate-400">{n}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <h2 className="text-sm font-medium text-slate-300">Per-user Results</h2>
              <select className="select-input text-sm ml-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="ALL">All decisions</option>
                {['SHOW','SOFTEN','DELAY','SUPPRESS'].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-slate-800">
                    <th className="pb-2 text-slate-500 font-medium">User</th>
                    <th className="pb-2 text-slate-500 font-medium">Age</th>
                    <th className="pb-2 text-slate-500 font-medium">Decision</th>
                    <th className="pb-2 text-slate-500 font-medium">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 50).map((r) => (
                    <tr key={r.user_id} className="border-b border-slate-800/40 hover:bg-slate-800/20 transition-colors">
                      <td className="py-2 text-slate-300">{r.user_name}</td>
                      <td className="py-2 text-slate-500">{r.age_group}</td>
                      <td className="py-2"><DecisionBadge decision={r.decision} size="sm" /></td>
                      <td className="py-2 font-mono text-slate-500">{r.combined_score.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length > 50 && <p className="text-xs text-slate-500 mt-2">Showing 50 of {filtered.length}</p>}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
