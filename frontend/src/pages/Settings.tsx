import { useStore } from '../store'
import { evolveApi } from '../api/client'

export default function Settings() {
  const { settings, updateSettings, chromosomeGenes, chromosomeFitness, clearChromosome } = useStore()

  async function loadBestChromosome() {
    try {
      const r = await evolveApi.loadBest()
      const genes = r.data.chromosome?.genes || r.data.genes
      const fitness = r.data.chromosome?.fitness ?? null
      if (genes) useStore.getState().setChromosome(genes, fitness)
      alert('Chromosome loaded.')
    } catch { alert('No saved chromosomes found.') }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-xl font-semibold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">Configure GA parameters, agent weights, and LLM provider</p>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-medium text-slate-300">Genetic Algorithm</h2>
        <div className="space-y-4">
          <div>
            <label className="label">Max Generations — {settings.maxGenerations}</label>
            <input type="range" min={10} max={200} step={10} value={settings.maxGenerations}
              onChange={(e) => updateSettings({ maxGenerations: Number(e.target.value) })}
              className="w-full mt-2 accent-sky-500" />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              <span>10</span><span>200</span>
            </div>
          </div>
          <div>
            <label className="label">Population Size — {settings.populationSize}</label>
            <input type="range" min={10} max={100} step={5} value={settings.populationSize}
              onChange={(e) => updateSettings({ populationSize: Number(e.target.value) })}
              className="w-full mt-2 accent-sky-500" />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              <span>10</span><span>100</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-medium text-slate-300">LLM Provider</h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">LLM Explanations</span>
          <button
            onClick={() => updateSettings({ llmEnabled: !settings.llmEnabled })}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.llmEnabled ? 'bg-sky-600' : 'bg-slate-700'}`}
          >
            <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${settings.llmEnabled ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
          </button>
        </div>
        {settings.llmEnabled && (
          <div>
            <label className="label">Provider</label>
            <select className="select-input mt-1 w-full" value={settings.llmProvider}
              onChange={(e) => updateSettings({ llmProvider: e.target.value as 'groq' | 'gemini' | 'off' })}>
              <option value="groq">Groq — llama-3.3-70b (14,400 req/day)</option>
              <option value="gemini">Gemini — gemini-2.5-flash (250 req/day)</option>
            </select>
            <p className="text-xs text-slate-600 mt-1">Set GROQ_API_KEY or GEMINI_API_KEY on the server.</p>
          </div>
        )}
        {!settings.llmEnabled && (
          <p className="text-xs text-slate-600">Using template-based reasoning. No API key required.</p>
        )}
      </div>

      <div className="card space-y-3">
        <h2 className="text-sm font-medium text-slate-300">Chromosome Management</h2>
        {chromosomeGenes ? (
          <div>
            <p className="text-sm text-slate-400">Active chromosome — fitness: <span className="font-mono text-sky-400">{chromosomeFitness?.toFixed(4) ?? 'unknown'}</span></p>
            <p className="text-xs font-mono text-slate-600 mt-1 break-all">[{chromosomeGenes.map((g) => g.toFixed(3)).join(', ')}]</p>
            <div className="flex gap-2 mt-3">
              <button className="btn-secondary text-sm" onClick={loadBestChromosome}>Reload Best Saved</button>
              <button className="btn-danger text-sm" onClick={clearChromosome}>Clear</button>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-sm text-slate-500">No chromosome loaded. Decisions use default (all genes = 0.5).</p>
            <button className="btn-secondary text-sm mt-3" onClick={loadBestChromosome}>Load Best Saved</button>
          </div>
        )}
      </div>

      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-300">Dark Mode</p>
            <p className="text-xs text-slate-600 mt-0.5">Always enabled</p>
          </div>
          <button
            onClick={() => updateSettings({ darkMode: !settings.darkMode })}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.darkMode ? 'bg-sky-600' : 'bg-slate-700'}`}
          >
            <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${settings.darkMode ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
          </button>
        </div>
      </div>
    </div>
  )
}
