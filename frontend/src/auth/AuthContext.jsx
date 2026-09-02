import React, { useMemo, useState } from 'react';
import { clearStoredSession } from './supabase';
import { AuthContext } from './useAuth';

const DEMO_SESSION_KEY = 'catstats_demo_session';

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(DEMO_SESSION_KEY));
      return stored?.session?.demo && stored?.profile?.role ? stored : null;
    } catch { localStorage.removeItem(DEMO_SESSION_KEY); }
    return null;
  });

  const value = useMemo(() => ({
    ...auth,
    loading: false,
    login: async (email, _password, expectedRole) => {
      const next = {
        session: { demo: true },
        profile: {
          role: expectedRole,
          email: email || (expectedRole === 'cat_admin' ? 'Caterpillar Admin' : 'Apex Customer'),
          full_name: expectedRole === 'cat_admin' ? 'Caterpillar Administrator' : 'Apex Operations',
          organization_name: expectedRole === 'customer' ? 'Apex Infra Logistics Corp' : 'Caterpillar',
        },
      };
      localStorage.setItem(DEMO_SESSION_KEY, JSON.stringify(next));
      setAuth(next);
      return next.profile;
    },
    logout: () => {
      clearStoredSession();
      localStorage.removeItem(DEMO_SESSION_KEY);
      setAuth(null);
    },
  }), [auth]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
