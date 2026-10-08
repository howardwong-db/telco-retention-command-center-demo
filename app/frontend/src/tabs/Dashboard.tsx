import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { TrendingDown, Users, ShieldAlert, Target, TrendingUp } from 'lucide-react'
import { getJSON, pct, money, COMPETITOR_COLORS } from '../api'
import { Card, Kpi, Loading, ErrorBox, Pill } from '../components/ui'

interface DashData {
  kpis: { churn_rate_pct: number; competitor_mention_rate: number; critical_count: number; save_rate: number }
  trend: { call_date: string; churn_rate_pct: number; competitor_mention_rate: number }[]
  competitor_pie: { name: string; value: number }[]
  critical_customers: {
    customer_id: string; market: string; plan_type: string
    monthly_spend: number; churn_score: number; recommended_offer_id: string
  }[]
  roi: { multiple: number; protected_revenue_m: number; program_cost_m: number; churn_reduction_pct: number }
}

const fmtDate = (s: string) => {
  const d = new Date(s + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export default function Dashboard() {
  const [data, setData] = useState<DashData | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    getJSON<DashData>('/api/dashboard').then(setData).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loading label="Loading executive metrics…" />

  const k = data.kpis
  return (
    <div className="space-y-6">
      <Header
        title="Executive Dashboard"
        subtitle="Real-time churn, competitor pressure, and retention program ROI"
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Current Churn Rate" value={`${k.churn_rate_pct.toFixed(2)}%`}
          tone="red" icon={<TrendingDown size={18} />} sub="Daily annualized rate" />
        <Kpi label="Competitor Mention Rate" value={pct(k.competitor_mention_rate)}
          tone="amber" icon={<Users size={18} />} sub="Share of calls citing a competitor" />
        <Kpi label="Critical-Tier Customers" value={k.critical_count.toLocaleString()}
          tone="red" icon={<ShieldAlert size={18} />} sub="Highest churn-risk accounts" />
        <Kpi label="Save Rate" value={pct(k.save_rate)}
          tone="green" icon={<Target size={18} />} sub="Retention agent effectiveness" />
      </div>

      {/* Trend + ROI */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card title="Churn Rate vs. Competitor Mention Rate" className="xl:col-span-2">
          <div className="text-xs text-slate-400 -mt-2 mb-3">
            Competitor pressure spiked ~3 weeks ago, dragging churn upward
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.trend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="call_date" tickFormatter={fmtDate} stroke="#7089a6" fontSize={11}
                minTickGap={28} />
              <YAxis yAxisId="left" stroke="#ef4b5c" fontSize={11}
                domain={[1.5, 'auto']} tickFormatter={(v) => `${v}%`} />
              <YAxis yAxisId="right" orientation="right" stroke="#f5a623" fontSize={11}
                tickFormatter={(v) => `${v}%`} />
              <Tooltip
                contentStyle={{ background: '#0d2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: '#e6eef7' }}
                formatter={(v: number, n: string) => [`${Number(v).toFixed(2)}%`, n]}
                labelFormatter={(l) => `Date: ${l}`}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="left" type="monotone" dataKey="churn_rate_pct" name="Churn Rate"
                stroke="#ef4b5c" strokeWidth={2.5} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="competitor_mention_rate" name="Competitor Mention Rate"
                stroke="#f5a623" strokeWidth={2.5} dot={false} strokeDasharray="5 3" />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Retention Program ROI">
          <div className="flex flex-col items-center justify-center py-2">
            <div className="relative">
              <div className="text-6xl font-extrabold bg-gradient-to-br from-spectrum-sky to-accent-green bg-clip-text text-transparent">
                {data.roi.multiple.toFixed(1)}x
              </div>
              <div className="text-center text-xs uppercase tracking-widest text-slate-400 mt-1">Return on Investment</div>
            </div>
            <div className="grid grid-cols-1 gap-3 w-full mt-6">
              <RoiRow label="Revenue Protected" value={`$${data.roi.protected_revenue_m}M`} tone="text-accent-green" icon={<TrendingUp size={16} />} />
              <RoiRow label="Program Cost" value={`$${data.roi.program_cost_m}M`} tone="text-slate-200" icon={<Target size={16} />} />
              <RoiRow label="Churn Reduction" value={`${data.roi.churn_reduction_pct}%`} tone="text-spectrum-sky" icon={<TrendingDown size={16} />} />
            </div>
          </div>
        </Card>
      </div>

      {/* Pie + Critical table */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card title="Competitor Mentions">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={data.competitor_pie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                innerRadius={55} outerRadius={95} paddingAngle={2} stroke="none">
                {data.competitor_pie.map((_, i) => (
                  <Cell key={i} fill={COMPETITOR_COLORS[i % COMPETITOR_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0d2138', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }}
                formatter={(v: number, n: string) => [`${v.toLocaleString()} mentions`, n]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title={`Critical-Tier Customers`} className="xl:col-span-2"
          right={<Pill color="#ef4b5c">Top {data.critical_customers.length} by churn score</Pill>}>
          <div className="overflow-auto max-h-[300px] rounded-lg">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-navy-800 text-slate-400 text-xs uppercase tracking-wider">
                <tr>
                  <Th>Customer</Th><Th>Market</Th><Th>Plan</Th>
                  <Th right>Monthly</Th><Th right>Churn Score</Th><Th>Offer</Th>
                </tr>
              </thead>
              <tbody>
                {data.critical_customers.map((c) => (
                  <tr key={c.customer_id} className="border-t border-white/5 hover:bg-white/5">
                    <Td className="font-mono text-xs text-slate-300">{c.customer_id}</Td>
                    <Td>{c.market}</Td>
                    <Td>{c.plan_type}</Td>
                    <Td right className="tabular-nums">{money(c.monthly_spend)}</Td>
                    <Td right>
                      <span className="tabular-nums font-semibold text-accent-red">
                        {(c.churn_score * 100).toFixed(0)}%
                      </span>
                    </Td>
                    <Td><Pill color="#0099d8">{c.recommended_offer_id}</Pill></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  )
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h1 className="text-2xl font-extrabold text-white tracking-tight">{title}</h1>
      <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>
    </div>
  )
}

function RoiRow({ label, value, tone, icon }: { label: string; value: string; tone: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-navy-900/60 px-4 py-2.5 border border-white/5">
      <span className="flex items-center gap-2 text-sm text-slate-300"><span className={tone}>{icon}</span>{label}</span>
      <span className={`font-bold tabular-nums ${tone}`}>{value}</span>
    </div>
  )
}

const Th = ({ children, right }: { children: React.ReactNode; right?: boolean }) => (
  <th className={`px-3 py-2 font-semibold ${right ? 'text-right' : 'text-left'}`}>{children}</th>
)
const Td = ({ children, right, className = '' }: { children: React.ReactNode; right?: boolean; className?: string }) => (
  <td className={`px-3 py-2 ${right ? 'text-right' : 'text-left'} ${className}`}>{children}</td>
)

export { Header }
