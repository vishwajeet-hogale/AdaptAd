import { useState } from 'react'
import DecisionBadge from './DecisionBadge'

interface BreakDecision {
  break_minute: number
  ad_category: string
  decision: string
  combined_score: number
  fatigue_at_break: number
  reasoning: string
}

interface Props {
  durationMinutes: number
  decisions: BreakDecision[]
  currentMinute?: number
}

const decisionDotColor: Record<string, string> = {
  SHOW: 'bg-show border-show',
  SOFTEN: 'bg-soften border-soften',
  DELAY: 'bg-delay border-delay',
  SUPPRESS: 'bg-suppress border-suppress',
}

export default function SessionTimeline({ durationMinutes, decisions, currentMinute }: Props) {
  const [selected, setSelected] = useState<number | null>(null)

  return (
    <div>
      <div className="relative h-8 bg-slate-800 rounded-full overflow-visible mb-6">
        {currentMinute != null && (
          <div
            className="absolute top-0 left-0 h-full bg-sky-900/40 rounded-full transition-all duration-300"
            style={{ width: `${(currentMinute / durationMinutes) * 100}%` }}
          />
        )}
        {decisions.map((d, i) => {
          const pct = (d.break_minute / durationMinutes) * 100
          return (
            <button
              key={i}
              className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full border-2 z-10 transition-transform hover:scale-125 ${decisionDotColor[d.decision] ?? 'bg-slate-500 border-slate-400'}`}
              style={{ left: `${pct}%` }}
              onClick={() => setSelected(selected === i ? null : i)}
              title={`${d.break_minute}min: ${d.decision}`}
            />
          )
        })}
        <div className="absolute -bottom-5 left-0 text-xs text-slate-500">0m</div>
        <div className="absolute -bottom-5 right-0 text-xs text-slate-500">{durationMinutes}m</div>
      </div>

      {selected !== null && decisions[selected] && (
        <div className="card mt-8 space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-slate-400">{decisions[selected].break_minute}min</span>
            <DecisionBadge decision={decisions[selected].decision} />
            <span className="text-xs text-slate-500">{decisions[selected].ad_category}</span>
            <span className="ml-auto text-xs font-mono text-slate-400">score {decisions[selected].combined_score.toFixed(3)}</span>
          </div>
          <p className="text-xs text-slate-500">{decisions[selected].reasoning}</p>
        </div>
      )}
    </div>
  )
}
