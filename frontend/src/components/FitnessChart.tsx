import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'

interface DataPoint {
  generation: number
  best_fitness: number
  avg_fitness: number
}

interface Props {
  data: DataPoint[]
  targetFitness?: number
}

export default function FitnessChart({ data, targetFitness = 0.58 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="generation"
          stroke="#475569"
          tick={{ fontSize: 11, fill: '#64748b' }}
          label={{ value: 'Generation', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }}
        />
        <YAxis
          domain={([dataMin, dataMax]: [number, number]) => [
            Math.max(0, parseFloat((dataMin - 0.03).toFixed(2))),
            Math.min(1, parseFloat((dataMax + 0.03).toFixed(2))),
          ]}
          stroke="#475569"
          tick={{ fontSize: 11, fill: '#64748b' }}
          tickFormatter={(v) => v.toFixed(2)}
        />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
          labelStyle={{ color: '#cbd5e1' }}
          formatter={(v: number, name: string) => [v.toFixed(4), name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
        <ReferenceLine
          y={targetFitness}
          stroke="#0284c7"
          strokeDasharray="4 4"
          label={{ value: `Target ${targetFitness}`, fill: '#38bdf8', fontSize: 10, position: 'right' }}
        />
        <Line type="monotone" dataKey="best_fitness" stroke="#0ea5e9" strokeWidth={2} dot={false} name="Best fitness" />
        <Line type="monotone" dataKey="avg_fitness" stroke="#334155" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="Avg fitness" />
      </LineChart>
    </ResponsiveContainer>
  )
}
