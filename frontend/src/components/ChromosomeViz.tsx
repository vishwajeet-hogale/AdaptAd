const GENE_NAMES = [
  'fatigue_weight', 'relevance_weight', 'timing_weight', 'frequency_threshold',
  'delay_probability', 'soften_threshold', 'category_boost', 'session_depth_factor',
]

const GENE_LABELS: Record<string, string> = {
  fatigue_weight: 'Fatigue Weight',
  relevance_weight: 'Relevance Weight',
  timing_weight: 'Timing Weight',
  frequency_threshold: 'Frequency Threshold',
  delay_probability: 'Delay Probability',
  soften_threshold: 'Soften Threshold',
  category_boost: 'Category Boost',
  session_depth_factor: 'Session Depth',
}

interface Props {
  genes: number[]
  fitness?: number | null
}

export default function ChromosomeViz({ genes, fitness }: Props) {
  return (
    <div className="space-y-2.5">
      {fitness != null && (
        <p className="text-sm text-slate-500 mb-3">
          Fitness: <span className="text-sky-400 font-mono font-semibold">{fitness.toFixed(4)}</span>
        </p>
      )}
      {GENE_NAMES.map((name, i) => {
        const val = genes[i] ?? 0
        return (
          <div key={name} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-36 shrink-0">{GENE_LABELS[name]}</span>
            <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-sky-500 rounded-full transition-all duration-500"
                style={{ width: `${val * 100}%` }}
              />
            </div>
            <span className="text-xs font-mono text-slate-400 w-10 text-right">{val.toFixed(3)}</span>
          </div>
        )
      })}
    </div>
  )
}
