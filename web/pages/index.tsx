import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';

type BarsRow = { ts: string; o: number; h: number; l: number; c: number; v: number };

export default function Home() {
  const [health, setHealth] = useState<string>('checking...');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [editSymbol, setEditSymbol] = useState<string>('');
  const [editing, setEditing] = useState<boolean>(true); // 初始为空，处于选择状态
  const [bars, setBars] = useState<BarsRow[]>([]);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [account, setAccount] = useState<{ equity:number; cash:number; positions_value:number } | null>(null);
  const [message, setMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [modelStatus, setModelStatus] = useState<{ status:string; last_run?:string; watch_symbol?:string; latency_sec?:number; last_signal?:string; last_error?:string; version?:string } | null>(null);
  const [modelEvents, setModelEvents] = useState<Array<{ ts:string; type:string; symbol?:string; signal?:string; score?:number; reason?:string }>>([]);

  useEffect(() => {
    api.health().then(h => setHealth(`${h.status} @ ${h.ts}`)).catch(() => setHealth('backend unreachable'));
  }, []);

  const reloadAll = async (sym: string) => {
    setLoading(true);
    try {
      const [barsRes, lastRes, accRes, ms, me] = await Promise.all([
        api.bars(sym),
        api.last(sym),
        api.account(),
        api.modelStatus(),
        api.modelEvents(20)
      ]);
      setBars(barsRes.rows);
      setLastPrice(lastRes.price);
      setAccount({ equity: accRes.equity, cash: accRes.cash, positions_value: accRes.positions_value });
      setModelStatus(ms);
      setModelEvents(me.events);
      setMessage('');
    } catch (e: any) {
      setMessage(e?.message || 'load failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedSymbol) reloadAll(selectedSymbol);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol]);

  // Poll model status/events every 8s
  useEffect(() => {
    const t = setInterval(async () => {
      try {
        const [ms, me] = await Promise.all([api.modelStatus(), api.modelEvents(20)]);
        setModelStatus(ms);
        setModelEvents(me.events);
      } catch {}
    }, 8000);
    return () => clearInterval(t);
  }, []);

  const lastClose = useMemo(() => (bars.length ? bars[bars.length - 1].c : null), [bars]);

  return (
    <div style={{ fontFamily: 'system-ui, Arial, sans-serif', padding: 16 }}>
      <h1>MyQuant Dashboard (Node + FastAPI)</h1>
      <p>Backend health: <strong>{health}</strong></p>

      <section style={{ border: '1px solid #ddd', padding: 12, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Stock Selection</h3>
        {editing ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              placeholder="Enter symbol (e.g. AAPL)"
              value={editSymbol}
              onChange={(e) => setEditSymbol(e.target.value.toUpperCase())}
              style={{ padding: 6 }}
            />
            <button
              onClick={() => {
                const sym = editSymbol.trim();
                if (!sym) return;
                setSelectedSymbol(sym);
                setEditing(false);
              }}
              disabled={!editSymbol.trim()}
            >Select</button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div>Selected symbol: <strong>{selectedSymbol}</strong></div>
            <button onClick={() => { setEditSymbol(selectedSymbol); setEditing(true); }}>Change</button>
            <button onClick={() => reloadAll(selectedSymbol)} disabled={loading}>Refresh</button>
            <span style={{ marginLeft: 12 }}>
              Last: <strong>{lastPrice ?? '-'}</strong> &nbsp; Latest close: <strong>{lastClose ?? '-'}</strong>
            </span>
          </div>
        )}
      </section>

      <section style={{ border: '1px solid #ddd', padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Price Monitor</h3>
        {!selectedSymbol ? (
          <p>Please select a symbol to start monitoring.</p>
        ) : (
          <table width="100%" cellPadding={4} style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th align="left">ts</th>
                <th>O</th>
                <th>H</th>
                <th>L</th>
                <th>C</th>
                <th>V</th>
              </tr>
            </thead>
            <tbody>
              {bars.slice(-20).map((r, i) => (
                <tr key={i}>
                  <td>{r.ts}</td>
                  <td align="right">{r.o.toFixed(2)}</td>
                  <td align="right">{r.h.toFixed(2)}</td>
                  <td align="right">{r.l.toFixed(2)}</td>
                  <td align="right">{r.c.toFixed(2)}</td>
                  <td align="right">{r.v.toFixed(0)}</td>
                </tr>
              ))}
              {!bars.length && (
                <tr><td colSpan={6} align="center">No data</td></tr>
              )}
            </tbody>
          </table>
        )}
        {message && <p style={{ color: 'crimson' }}>{message}</p>}
      </section>

      <section style={{ border: '1px solid #ddd', padding: 12, marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Model Monitor</h3>
        {!modelStatus ? (
          <p>Loading model status...</p>
        ) : (
          <div style={{ marginBottom: 8 }}>
            <div>Status: <strong>{modelStatus.status}</strong> {modelStatus.last_error ? <span style={{ color:'crimson' }}>(error: {modelStatus.last_error})</span> : null}</div>
            <div>Last run: {modelStatus.last_run ?? '-'}</div>
            <div>Watch symbol: {modelStatus.watch_symbol ?? '-'}</div>
            <div>Last signal: {modelStatus.last_signal ?? '-'}</div>
            <div>Latency: {modelStatus.latency_sec != null ? `${modelStatus.latency_sec.toFixed(1)}s` : '-'}</div>
            <div>Version: {modelStatus.version ?? '-'}</div>
          </div>
        )}
        <div>
          <strong>Recent events</strong>
          <table width="100%" cellPadding={4} style={{ borderCollapse: 'collapse', marginTop: 6 }}>
            <thead>
              <tr>
                <th align="left">ts</th>
                <th align="left">type</th>
                <th align="left">symbol</th>
                <th align="left">signal</th>
                <th align="right">score</th>
                <th align="left">reason</th>
              </tr>
            </thead>
            <tbody>
              {modelEvents.map((e, i) => (
                <tr key={i}>
                  <td>{e.ts}</td>
                  <td>{e.type}</td>
                  <td>{e.symbol ?? '-'}</td>
                  <td>{e.signal ?? '-'}</td>
                  <td align="right">{e.score != null ? e.score.toFixed(2) : '-'}</td>
                  <td>{e.reason ?? '-'}</td>
                </tr>
              ))}
              {!modelEvents.length && <tr><td colSpan={6} align="center">No events</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <footer style={{ marginTop: 24, color: '#666' }}>
        <small>Tip: Use the Change button to pick another symbol. API proxy via Next rewrites. Run with <code>npm run dev:all</code>.</small>
      </footer>
    </div>
  );
}
