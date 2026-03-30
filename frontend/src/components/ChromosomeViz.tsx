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

const GENE_DESCRIPTIONS: Record<string, { what: string; high: string; low: string }> = {
  fatigue_weight: {
    what: 'How much user fatigue weighs against showing an ad.',
    high: 'Very conservative — suppresses ads for tired users.',
    low: 'Fatigue barely reduces ad delivery.',
  },
  relevance_weight: {
    what: 'How much the ad-interest match influences the decision.',
    high: 'Only shows ads that closely match user interests.',
    low: 'Relevance has little effect on whether an ad runs.',
  },
  timing_weight: {
    what: 'How much time-of-day alignment matters.',
    high: 'Favors ads during the user\'s preferred viewing window.',
    low: 'Ads run regardless of the time of day.',
  },
  frequency_threshold: {
    what: 'The base score bar an ad opportunity must clear to be shown (range 0.35–0.65).',
    high: 'Stricter gate — fewer ads pass, better user experience.',
    low: 'Looser gate — more ads are shown.',
  },
  delay_probability: {
    what: 'Width of the DELAY zone just below the show threshold.',
    high: 'Prefers delaying marginal ads rather than suppressing them.',
    low: 'Borderline ads are suppressed instead of delayed.',
  },
  soften_threshold: {
    what: 'Width of the SOFTEN zone — how often a full ad is shortened instead.',
    high: 'Prefers showing a shorter ad over skipping entirely.',
    low: 'Ads are either shown in full or skipped — rarely softened.',
  },
  category_boost: {
    what: 'How much advertiser value is amplified when the ad category matches the user.',
    high: 'Strongly rewards category-relevant ads for advertiser revenue.',
    low: 'Category match gives little extra advertiser value.',
  },
  session_depth_factor: {
    what: 'How aggressively the system backs off as more ads have already run this session.',
    high: 'Increasingly cautious deep into a session — protects late-session experience.',
    low: 'Ad frequency stays steady throughout the session.',
  },
}

interface Props {
  genes: number[]
  fitness?: number | null
}

export default function ChromosomeViz({ genes, fitness }: Props) {
  return (
    <div className="space-y-3">
      {fitness != null && (
        <p className="text-sm text-slate-500 mb-3">
          Fitness: <span className="text-sky-400 font-mono font-semibold">{fitness.toFixed(4)}</span>
        </p>
      )}
      {GENE_NAMES.map((name, i) => {
        const val = genes[i] ?? 0
        const desc = GENE_DESCRIPTIONS[name]
        return (
          <div key={name} className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-300 w-36 shrink-0">{GENE_LABELS[name]}</span>
              <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-sky-500 rounded-full transition-all duration-500"
                  style={{ width: `${val * 100}%` }}
                />
              </div>
              <span className="text-xs font-mono text-slate-400 w-10 text-right">{val.toFixed(3)}</span>
            </div>
            {desc && (
              <div className="pl-[9.5rem] text-xs text-slate-500 leading-tight">
                {desc.what}{' '}
                <span className="text-sky-600">High: {desc.high}</span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
