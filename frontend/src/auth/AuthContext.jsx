import React, { useEffect, useMemo, useState } from 'react';
import { clearStoredSession, getProfile, loadStoredSession, refreshSession, signIn } from './supabase';
import { AuthContext } from './useAuth';

async function hydrate(stored) {
  if (!stored?.access_token || !stored?.user?.id) return null;
  const expiresSoon = stored.expires_at && stored.expires_at * 1000 < Date.now() + 60_000;
  const session = expiresSoon ? await refreshSession(stored.refresh_token) : stored;
  const profile = await getProfile(session.access_token, session.user.id);
  return { session, profile };
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    hydrate(loadStoredSession())
      .then((value) => { if (active) setAuth(value); })
      .catch(() => clearStoredSession())
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const value = useMemo(() => ({
    ...auth,
    loading,
    login: async (email, password, expectedRole) => {
      const session = await signIn(email, password);
      try {
        const profile = await getProfile(session.access_token, session.user.id);
        if (profile.role !== expectedRole) {
          throw new Error(`This account belongs to the ${profile.role === 'cat_admin' ? 'Caterpillar Admin' : 'Customer'} portal.`);
        }
        setAuth({ session, profile });
        return profile;
      } catch (error) {
        clearStoredSession();
        throw error;
      }
    },
    logout: () => {
      clearStoredSession();
      setAuth(null);
    },
  }), [auth, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
