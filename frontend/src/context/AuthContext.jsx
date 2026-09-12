import React, { createContext, useState, useEffect, useContext } from "react";
import { authAPI } from "../services/api";

const noopAsync = async () => {};
const noop = () => {};

const AuthContext = createContext({
  user: null,
  setUser: noop,
  isLoggedIn: false,
  setIsLoggedIn: noop,
  login: noopAsync,
  signup: noopAsync,
  logout: noop,
  loading: true,
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize auth state from storage
    const savedUser = localStorage.getItem("user");
    const access = localStorage.getItem("access_token");
    const refresh = localStorage.getItem("refresh_token");

    if (access && refresh) {
      setIsLoggedIn(true);
      if (savedUser) {
        setUser(JSON.parse(savedUser));
      } else {
        // Try to fetch current user when tokens exist
        authAPI
          .getCurrentUser()
          .then((res) => {
            const u = res.data;
            setUser(u);
            localStorage.setItem("user", JSON.stringify(u));
          })
          .catch(() => {
            // Tokens may be invalid; reset
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            setIsLoggedIn(false);
          })
          .finally(() => setLoading(false));
        return;
      }
    }
    setLoading(false);
  }, []);

  // Perform login against JWT endpoint and fetch user (username-based)
  const login = async (username, password) => {
    try {
      const tokenRes = await authAPI.login({ username, password });
      const { access, refresh } = tokenRes;
      if (!access || !refresh) {
        throw new Error("Invalid login response: tokens missing");
      }

      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);

      // Fetch current user
      const meRes = await authAPI.getCurrentUser();
      const userData = meRes.data;
      localStorage.setItem("user", JSON.stringify(userData));
      localStorage.setItem("is_logged_in", "true");

      setUser(userData);
      setIsLoggedIn(true);
      return userData;
    } catch (e) {
      // Ensure state is clean on failure
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      setIsLoggedIn(false);
      setUser(null);
      throw e;
    }
  };

  // Register then optionally auto-login
  const signup = async (username, email, password, referralCode = "") => {
    await authAPI.register({ username, email, password, ref: referralCode });
    return login(username, password);
  };

  const logout = () => {
    try {
      const refresh = localStorage.getItem("refresh_token");
      authAPI.logout(refresh).catch(() => {});
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      localStorage.removeItem("is_logged_in");
      setUser(null);
      setIsLoggedIn(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        isLoggedIn,
        setIsLoggedIn,
        login,
        signup,
        logout,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
