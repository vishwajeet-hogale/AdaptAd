import { useState } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

const AD_CATEGORIES = ['tech', 'food', 'auto', 'fashion', 'finance', 'travel', 'health', 'gaming']
const AGE_GROUPS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
const GENRES = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Documentary', 'Romance', 'Thriller', 'Animation', 'Fantasy']

interface Break { break_minute: number; ad_category: string; decision: string }
interface UserProfile {
  name: string; age_group: string; profession: string
  interests: string[]; content_preferences: string[]
  binge_tendency: number; fatigue_level: number
  ad_tolerance: number; preferred_watch_time: string
}
interface ContentProfile {
  title: string; genre: string; duration_minutes: number | null
  mood: string | null; language: string; is_series: boolean
}
interface SessionContext {
  ads_shown: number; total_breaks: number; fatigue: number
  session_depth: number; content_duration: number | null; binge: boolean
}
interface Session {
  session_id: string; user_name: string; content_title: string
  session_x: Break[]; session_y: Break[]
  user_profile?: UserProfile
  content_profile?: ContentProfile
  session_context?: SessionContext
}
interface Rating { annoyance: number; relevance: number; willingness: number }

const DEFAULT_CUSTOM = {
  person_name: '', age_group: '25-34', country: '',
  interests: [] as string[], ad_tolerance: 0.5,
  show_title: '', show_genre: 'Drama', show_duration_minutes: 45, is_series: false,
}
const DEFAULT_DURATION_STR = '45'

// ── small helpers ────────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-2 py-1.5 border-b border-slate-800/40 dark:border-slate-800/40 last:border-0">
      <span className="text-xs text-slate-500 shrink-0">{label}</span>
      <span className="text-xs text-slate-200 dark:text-slate-200 text-right">{value}</span>
    </div>
  )
}

function Tag({ label }: { label: string }) {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-700/60 text-slate-300 border border-slate-600/40">
      {label}
    </span>
  )
}

function ScaleRating({ value, onChange, readonly }: {
  value: number; onChange?: (v: number) => void; readonly?: boolean
}) {
  return (
    <div className="flex gap-1">
      {[1,2,3,4,5,6,7,8,9,10].map((n) => (
        <button
          key={n}
          onClick={() => !readonly && onChange?.(n)}
          className={`w-6 h-6 rounded text-[10px] font-semibold transition-colors border ${
            n === value
              ? 'bg-sky-600 border-sky-500 text-white'
              : readonly
              ? 'bg-slate-800 border-slate-700 text-slate-600 cursor-default'
              : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-sky-500 hover:text-sky-300 cursor-pointer'
          }`}
        >{n}</button>
      ))}
    </div>
  )
}

// ── info panels ──────────────────────────────────────────────────────────────

function UserCard({ p, name }: { p: UserProfile | undefined; name: string }) {
  const watchTime = p?.preferred_watch_time?.replace('TimeOfDay.', '') ?? '—'
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">User</p>
      <InfoRow label="Name" value={<span className="font-semibold">{p?.name ?? name}</span>} />
      <InfoRow label="Age Group" value={p?.age_group ?? '—'} />
      <InfoRow label="Profession" value={p?.profession ?? '—'} />
      <div className="py-1.5 border-b border-slate-800/40">
        <p className="text-xs text-slate-500 mb-1">Ad Interests</p>
        <p className="text-xs text-slate-200">{p?.interests?.join(', ') || '—'}</p>
      </div>
      <div className="py-1.5 border-b border-slate-800/40">
        <p className="text-xs text-slate-500 mb-1">Preferred Genres</p>
        <p className="text-xs text-slate-200">{p?.content_preferences?.join(', ') || '—'}</p>
      </div>
      <InfoRow label="Ad Tolerance" value={p ? p.ad_tolerance.toFixed(2) : '—'} />
      <InfoRow label="Binge Tendency" value={p ? p.binge_tendency.toFixed(2) : '—'} />
      <InfoRow label="Preferred Watch Time" value={watchTime} />
    </div>
  )
}

function ContentCard({ p, title }: { p: ContentProfile | undefined; title: string }) {
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Content</p>
      <InfoRow label="Title" value={<span className="font-semibold">{p?.title ?? title}</span>} />
      <InfoRow label="Genre" value={p?.genre ?? '—'} />
      <InfoRow label="Mood" value={p?.mood ?? '—'} />
      <InfoRow label="Duration" value={p?.duration_minutes ? `${p.duration_minutes} min` : '—'} />
      <InfoRow label="Language" value={p?.language ?? '—'} />
      <InfoRow label="Type" value={p ? (p.is_series ? 'Series episode' : 'Movie') : '—'} />
    </div>
  )
}

function ContextCard({ c }: { c: SessionContext | undefined }) {
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Session Context</p>
      <InfoRow label="Ads Shown" value={c?.ads_shown ?? '—'} />
      <InfoRow label="Total Breaks" value={c?.total_breaks ?? '—'} />
      <InfoRow label="Fatigue" value={c ? c.fatigue.toFixed(2) : '—'} />
      <InfoRow label="Minutes Into Session" value={c?.session_depth ?? '—'} />
      <InfoRow label="Content Duration" value={c?.content_duration ? `${c.content_duration} min` : '—'} />
      <InfoRow label="Binge Mode" value={c ? (c.binge ? 'Yes' : 'No') : '—'} />
    </div>
  )
}

// ── session card ─────────────────────────────────────────────────────────────

function SessionCard({
  label, breaks, rating, onRate, readonly = false
}: {
  label: string; breaks: Break[]; rating: Rating
  onRate?: (field: keyof Rating, v: number) => void; readonly?: boolean
}) {
  return (
    <div className="card flex-1 min-w-0 space-y-4">
      <h3 className="text-sm font-bold text-slate-300">Session {label}</h3>

      {/* Break list */}
      <div className="space-y-1.5">
        {breaks.length === 0
          ? <p className="text-xs text-slate-600">No ad breaks</p>
          : breaks.map((b, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-slate-500 font-mono text-xs w-8 shrink-0">{b.break_minute}m</span>
                <DecisionBadge decision={b.decision} size="sm" />
                <span className="text-slate-500 text-xs">{b.ad_category}</span>
              </div>
            ))
        }
      </div>

      {/* Ratings */}
      <div className="border-t border-slate-700/40 pt-3 space-y-3">
        {(['annoyance', 'relevance', 'willingness'] as (keyof Rating)[]).map((field) => (
          <div key={field} className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {field === 'willingness' ? 'Would Continue?' : field}
            </span>
            <ScaleRating
              value={rating[field]}
              onChange={readonly ? undefined : (v) => onRate?.(field, v)}
              readonly={readonly}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── main component ───────────────────────────────────────────────────────────

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
  const [durationStr, setDurationStr] = useState(DEFAULT_DURATION_STR)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [showDescription, setShowDescription] = useState('')

  function reset() {
    setSession(null); setSubmitted(false); setResults(null); setError(null)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setCustom(DEFAULT_CUSTOM); setDurationStr(DEFAULT_DURATION_STR); setShowDescription('')
  }

  async function loadFullSession(sessionId: string, base: Session) {
    try {
      const detail = (await abApi.session(sessionId)).data as Session
      setSession({ ...base, ...detail })
    } catch {
      setSession(base) // fall back to whatever start returned
    }
  }

  async function startSession() {
    reset(); setLoading(true)
    try {
      const base = (await abApi.start()).data as Session
      setSession(base)
      loadFullSession(base.session_id, base)
    } catch { setError('Failed to start session.') }
    finally { setLoading(false) }
  }

  async function startCustomSession() {
    if (!custom.interests.length) { setError('Select at least one interest.'); return }
    if (!custom.show_title.trim()) { setError('Enter a show or movie title.'); return }
    reset(); setLoading(true)
    try {
      const base = (await abApi.startCustom(custom)).data as Session
      setSession(base)
      setShowCustomForm(false)
      loadFullSession(base.session_id, base)
    } catch { setError('Failed to start custom session.') }
    finally { setLoading(false) }
  }

  async function submitRatings() {
    if (!session) return
    if (Object.values(xRating).some(v => v === 0) || Object.values(yRating).some(v => v === 0)) {
      setError('Please rate all fields (1–10) for both sessions.'); return
    }
    setLoading(true); setError(null)
    try {
      await abApi.rate(session.session_id, { session_label: 'X', ...xRating })
      await abApi.rate(session.session_id, { session_label: 'Y', ...yRating })
      setResults((await abApi.results()).data)
      setSubmitted(true)
    } catch { setError('Failed to submit ratings.') }
    finally { setLoading(false) }
  }

  async function lookupShow() {
    if (!custom.show_title.trim()) { setError('Enter a title first.'); return }
    setLookupLoading(true); setError(null)
    try {
      const d = (await abApi.lookupShow(custom.show_title)).data
      setCustom(c => ({ ...c, show_genre: d.genre, show_duration_minutes: d.duration_minutes, is_series: d.is_series }))
      setDurationStr(String(d.duration_minutes))
      setShowDescription(d.description || '')
    } catch { setError('Could not look up show — fill in manually.') }
    finally { setLookupLoading(false) }
  }

  function toggleInterest(cat: string) {
    setCustom(c => ({
      ...c,
      interests: c.interests.includes(cat) ? c.interests.filter(i => i !== cat) : [...c.interests, cat]
    }))
  }

  // Reveal logic
  const sessionDetail = session && submitted ? session : null
  let adaptadScore = 0, baselineScore = 0
  let winner: 'adaptad' | 'baseline' | 'tie' | null = null
  if (sessionDetail && (sessionDetail as unknown as { x_is_adaptad: boolean }).x_is_adaptad !== undefined) {
    const xIsAdaptAd = (sessionDetail as unknown as { x_is_adaptad: boolean }).x_is_adaptad
    const ar = xIsAdaptAd ? xRating : yRating
    const br = xIsAdaptAd ? yRating : xRating
    adaptadScore = ar.willingness + ar.relevance - ar.annoyance
    baselineScore = br.willingness + br.relevance - br.annoyance
    winner = adaptadScore > baselineScore ? 'adaptad' : adaptadScore < baselineScore ? 'baseline' : 'tie'
  }
  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  const inputCls = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="page-title">A/B Testing</h1>
          <p className="page-sub">Compare AdaptAd against random placement. Labels are randomized to prevent bias.</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button className="btn-secondary" onClick={() => { reset(); setShowCustomForm(v => !v) }} disabled={loading}>
            {showCustomForm ? 'Cancel' : 'Use My Profile'}
          </button>
          <button className="btn-primary" onClick={startSession} disabled={loading}>
            {loading ? 'Loading…' : 'New Session'}
          </button>
        </div>
      </div>

      {/* Custom profile form */}
      {showCustomForm && (
        <div className="card border-sky-700/30 space-y-5">
          <div>
            <h2 className="section-title mb-1">Real Person & Show</h2>
            <p className="text-xs text-slate-500">Enter your profile and a show you're watching for a personalised test.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="label">Your name</label>
              <input className={inputCls} placeholder="e.g. Priya Sharma" value={custom.person_name}
                onChange={e => setCustom(c => ({ ...c, person_name: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="label">Country</label>
              <input className={inputCls} placeholder="e.g. India" value={custom.country}
                onChange={e => setCustom(c => ({ ...c, country: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="label">Age group</label>
              <select className={inputCls} value={custom.age_group}
                onChange={e => setCustom(c => ({ ...c, age_group: e.target.value }))}>
                {AGE_GROUPS.map(g => <option key={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Ad tolerance <span className="text-sky-400 font-mono">{custom.ad_tolerance.toFixed(2)}</span></label>
              <input type="range" min="0" max="1" step="0.05" className="w-full accent-sky-500"
                value={custom.ad_tolerance}
                onChange={e => setCustom(c => ({ ...c, ad_tolerance: parseFloat(e.target.value) }))} />
              <div className="flex justify-between text-xs text-slate-600"><span>Low</span><span>High</span></div>
            </div>
          </div>
          <div className="space-y-2">
            <label className="label">Your interests</label>
            <div className="flex flex-wrap gap-2">
              {AD_CATEGORIES.map(cat => (
                <button key={cat} onClick={() => toggleInterest(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    custom.interests.includes(cat)
                      ? 'bg-sky-600/20 border-sky-500/50 text-sky-300'
                      : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500'
                  }`}>{cat}</button>
              ))}
            </div>
          </div>
          <div className="border-t border-slate-700/50 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1 sm:col-span-1">
              <label className="label">Show / movie title</label>
              <div className="flex gap-2">
                <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                  placeholder="e.g. Stranger Things" value={custom.show_title}
                  onChange={e => { setCustom(c => ({ ...c, show_title: e.target.value })); setShowDescription('') }} />
                <button onClick={lookupShow} disabled={lookupLoading || !custom.show_title.trim()}
                  className="shrink-0 px-3 py-2 bg-sky-700/30 hover:bg-sky-600/40 border border-sky-600/40 text-sky-300 text-xs font-semibold rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                  {lookupLoading ? '…' : 'Look Up'}
                </button>
              </div>
              {showDescription && <p className="text-xs text-slate-500 italic mt-1">{showDescription}</p>}
            </div>
            <div className="space-y-1">
              <label className="label">Genre</label>
              <select className={inputCls} value={custom.show_genre}
                onChange={e => setCustom(c => ({ ...c, show_genre: e.target.value }))}>
                {GENRES.map(g => <option key={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Duration (minutes)</label>
              <input type="text" inputMode="numeric" placeholder="e.g. 45" className={inputCls}
                value={durationStr}
                onChange={e => {
                  const raw = e.target.value.replace(/[^0-9]/g, '')
                  setDurationStr(raw)
                  const n = parseInt(raw, 10)
                  if (!isNaN(n) && n >= 10 && n <= 240) setCustom(c => ({ ...c, show_duration_minutes: n }))
                }}
                onBlur={() => {
                  const n = parseInt(durationStr, 10)
                  const v = isNaN(n) || n < 10 ? 45 : Math.min(240, n)
                  setDurationStr(String(v)); setCustom(c => ({ ...c, show_duration_minutes: v }))
                }} />
              <p className="text-xs text-slate-600">10–240 minutes</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="is-series" className="accent-sky-500"
              checked={custom.is_series} onChange={e => setCustom(c => ({ ...c, is_series: e.target.checked }))} />
            <label htmlFor="is-series" className="text-sm text-slate-400">This is a series episode</label>
          </div>
          <button className="btn-primary" onClick={startCustomSession} disabled={loading}>
            {loading ? 'Loading…' : 'Start with My Profile'}
          </button>
        </div>
      )}

      {error && <div className="card border-red-700/40 bg-red-950/20 text-red-400 text-sm">{error}</div>}

      {/* Empty state */}
      {!session && !loading && !showCustomForm && (
        <div className="card h-48 flex items-center justify-center text-slate-600 text-sm">
          Click "New Session" for a random test, or "Use My Profile" to test with your details
        </div>
      )}

      {/* Session loaded */}
      {session && (
        <>
          {/* Info banner */}
          <div className="card bg-slate-800/60 border-slate-700/40">
            <p className="text-sm text-slate-300 font-medium mb-1">Rate each session honestly.</p>
            <p className="text-xs text-slate-500 leading-relaxed">
              You do not know which system generated which. Consider whether the ads feel disruptive
              and whether they fit the user and content context.
            </p>
          </div>

          {/* Three info panels — always shown, graceful fallback if profile not yet loaded */}
          <div className="flex flex-col sm:flex-row gap-4">
            <UserCard p={session.user_profile} name={session.user_name} />
            <ContentCard p={session.content_profile} title={session.content_title} />
            <ContextCard c={session.session_context} />
          </div>

          {/* Rating guide */}
          {!submitted && (
            <div className="card bg-slate-800/40 border-slate-700/30 text-xs text-slate-500 leading-relaxed">
              <span className="text-slate-300 font-semibold">How to rate (1–10): </span>
              <span className="text-sky-400">Annoyance</span> — 1 = very annoying, 10 = barely noticeable ·{' '}
              <span className="text-sky-400">Relevance</span> — 1 = irrelevant, 10 = spot on ·{' '}
              <span className="text-sky-400">Would Continue</span> — 1 = would quit, 10 = definitely keep watching
            </div>
          )}

          {/* Session cards */}
          <div className="flex flex-col sm:flex-row gap-4">
            <SessionCard
              label="X"
              breaks={session.session_x as Break[]}
              rating={xRating}
              onRate={(f, v) => setXRating(r => ({ ...r, [f]: v }))}
              readonly={submitted}
            />
            <SessionCard
              label="Y"
              breaks={session.session_y as Break[]}
              rating={yRating}
              onRate={(f, v) => setYRating(r => ({ ...r, [f]: v }))}
              readonly={submitted}
            />
          </div>

          {/* Submit */}
          {!submitted && (
            <button className="btn-primary" onClick={submitRatings} disabled={loading}>
              {loading ? 'Submitting…' : 'Submit Ratings & Reveal'}
            </button>
          )}

          {/* Reveal */}
          {submitted && winner && (
            <div className={`card space-y-4 ${
              winner === 'adaptad' ? 'border-sky-500/40 bg-sky-900/10' :
              winner === 'baseline' ? 'border-red-500/40 bg-red-900/10' : 'border-slate-600/40'
            }`}>
              <div>
                {winner === 'adaptad' && <p className="text-sky-400 font-bold text-lg">AdaptAd won this round</p>}
                {winner === 'baseline' && <p className="text-red-400 font-bold text-lg">Baseline won this round</p>}
                {winner === 'tie' && <p className="text-slate-300 font-bold text-lg">This round was a tie</p>}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-slate-800/60 rounded-xl px-4 py-3">
                  <p className="text-xs text-sky-400 font-semibold mb-1">AdaptAd score: <span className="font-mono text-white">{adaptadScore > 0 ? '+' : ''}{adaptadScore} / 19</span></p>
                  <p className="text-xs text-slate-500">Uses your profile to decide when and whether to show each ad.</p>
                </div>
                <div className="bg-slate-800/60 rounded-xl px-4 py-3">
                  <p className="text-xs text-slate-300 font-semibold mb-1">Random baseline score: <span className="font-mono text-white">{baselineScore > 0 ? '+' : ''}{baselineScore} / 19</span></p>
                  <p className="text-xs text-slate-500">No intelligence — randomly shows or suppresses with no context.</p>
                </div>
              </div>
              <div className="bg-slate-800/40 rounded-xl px-4 py-3 text-xs text-slate-400 leading-relaxed">
                <p className="text-slate-200 font-semibold mb-1">How the score works</p>
                <p>Score = Willingness + Relevance − Annoyance. Range: −8 (worst) to +19 (best). Higher wins.</p>
              </div>
              {aggregate && (
                <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-700/40">
                  <div className="text-center">
                    <p className="text-xs text-slate-500 mb-1">AdaptAd Wins</p>
                    <p className="text-2xl font-bold text-sky-400">{String(aggregate.adaptad_wins)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500 mb-1">Baseline Wins</p>
                    <p className="text-2xl font-bold text-red-400">{String(aggregate.baseline_wins)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500 mb-1">Ties</p>
                    <p className="text-2xl font-bold text-slate-400">{String(aggregate.ties)}</p>
                  </div>
                </div>
              )}
              <button className="btn-secondary" onClick={startSession}>Run Another Session</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
