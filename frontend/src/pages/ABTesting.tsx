import { useState, useEffect } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

const AD_CATEGORIES = ['tech', 'food', 'auto', 'fashion', 'finance', 'travel', 'health', 'gaming']
const AGE_GROUPS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
const GENRES = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Documentary', 'Romance', 'Thriller', 'Animation', 'Fantasy']

interface Break { break_minute: number; ad_category: string; decision: string }
interface Session {
  session_id: string; user_name: string; content_title: string
  session_x: Break[]; session_y: Break[]
}
interface SessionDetail extends Session {
  x_is_adaptad: boolean
  ratings: Record<string, { annoyance: number; relevance: number; willingness: number }>
}
interface Rating { annoyance: number; relevance: number; willingness: number }

function StarRating({ value, onChange, readonly }: { value: number; onChange?: (v: number) => void; readonly?: boolean }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          onClick={() => !readonly && onChange?.(n)}
          className={`text-lg transition-colors ${n <= value ? 'text-yellow-400' : 'text-zinc-700'} ${!readonly ? 'hover:text-zinc-500 cursor-pointer' : 'cursor-default'}`}
        >★</button>
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

function RevealCard({
  label, isAdaptAd, breaks, rating
}: { label: string; isAdaptAd: boolean; breaks: Break[]; rating: Rating }) {
  const score = rating.willingness + rating.relevance - rating.annoyance
  return (
    <div className={`card flex-1 min-w-0 ${isAdaptAd ? 'border-sky-600/40' : 'border-slate-600/40'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="section-title">Session {label}</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${isAdaptAd ? 'bg-sky-600/20 text-sky-300' : 'bg-slate-700 text-slate-400'}`}>
          {isAdaptAd ? 'AdaptAd' : 'Random Baseline'}
        </span>
      </div>
      <div className="space-y-1 mb-4 max-h-32 overflow-y-auto">
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
      <div className="border-t border-slate-700/50 pt-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Annoyance</span>
          <StarRating value={rating.annoyance} readonly />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Relevance</span>
          <StarRating value={rating.relevance} readonly />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Would continue?</span>
          <StarRating value={rating.willingness} readonly />
        </div>
        <div className="flex items-center justify-between pt-1 border-t border-slate-700/30">
          <span className="text-xs text-slate-500">Score (willingness + relevance − annoyance)</span>
          <span className={`text-sm font-bold font-mono ${score > 0 ? 'text-sky-400' : score < 0 ? 'text-red-400' : 'text-slate-400'}`}>
            {score > 0 ? '+' : ''}{score}
          </span>
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
const DEFAULT_DURATION_STR = '45'

export default function ABTesting() {
  const [session, setSession] = useState<Session | null>(null)
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null)
  const [xRating, setXRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [yRating, setYRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [custom, setCustom] = useState(DEFAULT_CUSTOM)
  const [history, setHistory] = useState<Record<string, unknown>[] | null>(null)
  const [historyAggregate, setHistoryAggregate] = useState<Record<string, unknown> | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [durationStr, setDurationStr] = useState(DEFAULT_DURATION_STR)

  useEffect(() => {
    abApi.history().then((r) => {
      const data = r.data as { sessions: Record<string, unknown>[]; aggregate: Record<string, unknown> }
      setHistory(data.sessions)
      setHistoryAggregate(data.aggregate)
    }).catch(() => {})
  }, [submitted])

  function updateRating(which: 'X' | 'Y', field: keyof Rating, v: number) {
    if (which === 'X') setXRating((r) => ({ ...r, [field]: v }))
    else setYRating((r) => ({ ...r, [field]: v }))
  }

  function resetSession() {
    setSession(null); setSessionDetail(null); setSubmitted(false); setResults(null); setError(null)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setCustom(DEFAULT_CUSTOM); setDurationStr(DEFAULT_DURATION_STR)
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
      // Fetch the full session detail for the reveal
      const [detailRes, resultsRes] = await Promise.all([
        abApi.session(session.session_id),
        abApi.results(),
      ])
      setSessionDetail(detailRes.data as SessionDetail)
      setResults(resultsRes.data)
      setSubmitted(true)
    } catch { setError('Failed to submit ratings.') }
    finally { setLoading(false) }
  }

  function toggleInterestFixed(cat: string) {
    setCustom((c) => ({
      ...c,
      interests: c.interests.includes(cat)
        ? c.interests.filter((i) => i !== cat)
        : [...c.interests, cat],
    }))
  }

  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  // Determine this-session winner for the reveal
  let thisSessionWinner: 'adaptad' | 'baseline' | 'tie' | null = null
  let adaptadScore = 0
  let baselineScore = 0
  if (sessionDetail) {
    const xIsAdaptAd = sessionDetail.x_is_adaptad
    const adaptadRating = xIsAdaptAd ? xRating : yRating
    const baselineRating = xIsAdaptAd ? yRating : xRating
    adaptadScore = adaptadRating.willingness + adaptadRating.relevance - adaptadRating.annoyance
    baselineScore = baselineRating.willingness + baselineRating.relevance - baselineRating.annoyance
    thisSessionWinner = adaptadScore > baselineScore ? 'adaptad' : adaptadScore < baselineScore ? 'baseline' : 'tie'
  }

  return (
    <div className="space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="page-title">A/B Testing</h1>
          <p className="page-sub">Compare AdaptAd against random placement. You rate two mystery sessions — then we reveal which was which.</p>
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
              <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. Priya Sharma" value={custom.person_name}
                onChange={(e) => setCustom((c) => ({ ...c, person_name: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="label">Country</label>
              <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. India" value={custom.country}
                onChange={(e) => setCustom((c) => ({ ...c, country: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="label">Age group</label>
              <select className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={custom.age_group} onChange={(e) => setCustom((c) => ({ ...c, age_group: e.target.value }))}>
                {AGE_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Ad tolerance <span className="text-sky-500 font-mono">{custom.ad_tolerance.toFixed(2)}</span></label>
              <input type="range" min="0" max="1" step="0.05" className="w-full accent-sky-500"
                value={custom.ad_tolerance} onChange={(e) => setCustom((c) => ({ ...c, ad_tolerance: parseFloat(e.target.value) }))} />
              <div className="flex justify-between text-xs text-slate-600"><span>Low (dislike ads)</span><span>High (don't mind)</span></div>
            </div>
          </div>
          <div className="space-y-2">
            <label className="label">Your interests <span className="text-slate-600 font-normal">(select all that apply)</span></label>
            <div className="flex flex-wrap gap-2">
              {AD_CATEGORIES.map((cat) => (
                <button key={cat} onClick={() => toggleInterestFixed(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${custom.interests.includes(cat) ? 'bg-sky-600/20 border-sky-500/50 text-sky-300' : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500'}`}>
                  {cat}
                </button>
              ))}
            </div>
          </div>
          <div className="border-t border-slate-700/50 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1 sm:col-span-1">
              <label className="label">Show / movie title</label>
              <input className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                placeholder="e.g. Stranger Things" value={custom.show_title}
                onChange={(e) => setCustom((c) => ({ ...c, show_title: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="label">Genre</label>
              <select className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={custom.show_genre} onChange={(e) => setCustom((c) => ({ ...c, show_genre: e.target.value }))}>
                {GENRES.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="label">Duration (minutes)</label>
              <input type="number" min="10" max="240"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                value={durationStr}
                onChange={(e) => {
                  setDurationStr(e.target.value)
                  const parsed = parseInt(e.target.value, 10)
                  if (!isNaN(parsed) && parsed >= 10) {
                    setCustom((c) => ({ ...c, show_duration_minutes: parsed }))
                  }
                }}
                onBlur={() => {
                  const parsed = parseInt(durationStr, 10)
                  const clamped = isNaN(parsed) ? 45 : Math.max(10, Math.min(240, parsed))
                  setDurationStr(String(clamped))
                  setCustom((c) => ({ ...c, show_duration_minutes: clamped }))
                }} />
              <p className="text-xs text-slate-600">10–240 minutes</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="is-series" className="accent-sky-500"
              checked={custom.is_series} onChange={(e) => setCustom((c) => ({ ...c, is_series: e.target.checked }))} />
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

      {/* Rating phase */}
      {session && !submitted && (
        <>
          <div className="card">
            <p className="text-sm text-zinc-400">
              User: <span className="text-zinc-100 font-medium">{session.user_name}</span>
              <span className="text-zinc-600 mx-2">·</span>
              Content: <span className="text-zinc-100 font-medium">{session.content_title}</span>
            </p>
            <p className="text-xs text-zinc-500 mt-2 leading-relaxed">
              Below are two ad schedules for the same user watching the same content.
              One was decided by <span className="text-sky-400">AdaptAd</span> (considering fatigue, relevance, timing).
              The other is a <span className="text-slate-300">random baseline</span> (show or suppress at random).
              The labels are shuffled — you don't know which is which. Rate honestly, then submit to see the reveal.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-4">
            <SessionView label="X" breaks={session.session_x as Break[]} rating={xRating} onRate={(f, v) => updateRating('X', f, v)} />
            <SessionView label="Y" breaks={session.session_y as Break[]} rating={yRating} onRate={(f, v) => updateRating('Y', f, v)} />
          </div>
          <div className="card bg-slate-800/40 text-xs text-slate-500 leading-relaxed">
            <span className="text-slate-300 font-semibold">How to rate: </span>
            <span className="text-sky-400">Annoyance</span> — how disruptive did the ads feel? (1 = very annoying, 5 = barely noticeable) ·{' '}
            <span className="text-sky-400">Relevance</span> — did the ads feel related to your interests? ·{' '}
            <span className="text-sky-400">Would continue?</span> — would you keep watching after this experience?
          </div>
          <button className="btn-primary" onClick={submitRatings} disabled={loading}>
            {loading ? 'Submitting…' : 'Submit Ratings & Reveal'}
          </button>
        </>
      )}

      {/* Reveal + results phase */}
      {submitted && sessionDetail && aggregate && (
        <div className="space-y-5">
          {/* The reveal */}
          <div className="card border-sky-700/30">
            <h2 className="section-title mb-1">The Reveal</h2>
            <p className="text-xs text-slate-500 mb-4">Here's what each session actually was, and the scores based on your ratings.</p>
            <div className="flex flex-col sm:flex-row gap-4">
              <RevealCard
                label="X"
                isAdaptAd={sessionDetail.x_is_adaptad}
                breaks={session!.session_x as Break[]}
                rating={xRating}
              />
              <RevealCard
                label="Y"
                isAdaptAd={!sessionDetail.x_is_adaptad}
                breaks={session!.session_y as Break[]}
                rating={yRating}
              />
            </div>
          </div>

          {/* This session verdict */}
          <div className={`card space-y-4 ${
            thisSessionWinner === 'adaptad' ? 'border-sky-500/40 bg-sky-900/10' :
            thisSessionWinner === 'baseline' ? 'border-red-500/40 bg-red-900/10' :
            'border-slate-600/40'
          }`}>
            <div>
              {thisSessionWinner === 'adaptad' && <p className="text-sky-400 font-bold text-lg">AdaptAd won this round</p>}
              {thisSessionWinner === 'baseline' && <p className="text-red-400 font-bold text-lg">Baseline won this round</p>}
              {thisSessionWinner === 'tie' && <p className="text-slate-300 font-bold text-lg">This round was a tie</p>}
            </div>

            {/* Score breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-slate-800/60 rounded-xl px-4 py-3 space-y-1">
                <p className="text-xs text-sky-400 font-semibold">AdaptAd score: <span className="font-mono text-white">{adaptadScore > 0 ? '+' : ''}{adaptadScore} / 10</span></p>
                <p className="text-xs text-slate-500">Uses your profile (fatigue, interests, time of day, session depth) to decide <em>when</em> and <em>whether</em> to show each ad. It can choose to SHOW, SOFTEN (shorter ad), DELAY, or SUPPRESS.</p>
              </div>
              <div className="bg-slate-800/60 rounded-xl px-4 py-3 space-y-1">
                <p className="text-xs text-slate-300 font-semibold">Random baseline score: <span className="font-mono text-white">{baselineScore > 0 ? '+' : ''}{baselineScore} / 10</span></p>
                <p className="text-xs text-slate-500">No intelligence — randomly picks SHOW or SUPPRESS for every ad opportunity with no knowledge of who you are or what you're watching.</p>
              </div>
            </div>

            {/* How the score works */}
            <div className="bg-slate-800/40 rounded-xl px-4 py-3 text-xs text-slate-400 leading-relaxed">
              <p className="text-slate-200 font-semibold mb-1">How the score is calculated</p>
              <p>
                Score = <span className="text-sky-400">Willingness to continue</span> + <span className="text-sky-400">Relevance</span> − <span className="text-red-400">Annoyance</span>.
                Each metric is 1–5, so scores range from −3 (very annoying, irrelevant, would quit) to +9 (not annoying, very relevant, would keep watching).
                The system with the higher score wins the round.
              </p>
            </div>

            {/* What winning means */}
            <div className="bg-slate-800/40 rounded-xl px-4 py-3 text-xs text-slate-400 leading-relaxed">
              <p className="text-slate-200 font-semibold mb-1">What does a win mean?</p>
              {thisSessionWinner === 'adaptad' && (
                <p>AdaptAd's evolved chromosome made better ad decisions for this user and content. By timing ads carefully — suppressing them when you're fatigued, delaying them during intense scenes, only showing relevant ones — it produced a less annoying, more relevant viewing experience than random placement. This is the hypothesis (H1) we're testing: that an evolved policy beats a dumb baseline.</p>
              )}
              {thisSessionWinner === 'baseline' && (
                <p>The random baseline happened to score higher this round. This can occur — random placement sometimes gets lucky and shows the right ad at the right moment purely by chance. One session isn't enough to draw conclusions; run more sessions to see if AdaptAd pulls ahead consistently.</p>
              )}
              {thisSessionWinner === 'tie' && (
                <p>Both policies scored identically this round. This usually happens when the content has very few ad breaks, or your ratings were similar for both sessions. Run more sessions to build a clearer picture.</p>
              )}
            </div>
          </div>

          {/* Running aggregate */}
          <div className="card space-y-4">
            <div>
              <h2 className="section-title mb-1">Running Totals</h2>
              <p className="text-xs text-slate-500">
                Across all sessions completed in this browser session. The more sessions you run, the more statistically meaningful the result.
                If AdaptAd consistently wins, it validates H1: the GA-evolved policy produces a measurably better viewing experience than random ad placement.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="card bg-show/5 border-show/20 text-center">
                <p className="label mb-1">AdaptAd Wins</p>
                <p className="text-3xl font-bold text-show">{String(aggregate.adaptad_wins)}</p>
                <p className="text-xs text-slate-600 mt-2">Rounds where the evolved policy was preferred</p>
              </div>
              <div className="card bg-suppress/5 border-suppress/20 text-center">
                <p className="label mb-1">Baseline Wins</p>
                <p className="text-3xl font-bold text-suppress">{String(aggregate.baseline_wins)}</p>
                <p className="text-xs text-slate-600 mt-2">Rounds where random placement was preferred</p>
              </div>
              <div className="card text-center">
                <p className="label mb-1">Ties</p>
                <p className="text-3xl font-bold text-zinc-400">{String(aggregate.ties)}</p>
                <p className="text-xs text-slate-600 mt-2">Equal scores — no winner</p>
              </div>
            </div>
          </div>

          <button className="btn-secondary" onClick={startSession}>Run Another Session</button>
        </div>
      )}

      {!session && !loading && !showCustomForm && (
        <div className="card h-48 flex items-center justify-center text-zinc-600 text-sm">
          Click "New Session" for a random test, or "Use My Profile" to test with your own details
        </div>
      )}

      {/* Persistent history from database */}
      {history !== null && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="section-title mb-0.5">Session History</h2>
              <p className="text-xs text-slate-500">
                All completed sessions saved to the database — persists across page reloads and server restarts.
                {historyAggregate && Number(historyAggregate.total) > 0 && (
                  <span className="ml-2 text-sky-400 font-medium">
                    AdaptAd win rate: {Math.round(Number(historyAggregate.win_rate) * 100)}% across {Number(historyAggregate.total)} sessions
                  </span>
                )}
              </p>
            </div>
            <button className="btn-secondary text-xs py-1 px-3" onClick={() => setShowHistory(v => !v)}>
              {showHistory ? 'Hide' : `Show ${history.length}`}
            </button>
          </div>

          {historyAggregate && Number(historyAggregate.total) > 0 && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">AdaptAd Wins</p>
                <p className="text-xl font-bold text-show">{String(historyAggregate.adaptad_wins)}</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Baseline Wins</p>
                <p className="text-xl font-bold text-suppress">{String(historyAggregate.baseline_wins)}</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Ties</p>
                <p className="text-xl font-bold text-zinc-400">{String(historyAggregate.ties)}</p>
              </div>
            </div>
          )}

          {showHistory && history.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">No completed sessions yet. Run and rate a session to see it here.</p>
          )}

          {showHistory && history.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-700/50 text-slate-500">
                    <th className="text-left py-2 pr-4 font-medium">User</th>
                    <th className="text-left py-2 pr-4 font-medium">Age / Country</th>
                    <th className="text-left py-2 pr-4 font-medium">Content</th>
                    <th className="text-left py-2 pr-4 font-medium">Interests</th>
                    <th className="text-center py-2 pr-4 font-medium">AdaptAd</th>
                    <th className="text-center py-2 pr-4 font-medium">Baseline</th>
                    <th className="text-center py-2 font-medium">Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((s) => (
                    <tr key={String(s.session_id)} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                      <td className="py-2 pr-4 text-slate-300 font-medium">
                        {String(s.user_name)}
                        {s.is_custom && <span className="ml-1 text-sky-600 text-[10px]">custom</span>}
                      </td>
                      <td className="py-2 pr-4 text-slate-500">
                        {String(s.user_age_group)}{s.user_country ? ` · ${String(s.user_country)}` : ''}
                      </td>
                      <td className="py-2 pr-4 text-slate-400 max-w-[160px] truncate">
                        {String(s.content_title)}
                        <span className="ml-1 text-slate-600">{String(s.content_genre)}</span>
                      </td>
                      <td className="py-2 pr-4 text-slate-500">
                        {(s.user_interests as string[]).slice(0, 3).join(', ')}
                      </td>
                      <td className="py-2 pr-4 text-center font-mono">
                        <span className={Number(s.adaptad_score) > Number(s.baseline_score) ? 'text-sky-400 font-bold' : 'text-slate-500'}>
                          {s.adaptad_score != null ? (Number(s.adaptad_score) > 0 ? `+${s.adaptad_score}` : String(s.adaptad_score)) : '—'}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-center font-mono">
                        <span className={Number(s.baseline_score) > Number(s.adaptad_score) ? 'text-red-400 font-bold' : 'text-slate-500'}>
                          {s.baseline_score != null ? (Number(s.baseline_score) > 0 ? `+${s.baseline_score}` : String(s.baseline_score)) : '—'}
                        </span>
                      </td>
                      <td className="py-2 text-center">
                        {s.winner === 'adaptad' && <span className="px-2 py-0.5 bg-sky-600/20 text-sky-400 rounded-full text-[10px] font-semibold">AdaptAd</span>}
                        {s.winner === 'baseline' && <span className="px-2 py-0.5 bg-red-600/20 text-red-400 rounded-full text-[10px] font-semibold">Baseline</span>}
                        {s.winner === 'tie' && <span className="px-2 py-0.5 bg-slate-700 text-slate-400 rounded-full text-[10px] font-semibold">Tie</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
