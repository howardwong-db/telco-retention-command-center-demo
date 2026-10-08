export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { 'Content-Type': 'application/json' } })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export async function patchJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export async function del(url: string): Promise<void> {
  await fetch(url, { method: 'DELETE' })
}

export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`
export const money = (v: number) =>
  `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
export const money2 = (v: number) =>
  `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export const TIER_COLORS: Record<string, string> = {
  'Top Performer': '#2dce89',
  'On Target': '#0099d8',
  'Needs Coaching': '#f5a623',
  'At Risk': '#ef4b5c',
}

export const COMPETITOR_COLORS = [
  '#0099d8',
  '#34c3f0',
  '#22c1b3',
  '#f5a623',
  '#a78bfa',
  '#ef4b5c',
  '#7fd8f5',
]
