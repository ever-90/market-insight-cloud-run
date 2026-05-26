import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../services/auth';

export default function Layout() {
  const loc = useLocation();
  const { user, logout } = useAuth();
  const link = (to, label) => (
    <Link to={to}
      className={`px-4 py-2 rounded font-bold text-sm ${
        loc.pathname === to ? 'bg-cyan-600 text-white' : 'text-gray-600 hover:bg-gray-100'
      }`}>{label}</Link>
  );
  return (
    <div className="min-h-screen">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-black">Market Insight</h1>
          <nav className="flex items-center gap-2">
            {link('/', '시장 분석')}
            {link('/analytics', 'Analytics')}
            <span className="text-sm text-gray-500 ml-4">{user?.email}</span>
            <button onClick={logout} className="text-xs text-gray-500 underline ml-2">Logout</button>
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6"><Outlet /></main>
    </div>
  );
}
