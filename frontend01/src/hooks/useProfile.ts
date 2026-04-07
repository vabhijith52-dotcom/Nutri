// src/hooks/useProfile.tsx
import { useEffect, useState, useCallback } from "react";
import { authAPI } from "@/lib/api";

export interface Profile {
  id:                      string;
  user_id:                 string;
  full_name:               string | null;
  age:                     number | null;
  gender:                  string | null;
  conditions:              string[] | null;
  condition_severities:    Record<string, string> | null;
  hba1c:                   number | null;
  fasting_sugar:           number | null;
  weight:                  number | null;
  bmi:                     number | null;
  systolic_bp:             number | null;
  diastolic_bp:            number | null;
  ldl:                     number | null;
  hdl:                     number | null;
  triglycerides:           number | null;
  food_preference:         string | null;
  allergies:               string[] | null;
  doctor_gi_limit:         number | null;
  doctor_sodium_limit_mg:  number | null;
  doctor_calorie_target:   number | null;
  current_streak:          number;
  longest_streak:          number;
  last_streak_date:        string | null;
  onboarding_complete:     boolean | null;
  created_at:              string;
  updated_at:              string;
}

export function useProfile() {
  const [profile,   setProfile]   = useState<Profile | null>(() => {
    try {
      const cached = localStorage.getItem("ns_profile");
      return cached ? JSON.parse(cached) : null;
    } catch { return null; }
  });
  const [isLoading, setIsLoading] = useState(!profile);

  const fetchProfile = useCallback(async () => {
    const token = localStorage.getItem("ns_token");
    if (!token) { setIsLoading(false); return; }
    try {
      const res = await authAPI.getMe();
      setProfile(res.data);
      localStorage.setItem("ns_profile", JSON.stringify(res.data));
    } catch {
      localStorage.removeItem("ns_token");
      localStorage.removeItem("ns_profile");
      setProfile(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const updateProfile = {
    mutateAsync: async (updates: Partial<Profile>) => {
      const res = await authAPI.updateProfile(updates as Record<string, unknown>);
      const updated = { ...profile, ...updates } as Profile;
      setProfile(updated);
      localStorage.setItem("ns_profile", JSON.stringify(updated));
      return res.data;
    },
    isPending: false,
  };

  return { profile, isLoading, updateProfile, refetch: fetchProfile };
}