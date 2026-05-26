import { createContext, useContext, useEffect, useState } from 'react';
import { initializeApp } from 'firebase/app';
import {
  getAuth, GoogleAuthProvider, signInWithPopup, signOut, onIdTokenChanged,
} from 'firebase/auth';

// Firebase config injected via env (VITE_FIREBASE_*)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

const AuthCtx = createContext({ user: null, loading: true, token: null, login: () => {}, logout: () => {} });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    return onIdTokenChanged(auth, async (u) => {
      setUser(u);
      setToken(u ? await u.getIdToken() : null);
      setLoading(false);
    });
  }, []);

  const login = async () => {
    const result = await signInWithPopup(auth, new GoogleAuthProvider());
    setUser(result.user);
    setToken(await result.user.getIdToken());
  };
  const logout = () => signOut(auth);

  return <AuthCtx.Provider value={{ user, token, loading, login, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
