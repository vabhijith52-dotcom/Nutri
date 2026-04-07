// src/hooks/useAuth.tsx
import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/integrations/supabase/client";
import type { User, Session } from "@supabase/supabase-js";
import { authAPI } from "@/lib/api";

export function useAuth() {
  const [user,    setUser]    = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session on mount
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setUser(data.session?.user ?? null);
      if (data.session?.access_token) {
        localStorage.setItem("ns_token", data.session.access_token);
      }
      setLoading(false);
    });

    // Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, sess) => {
        setSession(sess);
        setUser(sess?.user ?? null);
        if (sess?.access_token) {
          localStorage.setItem("ns_token", sess.access_token);
        } else {
          localStorage.removeItem("ns_token");
          localStorage.removeItem("ns_profile");
        }
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signUp = useCallback(async (email: string, password: string, full_name = "") => {
    try {
      const res = await authAPI.signup(email, password, full_name);
      const token = res.data.access_token;
      if (token) {
        localStorage.setItem("ns_token", token);
        await supabase.auth.setSession({
          access_token:  token,
          refresh_token: res.data.refresh_token || "",
        });
      }
      return { error: null, data: res.data };
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Signup failed";
      return { error: new Error(msg), data: null };
    }
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const res = await authAPI.login(email, password);
      const { access_token, refresh_token, profile } = res.data;
      localStorage.setItem("ns_token", access_token);
      if (profile) localStorage.setItem("ns_profile", JSON.stringify(profile));
      await supabase.auth.setSession({ access_token, refresh_token: refresh_token || "" });
      return { error: null, data: res.data };
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Invalid email or password";
      return { error: new Error(msg), data: null };
    }
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("ns_token");
    localStorage.removeItem("ns_profile");
    return { error: null };
  }, []);

  return { user, session, loading, signUp, signIn, signOut };
}