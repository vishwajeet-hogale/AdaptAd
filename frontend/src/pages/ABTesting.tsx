import { useState } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

const AD_CATEGORIES = ['tech', 'food', 'auto', 'fashion', 'finance', 'travel', 'health', 'gaming']
const AGE_GROUPS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
const GENRES = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Documentary', 'Romance', 'Thriller', 'Animation', 'Fantasy']

interface Break { break_minute: number; ad_category: string; decision: string }
interface Session { session_id: string; user_name: string; content_title: string; session_x: Break[]; session_y: Break[] }
interface Rating { annoyance: number; relevance: number; willingness: number }

function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} onClick={() => onChange(n)} className={`text-lg transition-colors ${n <= value ? 'text-yellow-400' : 'text-zinc-700 hover:text-zinc-500'}`}>★</button>
      ))}
    </div>
  )
}

function SessionView({ label, breaks, rating, onRate }: { label: string; breaks: Break[]; rating: Rating; onRate: (field: keyof Rating, v: number) => void }) {
  return (
    <div className="card flex-1 min-w-0">
      <h3 className="section-title mb-3">Session {label}</h3>
      <div className="space-y-1 mb-4 max-h-48 overflow-y-auto">
        {breaks.length === 0
          ? <p className="text-zinc-600 text-sm">No ad breaks</p>
          : breaks.map((b, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-zinc-600 w-10 font-mono text-xs">{b.break_minute}m</span>
                <DecisionBadge decision={b.decision} size="sm" />
                <span className="text-zinc-500 text-xs">{b.ad_category}</span>
              </div>
            ))
        }
      </div>
      <div className="border-t border-violet-900/30 pt-3 space-y-3">
        <div className="flex items-center justify-between">
          <span className="label">Annoyance</span>
          <StarRating value={rating.annoyance} onChange={(v) => onRate('annoyance', v)} />
        </div>
        <div className="flex items-center justify-between">
          <span className="label">Relevance</span>
          <StarRating value={rating.relevance} onChange={(v) => onRate('relevance', v)} />
        </div>
        <div className="flex items-center justify-between">
          <span className="label">Would continue?</span>
          <StarRating value={rating.willingness} onChange={(v) => onRate('willingness', v)} />
        </div>
      </div>
    </div>
  )
}

const DEFAULT_CUSTOM = {
  person_name: '',
  age_group: '25-34',
  country: '',
  interests: [] as string[],
  ad_tolerance: 0.5,
  show_title: '',
  show_genre: 'Drama',
  show_duration_minutes: 45,
  is_series: false,
}

export default function ABTesting() {
  const [session, setSession] = useState<Session | null>(null)
  const [xRating, setXRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [yRating, setYRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [custom, setCustom] = useState(DEFAULT_CUSTOM)

  function updateRating(which: 'X' | 'Y', field: keyof Rating, v: number) {
    if (which === 'X') setXRating((r) => ({ ...r, [field]: v }))
    else setYRating((r) => ({ ...r, [field]: v }))
  }

  function resetSession() {
    setSession(null); setSubmitted(false); setResults(null); setError(null)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
  }

  async function startSession() {
    resetSession(); setLoading(true)
    try {
      const r = await abApi.start()
      setSession(r.data as Session)
    } catch { setError('Failed to start A/B session.') }
    finally { setLoading(false) }
  }

  async function startCustomSession() {
    if (custom.interests.length === 0) { setError('Please select at least one interest.'); return }
    if (!custom.show_title.trim()) { setError('Please enter a show or movie title.'); return }
    resetSession(); setLoading(true)
    try {
      const r = await abApi.startCustom(custom)
      setSession(r.data as Session)
      setShowCustomForm(false)
    } catch { setError('Failed to start custom A/B session.') }
    finally { setLoading(false) }
  }

  async function submitRatings() {
    if (!session) return
    const missingX = Object.values(xRating).some((v) => v === 0)
    const missingY = Object.values(yRating).some((v) => v === 0)
    if (missingX || missingY) { setError('Please rate all fields for both sessions.'); return }
    setLoading(true); setError(null)
    try {
      await abApi.rate(session.session_id, { session_label: 'X', ...xRating })
      await abApi.rate(session.session_id, { session_label: 'Y', ...yRating })
      setSubmitted(true)
      const r = await abApi.results()
      setResults(r.data)
    } catch { setError('Failed to submit ratings.') }
    finally { setLoading(false) }
  }

  function toggleInterest(cat: string) {
    setCustom((c) => ({
      ...c,
      interests: c.interests.includes(cat)
        ? c.interests.filter((i) => i !== cat)
        : [...c.interests, cat],
    }))
  }

  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  return (
    <div className="space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="page-title">A/B Testing</h1>
          <p className="page-sub">Compare AdaptAd against random placement. Labels are randomized to prevent bias.</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button className="btn-secondary" onClick={() => { resetSession(); setShowCustomForm((v) => !v) }} disabled={loading}>
            {showCustomForm ? 'Cancel' : 'Use My Profile'}
          </button>
          <button className="btn-primary" onClick={startSession} disabled={loading}>
            {loading ? 'Loading…' : 'New Session'}
          </button>
        </div>
      </div>

      {/* Custom person & show form */}
      {showCustomForm && (
        <div className="card border-sky-700/30 space-y-5">
          <div>
            <h2 className="section-title mb-1">Real Person & Show</h2>
            <p className="text-xs text-slate-500">Enter your own profile and a show you're watching. AdaptAd will run a personalised A/B test.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="label">Your name</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. Priya Sharma"
                value={custom.person_name}
                onChange={(e) => setCustom((c) => ({ ...c, person_name: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="label">Country</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. India"
                value={custom.country}
                onChange={(e) => setCustom((c) => ({ ...c, country: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="label">Age group</label>
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={custom.age_group}
                onChange={(e) => setCustom((c) => ({ ...c, age_group: e.target.value }))}
              >
                {AGE_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Ad tolerance <span className="text-sky-500 font-mono">{custom.ad_tolerance.toFixed(2)}</span></label>
              <input
                type="range" min="0" max="1" step="0.05"
                className="w-full accent-sky-500"
                value={custom.ad_tolerance}
                onChange={(e) => setCustom((c) => ({ ...c, ad_tolerance: parseFloat(e.target.value) }))}
              />
              <div className="flex justify-between text-xs text-slate-600">
                <span>Low (dislike ads)</span><span>High (don't mind)</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="label">Your interests <span className="text-slate-600 font-normal">(select all that apply)</span></label>
            <div className="flex flex-wrap gap-2">
              {AD_CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => toggleInterest(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    custom.interests.includes(cat)
                      ? 'bg-sky-600/20 border-sky-500/50 text-sky-300'
                      : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-700/50 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1 sm:col-span-1">
              <label className="label">Show / movie title</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. Stranger Things"
                value={custom.show_title}
                onChange={(e) => setCustom((c) => ({ ...c, show_title: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="label">Genre</label>
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={custom.show_genre}
                onChange={(e) => setCustom((c) => ({ ...c, show_genre: e.target.value }))}
              >
                {GENRES.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Duration (minutes)</label>
              <input
                type="number" min="10" max="240"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={custom.show_duration_minutes}
                onChange={(e) => setCustom((c) => ({ ...c, show_duration_minutes: parseInt(e.target.value) || 45 }))}
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox" id="is-series" className="accent-sky-500"
              checked={custom.is_series}
              onChange={(e) => setCustom((c) => ({ ...c, is_series: e.target.checked }))}
            />
            <label htmlFor="is-series" className="text-sm text-slate-400">This is a series episode (fewer ad breaks)</label>
          </div>

          <button className="btn-primary" onClick={startCustomSession} disabled={loading}>
            {loading ? 'Loading…' : 'Start with My Profile'}
          </button>
        </div>
      )}

      {error && (
        <div className="card border-red-700/40 bg-red-950/20 text-red-400 text-sm">{error}</div>
      )}

      {session && !submitted && (
        <>
          <div className="card">
            <p className="text-sm text-zinc-400">
              User: <span className="text-zinc-100 font-medium">{session.user_name}</span>
              <span className="text-zinc-600 mx-2">·</span>
              Content: <span className="text-zinc-100 font-medium">{session.content_title}</span>
            </p>
            <p className="text-xs text-zinc-600 mt-1.5">Rate each session honestly. You do not know which system generated which.</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-4">
            <SessionView label="X" breaks={session.session_x as Break[]} rating={xRating} onRate={(f, v) => updateRating('X', f, v)} />
            <SessionView label="Y" breaks={session.session_y as Break[]} rating={yRating} onRate={(f, v) => updateRating('Y', f, v)} />
          </div>
          <button className="btn-primary" onClick={submitRatings} disabled={loading}>Submit Ratings</button>
        </>
      )}

      {submitted && aggregate && (
        <div className="card space-y-5">
          <div>
            <h2 className="section-title text-show mb-1">Ratings submitted — aggregate results</h2>
            <p className="text-xs text-slate-500">
              A <span className="text-slate-300 font-medium">win</span> is awarded to whichever session scored higher on{' '}
              <span className="text-sky-400">willingness to continue</span> +{' '}
              <span className="text-sky-400">relevance</span> −{' '}
              <span className="text-sky-400">annoyance</span> across all completed sessions.
              The labels X and Y were randomised so you couldn't tell which system was which while rating.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card bg-show/5 border-show/20">
              <p className="label mb-1">AdaptAd Wins</p>
              <p className="text-3xl font-bold text-show">{String(aggregate.adaptad_wins)}</p>
              <p className="text-xs text-slate-500 mt-2">Sessions where AdaptAd's human-centered policy was preferred — it showed fewer, more relevant ads at better moments.</p>
            </div>
            <div className="card bg-suppress/5 border-suppress/20">
              <p className="label mb-1">Baseline Wins</p>
              <p className="text-3xl font-bold text-suppress">{String(aggregate.baseline_wins)}</p>
              <p className="text-xs text-slate-500 mt-2">Sessions where the random policy was preferred — it simply shows or suppresses ads at random with no user context.</p>
            </div>
            <div className="card">
              <p className="label mb-1">Ties</p>
              <p className="text-3xl font-bold text-zinc-400">{String(aggregate.ties)}</p>
              <p className="text-xs text-slate-500 mt-2">Sessions where both policies scored equally. Run more sessions to break the tie.</p>
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-xl px-4 py-3 text-xs text-slate-400 leading-relaxed">
            <span className="text-slate-200 font-semibold">How to read this: </span>
            More AdaptAd wins means the GA-evolved chromosome is genuinely improving the viewing experience compared to random ad placement. Run more sessions to build statistical confidence — a single session is just one data point.
          </div>

          <button className="btn-secondary" onClick={startSession}>Run Another Session</button>
        </div>
      )}

      {!session && !loading && !showCustomForm && (
        <div className="card h-48 flex items-center justify-center text-zinc-600 text-sm">
          Click "New Session" for a random test, or "Use My Profile" to test with your own details
        </div>
      )}
    </div>
  )
}
