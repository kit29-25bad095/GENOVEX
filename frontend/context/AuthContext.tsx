"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User, ApiClient } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  guestSessionToken: string;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name: string) => Promise<void>;
  logout: () => void;
  setGuestSessionToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [guestSessionToken, setGuestSessionTokenState] = useState<string>("");

  useEffect(() => {
    // Initialize guest session token for anonymous assessments
    let storedGuest = localStorage.getItem("genovex_guest_token");
    if (!storedGuest) {
      storedGuest = "gst_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      localStorage.setItem("genovex_guest_token", storedGuest);
    }
    setGuestSessionTokenState(storedGuest);

    // Initialize authenticated user session
    const storedToken = localStorage.getItem("genovex_token");
    if (storedToken) {
      setToken(storedToken);
      ApiClient.getCurrentUser()
        .then((userData) => setUser(userData))
        .catch(() => {
          localStorage.removeItem("genovex_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, pass: string) => {
    const authData = await ApiClient.login(email, pass);
    localStorage.setItem("genovex_token", authData.access_token);
    setToken(authData.access_token);
    const userData = await ApiClient.getCurrentUser();
    setUser(userData);
  };

  const register = async (email: string, pass: string, name: string) => {
    await ApiClient.register({ email, password: pass, full_name: name });
    await login(email, pass);
  };

  const logout = () => {
    localStorage.removeItem("genovex_token");
    setToken(null);
    setUser(null);
  };

  const setGuestSessionToken = (newToken: string) => {
    localStorage.setItem("genovex_guest_token", newToken);
    setGuestSessionTokenState(newToken);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        guestSessionToken,
        login,
        register,
        logout,
        setGuestSessionToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
