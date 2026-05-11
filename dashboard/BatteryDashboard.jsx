/**
 * BatteryDashboard.jsx — Production version
 *
 * Fetches real price data from a JSON endpoint (data/current.json) populated
 * by the Python scraper running on GitHub Actions cron.
 *
 * Configuration:
 *   <BatteryDashboard dataUrl="https://raw.githubusercontent.com/USER/REPO/main/data/current.json" />
 *
 * If dataUrl is omitted, defaults to "./data/current.json" (relative to host).
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  Area,
  AreaChart,
} from 'recharts';
import { RefreshCw, ExternalLink, AlertCircle } from 'lucide-react';

/* ────────── Pretendard font ────────── */
const FontStyle = () => (
  <style>{`
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    .font-pretendard { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, 'Apple SD Gothic Neo', sans-serif; }
    .font-tabular { font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums; }
  `}</style>
);

/* ────────── Formatting helpers ────────── */
const fmt = (n, d = 0) =>
  n == null || isNaN(n)
    ? '—'
    : n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

const fmtPct = (p) => (p == null ? '—' : `${p > 0 ? '+' : ''}${p.toFixed(2)}%`);

const colorForReturn = (p) => {
  if (p == null) return 'text-slate-500 bg-slate-700/30 border-slate-600/40';
  if (p > 0) return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30';
  if (p < 0) return 'text-rose-300 bg-rose-500/10 border-rose-500/30';
  return 'text-slate-400 bg-slate-700/30 border-slate-600/40';
};

const fmtMonth = (s) => {
  if (!s) return '';
  const d = new Date(s);
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${m[d.getMonth()]} ${d.getFullYear()}`;
};

/* ────────── Performance pill ────────── */
const PerformancePill = ({ label, value }) => (
  <div
    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10.5px] font-semibold tracking-tight border font-tabular ${
      value != null ? colorForReturn(value) : 'text-slate-500 bg-slate-700/20 border-slate-600/30'
    }`}
  >
    <span className="opacity-90">{label}</span>
    <span>{value != null ? fmtPct(value) : '—'}</span>
  </div>
);

/* ────────── Tooltip ────────── */
const ChartTooltip = ({ active, payload, decimals, type }) => {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  return (
    <div className="bg-slate-900/95 border border-slate-700/60 rounded-md px-3 py-2 text-[11px] shadow-xl backdrop-blur font-tabular">
      <div className="text-slate-400 mb-1">{p.date}</div>
      {type === 'range' ? (
        <div className="space-y-0.5">
          <div className="flex justify-between gap-4">
            <span className="text-emerald-400">High</span>
            <span className="text-slate-100">{fmt(p.high, decimals)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-cyan-400">Avg</span>
            <span className="text-slate-100">{fmt(p.avg, decimals)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-amber-400">Low</span>
            <span className="text-slate-100">{fmt(p.low, decimals)}</span>
          </div>
        </div>
      ) : (
        <div className="text-slate-100">{fmt(p.value, decimals)}</div>
      )}
    </div>
  );
};

/* ────────── Card ────────── */
const PriceCard = ({ id, commodity, asOfDate }) => {
  const series = commodity.series || [];
  const latest = commodity.latest;
  const returns = commodity.returns || {};

  const ticks = useMemo(() => {
    if (series.length < 30) return series.length > 0 ? [series[Math.floor(series.length / 2)].date] : [];
    const seen = new Set();
    const out = [];
    for (const p of series) {
      const ym = p.date.slice(0, 7);
      if (!seen.has(ym)) {
        seen.add(ym);
        out.push(p.date);
      }
    }
    return out;
  }, [series]);

  const yDomain = useMemo(() => {
    if (!series.length) return [0, 1];
    const vals =
      commodity.type === 'range'
        ? series.flatMap((p) => [p.high, p.low])
        : series.map((p) => p.value);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = (max - min) * 0.08 || max * 0.05;
    return [Math.max(0, min - pad), max + pad];
  }, [series, commodity.type]);

  return (
    <div className="relative bg-[#0f1623] border border-slate-700/40 rounded-xl p-5 flex flex-col gap-3 hover:border-slate-600/60 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[15px] font-bold text-slate-100 tracking-tight">{commodity.title}</h3>
          <div className="text-[11.5px] text-slate-500 font-medium mt-0.5">{commodity.unit}</div>
        </div>
        <div className="text-[10.5px] text-slate-500 font-tabular pt-1">{asOfDate}</div>
      </div>

      <div className="flex items-baseline gap-3 flex-wrap">
        <div className="flex items-baseline gap-1.5">
          <span className="text-[11px] text-slate-500">최근값</span>
          <span className="text-[18px] font-bold text-slate-50 font-tabular">
            {fmt(latest, commodity.decimals)}
          </span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-[11px] text-slate-500">데이터</span>
          <span className="text-[13px] font-semibold text-slate-200 font-tabular">{commodity.points}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {['1D', '1W', '1M', '3M', '6M'].map((h) => (
          <PerformancePill key={h} label={h} value={returns[h]} />
        ))}
      </div>

      <div className="h-[170px] -mx-1 mt-1">
        {series.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-[11px]">
            데이터를 받아오지 못했습니다
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {commodity.type === 'range' ? (
              <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="2 4" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
                  tickLine={false}
                  ticks={ticks}
                  tickFormatter={fmtMonth}
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={55}
                  tickFormatter={(v) => fmt(v, 0)}
                />
                <Tooltip content={<ChartTooltip decimals={commodity.decimals} type="range" />} />
                <Line type="monotone" dataKey="high" stroke="#10b981" strokeWidth={1.6} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="avg" stroke="#22d3ee" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="low" stroke="#f59e0b" strokeWidth={1.6} dot={false} isAnimationActive={false} />
              </LineChart>
            ) : (
              <AreaChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="2 4" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
                  tickLine={false}
                  ticks={ticks}
                  tickFormatter={fmtMonth}
                  angle={-30}
                  dy={6}
                  height={36}
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={55}
                  tickFormatter={(v) => (commodity.decimals > 0 ? v.toFixed(commodity.decimals) : fmt(v, 0))}
                />
                <Tooltip content={<ChartTooltip decimals={commodity.decimals} type="single" />} />
                <Area type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={1.6} fill={`url(#grad-${id})`} isAnimationActive={false} dot={false} />
              </AreaChart>
            )}
          </ResponsiveContainer>
        )}
      </div>

      {commodity.type === 'range' && series.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] bg-cyan-400 rounded" />
            <span>Battery Grade LiPF6 — Avg</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] bg-emerald-500 rounded" />
            <span>Battery Grade LiPF6 — High</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] bg-amber-500 rounded" />
            <span>Battery Grade LiPF6 — Low</span>
          </div>
        </div>
      )}

      <div className="text-[10.5px] text-slate-500 mt-auto pt-1">
        출처:{' '}
        <a href={commodity.source_url} target="_blank" rel="noreferrer"
           className="text-cyan-400/80 hover:text-cyan-300 inline-flex items-center gap-0.5">
          {commodity.source}
          <ExternalLink className="w-2.5 h-2.5" />
        </a>
      </div>
    </div>
  );
};

/* ────────── Main dashboard ────────── */
export default function BatteryDashboard({ dataUrl = './data/current.json' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = dataUrl.includes('?') ? `${dataUrl}&_=${Date.now()}` : `${dataUrl}?_=${Date.now()}`;
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastFetch(new Date());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [dataUrl]);

  useEffect(() => {
    load();
  }, [load]);

  const commodities = data?.commodities || {};
  const order = ['lithium', 'nickel', 'copper', 'aluminum', 'lipf6_usd', 'lipf6_cny'];
  const sortedIds = order.filter((id) => commodities[id]);

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 font-pretendard p-4 sm:p-6 lg:p-8">
      <FontStyle />

      <div className="max-w-[1600px] mx-auto mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-1 h-8 bg-cyan-400 rounded-full mt-1 shadow-[0_0_12px_rgba(34,211,238,0.6)]" />
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-slate-50">
                  배터리 <span className="text-slate-300 font-semibold">Battery</span>
                </h1>
                <span className="inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 bg-slate-700/60 border border-slate-600/50 rounded-full text-[11px] font-bold text-slate-300 font-tabular">
                  {sortedIds.length}
                </span>
              </div>
              <p className="text-[12.5px] text-slate-500 mt-1 font-medium">
                탄산리튬, LiPF6, 구리, 알루미늄, 니켈
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-[11px] text-slate-500 font-tabular hidden sm:block">
              {data?.as_of && (
                <>
                  기준일: <span className="text-slate-300">{data.as_of}</span>
                </>
              )}
              {lastFetch && (
                <span className="ml-2 text-slate-600">
                  · {lastFetch.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })} fetched
                </span>
              )}
            </div>
            <button
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed border border-cyan-500/30 hover:border-cyan-400/50 text-cyan-300 hover:text-cyan-200 rounded-lg text-[12px] font-semibold transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              {loading ? '로딩…' : '새로고침'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 px-3 py-2 bg-rose-500/10 border border-rose-500/30 rounded-md text-[11.5px] text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <div>
              데이터 로드 실패 ({error}). <code className="text-rose-200 bg-rose-500/10 px-1 rounded">{dataUrl}</code> 경로를 확인해주세요.
            </div>
          </div>
        )}

        {data?.errors && data.errors.length > 0 && (
          <div className="mt-3 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-md text-[11.5px] text-amber-300">
            ⚠ 일부 항목 업데이트 실패: {data.errors.join(', ')}
          </div>
        )}
      </div>

      {loading && !data ? (
        <div className="max-w-[1600px] mx-auto grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-[#0f1623] border border-slate-700/40 rounded-xl p-5 h-[340px] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="max-w-[1600px] mx-auto grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedIds.map((id) => (
            <PriceCard key={id} id={id} commodity={commodities[id]} asOfDate={data?.as_of || '—'} />
          ))}
        </div>
      )}

      <div className="max-w-[1600px] mx-auto mt-6 text-[10.5px] text-slate-600 leading-relaxed">
        Sina Finance(LC0/NI0) · Yahoo Finance(HG=F/ALI=F) · SMM(LiPF6).
        업데이트 주기: 평일 KST 18:00 (GitHub Actions cron).
        {data?.updated_at && (
          <> · 마지막 스크래핑: <span className="text-slate-500 font-tabular">{new Date(data.updated_at).toLocaleString('ko-KR')}</span></>
        )}
      </div>
    </div>
  );
}
