import { useState, useEffect } from 'react';
import { useApi } from '../services/api';

export default function SearchPage() {
  const api = useApi();
  const [kw, setKw] = useState('');
  const [topN, setTopN] = useState(10);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);

  useEffect(() => { api.history(7).then(r => setHistory(r.history || [])).catch(() => {}); }, [result]);

  const run = async () => {
    if (!kw.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try { setResult(await api.search(kw.trim(), topN)); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-2xl font-bold mb-4">시장 분석</h2>
        {history.length > 0 && (
          <div className="text-xs text-gray-600 mb-2">
            최근 검색:{' '}
            {history.slice(0, 5).map((h, i) => (
              <span key={i} onClick={() => setKw(h.keyword)}
                    className="inline-block px-2 py-0.5 mr-1 bg-gray-100 rounded cursor-pointer hover:bg-cyan-100">
                {h.keyword}
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input value={kw} onChange={e => setKw(e.target.value)}
                 onKeyDown={e => e.key === 'Enter' && run()}
                 placeholder="키워드 (예: 유산균, 콜라겐)"
                 className="flex-1 px-4 py-2 border rounded-xl" />
          <select value={topN} onChange={e => setTopN(+e.target.value)} className="px-3 py-2 border rounded-xl">
            {[5, 10, 20, 50].map(n => <option key={n} value={n}>상위 {n}</option>)}
          </select>
          <button onClick={run} disabled={loading}
                  className="px-5 py-2 rounded-xl font-bold text-white bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50">
            {loading ? '분석 중...' : '분석'}
          </button>
        </div>
        {error && <div className="mt-3 text-red-500 text-sm">에러: {error}</div>}
      </div>

      {result?.success && (
        <div className="bg-white rounded-2xl p-6 shadow">
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className={`px-2 py-1 rounded font-bold ${
              result.tier >= 1 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {result.tier >= 1 ? `Tier 1 · ${result.category}` : 'Tier 0 · 단순 매칭'} ·
              매핑 커버리지 {result.mapping_coverage}%
            </span>
            <span className="text-gray-500">{result.totalRows} rows · {result.elapsedMs}ms</span>
          </div>

          {result.tier === 1 ? (
            <>
              <h3 className="font-bold mb-2">⭐ 매핑 브랜드 ({result.mapped_count})</h3>
              <table className="w-full text-sm mb-4">
                <thead><tr className="bg-emerald-50 text-left">
                  <th className="p-2">브랜드</th><th className="p-2">type</th>
                  <th className="p-2 text-right">production_kg</th>
                  <th className="p-2 text-right">share</th><th className="p-2">신뢰</th>
                </tr></thead>
                <tbody>
                  {result.mapped_brands.map((b, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-2 font-bold">{b.display || b.brand}</td>
                      <td className="p-2 text-xs">{b.type}</td>
                      <td className="p-2 text-right">{Math.round(b.kg).toLocaleString()}</td>
                      <td className="p-2 text-right font-bold">{b.share}%</td>
                      <td className="p-2">
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          b.confidence === 'H' ? 'bg-emerald-100 text-emerald-700'
                          : b.confidence === 'M' ? 'bg-amber-100 text-amber-700' : 'bg-gray-200'
                        }`}>{b.confidence}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.unmapped?.length > 0 && (
                <details className="text-sm">
                  <summary className="cursor-pointer font-bold">📋 기타 ({result.unmapped_count})</summary>
                  <table className="w-full mt-2">
                    <tbody>
                      {result.unmapped.map((c, i) => (
                        <tr key={i} className="border-b">
                          <td className="p-2">{c.company}</td>
                          <td className="p-2 text-right">{Math.round(c.kg).toLocaleString()}</td>
                          <td className="p-2 text-right">{c.share}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              )}
            </>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-100"><th className="p-2">순위</th><th className="p-2">영업자</th><th className="p-2 text-right">kg</th></tr></thead>
              <tbody>
                {(result.topCompanies || []).map((c, i) => (
                  <tr key={i} className="border-b">
                    <td className="p-2 font-bold">{i + 1}</td>
                    <td className="p-2">{c.company}</td>
                    <td className="p-2 text-right">{Math.round(c.kg).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="text-xs text-gray-500 mt-3">⚠️ 절대 매출 X, 상대 서열만</p>
        </div>
      )}
    </div>
  );
}
