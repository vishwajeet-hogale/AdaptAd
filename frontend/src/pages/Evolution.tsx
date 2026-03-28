import { useState, useCallback, useEffect } from 'react'
import { evolveApi } from '../api/client'
import { useStore } from '../store'
import { useWebSocket, type WsMessage } from '../hooks/useWebSocket'
import FitnessChart from '../components/FitnessChart'
import ChromosomeViz from '../components/ChromosomeViz'

interface GenPoint { generation: number; best_fitness: number; avg_fitness: number; diversity: number }

export default function Evolution() {
  const { settings, setChromosome, activeJobId, setActiveJobId } = useStore()
  const chromosomeGenes = useStore((s) => s.chromosomeGenes)
  const chromosomeFitness = useStore((s) => s.chromosomeFitness)

  useEffect(() => { setActiveJobId(null) }, [])

  const [history, setHistory] = useState<GenPoint[]>([])
  const [status, setStatus] = useState<string>('idle')
  const [finalGenes, setFinalGenes] = useState<number[] | null>(null)
  const [diversity, setDiversity] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === 'generation') {
      setHistory((prev) => [...prev, msg.data])
      setDiversity(msg.data.diversity)
      setStatus('running')
    } else if (msg.type === 'converged') {
      setFinalGenes(msg.data.best_chromosome)
      setChromosome(msg.data.best_chromosome, msg.data.fitness)
      setStatus('converged')
    } else if (msg.type === 'error') {
      setError(msg.data.message)
      setStatus('error')
    }
  }, [setChromosome])

  useWebSocket(activeJobId, { onMessage: handleMessage })

  async function startEvolution() {
    setHistory([])
    setError(null)
    setStatus('starting')
    try {
      const r = await evolveApi.start(settings.maxGenerations)
      setActiveJobId(r.data.job_id)
      setStatus('queued')
    } catch {
      setError('Failed to start evolution. Is the server running?')
      setStatus('error')
    }
  }

  async function stopEvolution() {
    if (!activeJobId) return
    await evolveApi.stop(activeJobId).catch(() => {})
    setStatus('stopped')
    setActiveJobId(null)
  }

  async function loadBest() {
    try {
      const r = await evolveApi.loadBest()
      const genes = r.data.chromosome?.genes || r.data.genes
      const fitness = r.data.chromosome?.fitness ?? null
      if (genes) { setChromosome(genes, fitness); setFinalGenes(genes) }
    } catch { setError('No saved chromosomes found.') }
  }

  const displayGenes = finalGenes ?? chromosomeGenes
  const currentBest = history.length > 0 ? history[history.length - 1].best_fitness : null

  const statusColor =
    status === 'converged' ? 'text-show' :
    status === 'running'   ? 'text-sky-400' :
    status === 'error'     ? 'text-suppress' :
    'text-slate-400'

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Evolution</h1>
          <p className="text-sm text-slate-500 mt-1">Evolve the 8-gene chromosome via genetic algorithm</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button className="btn-secondary" onClick={loadBest}>Load Best Saved</button>
          {status === 'running' || status === 'queued'
            ? <button className="btn-danger" onClick={stopEvolution}>Stop</button>
            : <button className="btn-primary" onClick={startEvolution} disabled={status === 'starting'}>
                {status === 'starting' ? 'Starting…' : 'Start Evolution'}
              </button>
          }
        </div>
      </div>

      {error && (
        <div className="card border-red-800/40 bg-red-950/20 text-red-400 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card text-center">
          <p className="label mb-2">Status</p>
          <p className={`font-medium capitalize ${statusColor}`}>{status}</p>
        </div>
        <div className="card text-center">
          <p className="label mb-2">Generation</p>
          <p className="font-mono text-xl text-slate-200">{history.length}</p>
        </div>
        <div className="card text-center">
          <p className="label mb-2">Best Fitness</p>
          <p className="font-mono text-xl text-sky-400">
            {currentBest?.toFixed(4) ?? chromosomeFitness?.toFixed(4) ?? '—'}
          </p>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-slate-300">Fitness over Generations</h2>
          <span className="text-xs text-slate-500 font-mono">Diversity: {(diversity * 100).toFixed(1)}%</span>
        </div>
        {history.length > 0
          ? <FitnessChart data={history} />
          : <div className="h-48 flex items-center justify-center text-slate-600 text-sm">Start evolution to see live chart</div>
        }
      </div>

      {displayGenes && (
        <div className="card">
          <h2 className="text-sm font-medium text-slate-300 mb-4">Chromosome Genes</h2>
          <ChromosomeViz genes={displayGenes} fitness={chromosomeFitness} />
        </div>
      )}
    </div>
  )
}
