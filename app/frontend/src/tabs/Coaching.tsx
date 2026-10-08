import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Lightbulb, Award, TrendingUp, AlertTriangle, Users } from 'lucide-react'
import { getJSON, pct, TIER_COLORS } from '../api'
import { Card, Loading, ErrorBox, Pill } from '../components/ui'
import { Header } from './Dashboard'

interface Tier { tier: string; agents: number; avg_save_rate: number; avg_handle_time: number; avg_nps: number }
interface ScatterPt { agent_name: string; team: string; tier: string; save_rate: number; handle_time: number; nps: number }
interface CoachRow { agent_name: string; team: string; avg_handle_time_min: number; nps: number; offer_conversion_rate: number; save_rate: number }
interface AgentData { tiers: Tier[]; scatter: ScatterPt[]; coaching_table: CoachRow[]; insight: string }

const TIER_ICON: Record<string, React.ReactNode> = {
  'Top Performer': <Award size={18} />,
  'On Target': <TrendingUp size={18} />,
  'Needs Coaching': <Users size={18} />,
  'At Risk': <AlertTriangle size={18} />,
}

export default function Coaching() {
  const [data, setData] = useState<AgentData | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    getJSON<AgentData>('/api/agents').then(setData).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loading label="Loading agent performance…" />

  const byTier: Record<string, ScatterPt[]> = {}
  data.scatter.forEach((p) => { (byTier[p.tier] ||= []).push(p) })
  const tierOrder = ['Top Performer', 'On Target', 'Needs Coaching', 'At Risk']

  return (
    <div className="space-y-6">
      <Header title="Agent Coaching" subtitle="Performance tiers, save-rate drivers, and targeted coaching opportunities" />

      {/* Insight banner */}
      <div className="card p-4 flex items-start gap-3 border-spectrum-sky/20 bg-gradient-to-r from-spectrum-blue/10 to-transparent">
        <div className="h-9 w-9 rounded-lg bg-spectrum-blue/20 flex items-center justify-center shrink-0">
          <Lightbulb size={18} className="text-spectrum-sky" />
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-spectrum-sky font-semibold">Coaching Insight</div>
          <div className="text-sm text-slate-200 mt-0.5">{data.insight}</div>
        </div>
      </div>

      {/* Tier cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data.tiers.map((t) => {
          const color = TIER_COLORS[t.tier] || '#0099d8'
          return (
            <div key={t.tier} className="card p-5 relative overflow-hidden">
              <div className="absolute inset-x-0 top-0 h-1" style={{ background: color }} />
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">{t.tier}</span>
                <span style={{ color }}>{TIER_ICON[t.tier]}</span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white tabular-nums">{t.agents}</span>
                <span className="text-xs text-slate-400">agents</span>
              </div>
              <div className="mt-3 space-y-1.5">
                <StatLine label="Avg save rate" value={pct(t.avg_save_rate)} color={color} />
                <StatLine label="Avg handle time" value={`${t.avg_handle_time.toFixed(1)} min`} />
                <StatLine label="Avg NPS" value={t.avg_nps.toFixed(0)} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Scatter */}
      <Card title="Save Rate vs. Handle Time" right={<span className="text-xs text-slate-400">Each point = one agent · colored by tier</span>}>
        <ResponsiveContainer width="100%" height={360}>
          <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis type="number" dataKey="handle_time" name="Handle time"
              unit=" min" stroke="#7089a6" fontSize={11}
              domain={['dataMin - 1', 'dataMax + 1']}
              label={{ value: 'Avg Handle Time (min)', position: 'insideBottom', offset: -5, fill: '#7089a6', fontSize: 11 }} />
            <YAxis type="number" dataKey="save_rate" name="Save rate"
              stroke="#7089a6" fontSize={11} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              domain={[0, 1]}
              label={{ value: 'Save Rate', angle: -90, position: 'insideLeft', fill: '#7089a6', fontSize: 11 }} />
            <ZAxis type="number" dataKey="nps" range={[40, 260]} name="NPS" />
            <Tooltip
              cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }}
              contentStyle={{ background: '#0d2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }}
              formatter={(v: number, n: string) =>
                n === 'Save rate' ? [pct(Number(v)), n] : n === 'Handle time' ? [`${Number(v).toFixed(1)} min`, n] : [v, n]}
              labelFormatter={() => ''}
              content={({ payload }) => {
                if (!payload || !payload.length) return null
                const p = payload[0].payload as ScatterPt
                return (
                  <div className="rounded-lg bg-navy-800 border border-white/10 px-3 py-2 text-xs">
                    <div className="font-bold text-white">{p.agent_name}</div>
                    <div className="text-slate-400">{p.team} · {p.tier}</div>
                    <div className="mt-1 text-slate-200">Save {pct(p.save_rate)} · {p.handle_time.toFixed(1)} min · NPS {p.nps.toFixed(0)}</div>
                  </div>
                )
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {tierOrder.filter((t) => byTier[t]).map((t) => (
              <Scatter key={t} name={t} data={byTier[t]} fill={TIER_COLORS[t]} fillOpacity={0.7} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      {/* Coaching table */}
      <Card title="Coaching Priority — Lowest 20 by Save Rate"
        right={<Pill color="#f5a623">Focus list</Pill>}>
        <div className="overflow-auto rounded-lg">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-navy-800 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <Th>Agent</Th><Th>Team</Th>
                <Th right>Handle Time</Th><Th right>NPS</Th>
                <Th right>Offer Conv.</Th><Th right>Save Rate</Th>
              </tr>
            </thead>
            <tbody>
              {data.coaching_table.map((r, i) => (
                <tr key={i} className="border-t border-white/5 hover:bg-white/5">
                  <Td className="font-medium text-slate-100">{r.agent_name}</Td>
                  <Td className="text-slate-400">{r.team}</Td>
                  <Td right className="tabular-nums">{r.avg_handle_time_min.toFixed(1)} min</Td>
                  <Td right className="tabular-nums">{r.nps.toFixed(0)}</Td>
                  <Td right className="tabular-nums">{pct(r.offer_conversion_rate)}</Td>
                  <Td right>
                    <span className="tabular-nums font-semibold" style={{ color: r.save_rate < 0.35 ? '#ef4b5c' : '#f5a623' }}>
                      {pct(r.save_rate)}
                    </span>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function StatLine({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold tabular-nums" style={{ color: color || '#e6eef7' }}>{value}</span>
    </div>
  )
}

const Th = ({ children, right }: { children: React.ReactNode; right?: boolean }) => (
  <th className={`px-3 py-2 font-semibold ${right ? 'text-right' : 'text-left'}`}>{children}</th>
)
const Td = ({ children, right, className = '' }: { children: React.ReactNode; right?: boolean; className?: string }) => (
  <td className={`px-3 py-2 ${right ? 'text-right' : 'text-left'} ${className}`}>{children}</td>
)
