import { useAuth } from '../services/auth';
import { Navigate } from 'react-router-dom';

export default function LoginPage() {
  const { user, login } = useAuth();
  if (user) return <Navigate to="/" />;
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-cyan-50 to-blue-100">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-black mb-2">Market Insight</h1>
        <p className="text-gray-500 mb-6">Tier-based market analysis SaaS</p>
        <button onClick={login} className="bg-white border-2 border-gray-300 rounded-xl px-6 py-3 font-bold hover:bg-gray-50 w-full">
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
