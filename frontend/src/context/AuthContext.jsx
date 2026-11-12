import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const { i18n } = useTranslation();

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const me = await api.login(email, password);
    setUser(me);
    if (me.language) i18n.changeLanguage(me.language);
    return me;
  };
  const register = async (email, password, name) => {
    const me = await api.register(email, password, i18n.language, name);
    setUser(me);
    return me;
  };
  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, ready, refresh, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
