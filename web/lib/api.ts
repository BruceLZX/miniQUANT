export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT';

interface BarsRow { ts: string; o: number; h: number; l: number; c: number; v: number }

const base = process.env.NEXT_PUBLIC_API_BASE_URL || '';

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<{ status: string; ts: string; service: string }>(`/api/health`),
  bars: (symbol: string, start?: string, end?: string, freq: '1d'|'1h'|'30m' = '1d') => {
    const params = new URLSearchParams({ symbol, freq });
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    return http<{ symbol: string; freq: string; rows: BarsRow[] }>(`/api/market/bars?${params.toString()}`);
  },
  last: (symbol: string) => http<{ symbol: string; price: number | null; ts: string | null }>(`/api/market/last?symbol=${encodeURIComponent(symbol)}`),
  positions: () => http<Array<{ symbol: string; qty: number; avg_price: number }>>(`/api/positions`),
  orders: (limit = 50) => http<Array<{ id:number; ts:string; symbol:string; side:OrderSide; qty:number; order_type:OrderType; price?:number; status:string; fill_price?:number }>>(`/api/orders?limit=${limit}`),
  account: () => http<{ equity:number; cash:number; positions_value:number; positions:Array<{symbol:string;qty:number;avg_price:number}>; ts:string }>(`/api/account`),
  createOrder: (body: { symbol: string; side: OrderSide; qty: number; type: OrderType; price?: number }) =>
    http<{ id:number; ts:string; symbol:string; side:OrderSide; qty:number; order_type:OrderType; price?:number; status:string; fill_price?:number }>(`/api/orders`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  modelStatus: () => http<{ status: string; last_run?: string; watch_symbol?: string; latency_sec?: number; last_signal?: string; last_error?: string; version?: string }>(`/api/model/status`),
  modelEvents: (limit = 50) => http<{ events: Array<{ ts:string; type:string; symbol?:string; signal?:string; score?:number; reason?:string; order_id?:number; risk_flags?:string[] }>}>(`/api/model/events?limit=${limit}`)
};
