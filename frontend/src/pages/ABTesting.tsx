import { useState } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

interface Break { break_minute: number; ad_category: string; decision: string }
interface UserProfile {
  id: number
  name: string
  age_group: string
  profession: string
  interests: string[]
  content_preferences: string[]
  binge_tendency: number
  fatigue_level: number
  engagement_score: number
  ad_tolerance: number
  preferred_watch_time: string
  session_count: number
}

interface ContentProfile {
  id: number
  title: string
  genre?: string | null
  duration?: number | null
  mood?: string | null
}

interface SessionContext {
  ads_shown: number
  total_breaks: number
  fatigue: number
  session_depth: number
  content_duration?: number | null
  binge: boolean
}

interface Session {
  session_id: string
  user_name: string
  content_title: string
  user_profile: UserProfile
  content_profile: ContentProfile
  session_context: SessionContext
  session_x: Break[]
  session_y: Break[]
}

interface Rating {
  annoyance: number
  relevance: number
  willingness: number
}

function formatWatchTime(value: string) {
  return value.replace('TimeOfDay.', '')
}

function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} onClick={() => onChange(n)} className={`text-lg transition-colors ${n <= value ? 'text-yellow-400' : 'text-zinc-700 hover:text-zinc-500'}`}>★</button>
      ))}
    </div>
  )
}

function ContextCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="card">
      <h3 className="section-title mb-3">{title}</h3>
      <div className="space-y-2 text-sm text-zinc-300">{children}</div>
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

export default function ABTesting() {
  const [session, setSession] = useState<Session | null>(null)
  const [xRating, setXRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [yRating, setYRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function updateRating(which: 'X' | 'Y', field: keyof Rating, v: number) {
    if (which === 'X') setXRating((r) => ({ ...r, [field]: v }))
    else setYRating((r) => ({ ...r, [field]: v }))
  }

  async function startSession() {
    setLoading(true); setError(null); setSubmitted(false)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
    try {
      const r = await abApi.start()
      setSession(r.data as Session)
    } catch { setError('Failed to start A/B session.') }
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

  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  return (
    <div className="space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="page-title">A/B Testing</h1>
          <p className="page-sub">Compare AdaptAd against random placement. Labels are randomized to prevent bias.</p>
        </div>
        <button className="btn-primary shrink-0" onClick={startSession} disabled={loading}>
          {loading ? 'Loading…' : 'New Session'}
        </button>
      </div>

      {error && (
        <div className="card border-red-700/40 bg-red-950/20 text-red-400 text-sm">{error}</div>
      )}

      {session && !submitted && (
        <>
          <div className="card">
            <p className="text-sm text-zinc-400">
              Rate each session honestly. You do not know which system generated which.
            </p>
            <p className="text-xs text-zinc-600 mt-1.5">
              Consider whether the ads feel disruptive and whether they fit the user and content context.
            </p>
          </div>
                
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ContextCard title="User">
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Name</span>
                <span className="text-zinc-100 font-medium">{session.user_profile.name}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Age Group</span>
                <span>{session.user_profile.age_group}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Profession</span>
                <span>{session.user_profile.profession}</span>
              </div>
              <div>
                <span className="text-zinc-500">Ad Interests</span>
                <p className="mt-1 text-zinc-100">{session.user_profile.interests.join(', ')}</p>
              </div>
              <div>
                <span className="text-zinc-500">Preferred Genres</span>
                <p className="mt-1 text-zinc-100">{session.user_profile.content_preferences.join(', ')}</p>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Ad Tolerance</span>
                <span>{session.user_profile.ad_tolerance}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Binge Tendency</span>
                <span>{session.user_profile.binge_tendency}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Preferred Watch Time</span>
                <span>{formatWatchTime(session.user_profile.preferred_watch_time)}</span>
              </div>
            </ContextCard>
                
            <ContextCard title="Content">
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Title</span>
                <span className="text-zinc-100 font-medium">{session.content_profile.title}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Genre</span>
                <span>{session.content_profile.genre ?? 'Unknown'}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Mood</span>
                <span>{session.content_profile.mood ?? 'Unknown'}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Duration</span>
                <span>
                  {session.content_profile.duration != null
                    ? `${session.content_profile.duration} min`
                    : 'Unknown'}
                </span>
              </div>
            </ContextCard>
                  
            <ContextCard title="Session Context">
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Ads Shown</span>
                <span>{session.session_context.ads_shown}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Total Breaks</span>
                <span>{session.session_context.total_breaks}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Fatigue</span>
                <span>{session.session_context.fatigue}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Minutes Into Session</span>
                <span>{session.session_context.session_depth}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Content Duration</span>
                <span>
                  {session.session_context.content_duration != null
                    ? `${session.session_context.content_duration} min`
                    : 'Unknown'}
                </span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-zinc-500">Binge Mode</span>
                <span>{session.session_context.binge ? 'Yes' : 'No'}</span>
              </div>
            </ContextCard>
          </div>
          <div className="flex flex-col sm:flex-row gap-4">
            <SessionView label="X" breaks={session.session_x as Break[]} rating={xRating} onRate={(f, v) => updateRating('X', f, v)} />
            <SessionView label="Y" breaks={session.session_y as Break[]} rating={yRating} onRate={(f, v) => updateRating('Y', f, v)} />
          </div>
          <button className="btn-primary" onClick={submitRatings} disabled={loading}>Submit Ratings</button>
        </>
      )}

      {submitted && aggregate && (
        <div className="card space-y-4">
          <h2 className="section-title text-show">Ratings submitted — aggregate results</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card bg-show/5 border-show/20">
              <p className="label mb-1">AdaptAd Wins</p>
              <p className="text-2xl font-bold text-show">{String(aggregate.adaptad_wins)}</p>
            </div>
            <div className="card bg-suppress/5 border-suppress/20">
              <p className="label mb-1">Baseline Wins</p>
              <p className="text-2xl font-bold text-suppress">{String(aggregate.baseline_wins)}</p>
            </div>
            <div className="card">
              <p className="label mb-1">Ties</p>
              <p className="text-2xl font-bold text-zinc-400">{String(aggregate.ties)}</p>
            </div>
          </div>
          <button className="btn-secondary" onClick={startSession}>Run Another Session</button>
        </div>
      )}

      {!session && !loading && (
        <div className="card h-48 flex items-center justify-center text-zinc-600 text-sm">
          Click "New Session" to start an A/B test
        </div>
      )}
    </div>
  )
}
