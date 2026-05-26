import { useEffect, useState } from 'react';
import { Doughnut, Bar, Line } from 'react-chartjs-2';
import 'chart.js/auto';
import { useApi } from '../services/api';

export default function AnalyticsPage() {
  const api = useApi();
  const [data, setData] = useState(null);
  const [cat, setCat] = useState('');
  const [cagr, setCagr] = useState(null);
  const [yoy, setYoy] = useState(null);
  const [series, setSeries] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => { api.analytics(30).then(setData).catch(e => setError(e.message)); }, []);

  const loadCat = async () => {
    if (!cat.trim()) return;
    try {
      const [c, y, t] = await Promise.all([api.cagr(cat), api.yoy(cat), api.timeseries(cat)]);
      setCagr(c); setYoy(y); setSeries(t);
    } catch (e) { setError(e.message); }
  };

  if (error) return <div className="p-4 text-red-500">에러: {error}</div>;
  if (!data) return <div className="p-4">Loading...</div>;

  const tier = data.tier_distribution;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Analytics</h2>
          <div className="flex gap-2">
            <input value={cat} onChange={e => setCat(e.target.value)}
                   placeholder="카테고리 (시계열)" className="px-3 py-2 border rounded text-sm" />
            <button onClick={loadCat} className="px-4 py-2 bg-emerald-600 text-white rounded font-bold text-sm">로드</button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <KPI label="CAGR (12m)" value={cagr ? (cagr.cagr_pct != null ? cagr.cagr_pct + '%' : (cagr.insufficient || '—')) : '—'} />
          <KPI label="YoY" value={yoy ? (yoy.yoy_pct != null ? yoy.yoy_pct + '%' : (yoy.insufficient || '—')) : '—'} />
          <KPI label="시계열 자료 포인트" value={series ? series.count : '—'} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Card title="Tier 적중률">
            <Doughnut data={{
              labels: ['Tier 1 (매핑)', 'Tier 0 (단순)'],
              datasets: [{ data: [tier.tier1, tier.tier0], backgroundColor: ['#10b981', '#f59e0b'] }],
            }} />
          </Card>
          <Card title="시간대별 검색 분포">
            <Bar data={{
              labels: data.hourly.map(h => h.hour + '시'),
              datasets: [{ label: '검색 건수', data: data.hourly.map(h => h.count), backgroundColor: '#3b82f6' }],
            }} />
          </Card>
          <Card title="mapping_coverage 추이 (일별)">
            <Line data={{
              labels: data.coverage_trend.map(d => d.date),
              datasets: [{ label: 'avg %', data: data.coverage_trend.map(d => d.avg),
                           borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.2)', fill: true }],
            }} />
          </Card>
          <Card title="카테고리별 production_kg">
            <Bar data={{
              labels: data.production_by_category.map(x => x.category),
              datasets: [{ label: 'kg', data: data.production_by_category.map(x => x.kg), backgroundColor: '#06b6d4' }],
            }} />
          </Card>
          {series && series.success && series.series.length > 0 && (
            <Card title={`${cat} 시계열`}>
              <Line data={{
                labels: series.series.map(s => s.month),
                datasets: [{ label: 'kg', data: series.series.map(s => s.production_kg),
                             borderColor: '#0ea5e9', backgroundColor: 'rgba(14,165,233,0.2)', fill: true }],
              }} />
            </Card>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-3">⚠️ 절대 매출 X, 상대 서열만</p>
      </div>
    </div>
  );
}

const KPI = ({ label, value }) => (
  <div className="bg-gray-50 rounded-xl p-4 text-center">
    <div className="text-xs text-gray-500">{label}</div>
    <div className="text-xl font-bold mt-1">{value}</div>
  </div>
);

const Card = ({ title, children }) => (
  <div className="bg-gray-50 rounded-xl p-4">
    <h3 className="font-bold text-sm mb-2">{title}</h3>
    <div>{children}</div>
  </div>
);
