import { useEffect, useState } from 'react'
import { dataApi, decideApi, type User, type Ad, type DecisionResult } from '../api/client'
import { useStore } from '../store'
import DecisionBadge from '../components/DecisionBadge'
import AgentPanel from '../components/AgentPanel'

const TIMES = ['morning', 'afternoon', 'evening', 'latenight']
const SEASONS = ['Spring', 'Summer', 'Fall', 'Winter']

export default function DecisionExplorer() {
  const { settings, incrementDecisions } = useStore()
  const [users, setUsers] = useState<User[]>([])
  const [ads, setAds] = useState<Ad[]>([])
  const [userId, setUserId] = useState<number>(1)
  const [adId, setAdId] = useState<string>('')
  const [time, setTime] = useState('evening')
  const [season, setSeason] = useState('Fall')
  const [adsShown, setAdsShown] = useState(0)
  const [fatigue, setFatigue] = useState(0.2)
  const [result, setResult] = useState<DecisionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dataApi.getUsers(200).then((r) => { setUsers(r.data.users); if (r.data.users[0]) setUserId(r.data.users[0].id) }).catch(() => {})
    dataApi.getAds(80).then((r) => { setAds(r.data.ads); if (r.data.ads[0]) setAdId(r.data.ads[0].id) }).catch(() => {})
  }, [])

  async function runDecision() {
    setLoading(true); setError(null)
    try {
      const r = await decideApi.decide({ user_id: userId, ad_id: adId, time_of_day: time, season, ads_shown_this_session: adsShown, session_fatigue: fatigue, use_llm: settings.llmEnabled })
      setResult(r.data)
      incrementDecisions()
    } catch { setError('Decision failed. Is the server running?') }
    finally { setLoading(false) }
  }

  const user = users.find((u) => u.id === userId)
  const ad = ads.find((a) => a.id === adId)

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h1 className="page-title">Decision Explorer</h1>
        <p className="page-sub">Run a single ad decision and inspect both agent scores</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card space-y-4">
          <h2 className="section-title">Context</h2>
          <div>
            <label className="label">User</label>
            <select className="select-input w-full mt-1" value={userId} onChange={(e) => setUserId(Number(e.target.value))}>
              {users.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.age_group})</option>)}
            </select>
            {user && <p className="text-xs text-zinc-500 mt-1.5">Interests: {user.interests.join(', ')} · Fatigue: {user.fatigue_level.toFixed(2)}</p>}
          </div>
          <div>
            <label className="label">Ad</label>
            <select className="select-input w-full mt-1" value={adId} onChange={(e) => setAdId(e.target.value)}>
              {ads.map((a) => <option key={a.id} value={a.id}>{a.id} — {a.category} ({a.advertiser})</option>)}
            </select>
            {ad && <p className="text-xs text-zinc-500 mt-1.5">{ad.duration_seconds}s · {ad.creative_type} · priority {ad.priority.toFixed(2)}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Time of Day</label>
              <select className="select-input w-full mt-1" value={time} onChange={(e) => setTime(e.target.value)}>
                {TIMES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Season</label>
              <select className="select-input w-full mt-1" value={season} onChange={(e) => setSeason(e.target.value)}>
                {SEASONS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Ads Shown — {adsShown}</label>
              <input type="range" min={0} max={5} value={adsShown} onChange={(e) => setAdsShown(Number(e.target.value))} className="w-full mt-2 accent-violet-500" />
            </div>
            <div>
              <label className="label">Session Fatigue — {fatigue.toFixed(2)}</label>
              <input type="range" min={0} max={1} step={0.05} value={fatigue} onChange={(e) => setFatigue(Number(e.target.value))} className="w-full mt-2 accent-violet-500" />
            </div>
          </div>
          <button className="btn-primary w-full" onClick={runDecision} disabled={loading || !adId}>
            {loading ? 'Running…' : 'Run Decision'}
          </button>
          {error && <p className="text-suppress text-sm">{error}</p>}
        </div>

        <div className="space-y-4">
          {result ? (
            <>
              <div className="card flex items-center justify-between">
                <div>
                  <p className="label mb-2">Decision</p>
                  <DecisionBadge decision={result.decision} size="lg" />
                </div>
                <div className="text-right">
                  <p className="label mb-2">Combined Score</p>
                  <p className="font-mono text-2xl font-bold text-zinc-100">{result.combined_score.toFixed(3)}</p>
                </div>
              </div>
              <AgentPanel score={result.user_advocate} side="user" />
              <AgentPanel score={result.advertiser_advocate} side="advertiser" />
              <div className="card">
                <p className="label mb-2">Negotiation Summary</p>
                <p className="text-sm text-zinc-400 leading-relaxed">{result.reasoning}</p>
              </div>
            </>
          ) : (
            <div className="card h-48 flex items-center justify-center text-zinc-600 text-sm">
              Run a decision to see results
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
