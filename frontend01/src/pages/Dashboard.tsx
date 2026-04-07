// src/pages/Dashboard.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Utensils, TrendingUp, Flame, Activity, Plus } from "lucide-react";
import { Button }      from "@/components/ui/button";
import { useAuth }     from "@/hooks/useAuth";
import { useProfile }  from "@/hooks/useProfile";
import { mealsAPI, progressAPI } from "@/lib/api";
import AppLayout from "@/components/AppLayout";

interface MealRow {
  id:           string;
  description:  string | null;
  nutrition_data: { calories?: number } | null;
  meal_analyses:  Array<{ id: string; risk_score: number | null }>;
  created_at:   string;
}

export default function Dashboard() {
  const { user }    = useAuth();
  const { profile } = useProfile();
  const [meals,  setMeals]  = useState<MealRow[]>([]);
  const [streak, setStreak] = useState(0);
  const [loading,setLoading]= useState(true);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good Morning";
    if (h < 17) return "Good Afternoon";
    return "Good Evening";
  };

  useEffect(() => {
    if (!user) return;
    Promise.all([
      mealsAPI.getHistory(5).then((r) => setMeals(r.data || [])),
      progressAPI.getStreak().then((r) => setStreak(r.data.current_streak || 0)),
    ]).finally(() => setLoading(false));
  }, [user]);

  return (
    <AppLayout>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">{greeting()} 👋</h1>
          <p className="text-muted-foreground text-sm mt-1">Here's your health overview</p>
        </div>

        {/* Streak Banner */}
        {streak > 0 && (
          <div className="glass-strong rounded-2xl p-4 flex items-center gap-3">
            <span className="text-2xl">🔥</span>
            <div>
              <p className="font-semibold">{streak}-Day Streak!</p>
              <p className="text-xs text-muted-foreground">Keep logging meals daily to maintain it.</p>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Link to="/meal">
            <div className="glass-strong rounded-2xl p-5 hover:shadow-lg transition-shadow cursor-pointer group">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center mb-3">
                <Utensils className="w-5 h-5 text-primary-foreground" />
              </div>
              <h3 className="font-semibold text-sm">Log Meal</h3>
              <p className="text-xs text-muted-foreground mt-1">Analyze what you ate</p>
            </div>
          </Link>
          <Link to="/progress">
            <div className="glass-strong rounded-2xl p-5 hover:shadow-lg transition-shadow cursor-pointer">
              <div className="w-10 h-10 rounded-xl gradient-cool flex items-center justify-center mb-3">
                <TrendingUp className="w-5 h-5 text-accent-foreground" />
              </div>
              <h3 className="font-semibold text-sm">Track Progress</h3>
              <p className="text-xs text-muted-foreground mt-1">View your trends</p>
            </div>
          </Link>
        </div>

        {/* Health Conditions */}
        {profile?.conditions && profile.conditions.length > 0 && (
          <div className="glass-strong rounded-2xl p-5">
            <h3 className="font-semibold text-sm mb-3">Your Health Focus</h3>
            <div className="flex flex-wrap gap-2">
              {profile.conditions.map((c: string) => (
                <span key={c} className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium capitalize">{c}</span>
              ))}
            </div>
          </div>
        )}

        {/* Daily Check-in Prompt */}
        <Link to="/progress">
          <div className="glass-strong rounded-2xl p-5 border-2 border-dashed border-primary/20 hover:border-primary/40 transition-colors">
            <div className="flex items-center gap-3">
              <Plus className="w-5 h-5 text-primary" />
              <div>
                <h3 className="font-semibold text-sm">Daily Check-in</h3>
                <p className="text-xs text-muted-foreground">How are you feeling today?</p>
              </div>
            </div>
          </div>
        </Link>

        {/* Recent Meals */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Recent Meals</h3>
            <Link to="/meal" className="text-xs text-primary font-medium">Log New</Link>
          </div>

          {loading ? (
            <div className="text-center py-6 text-muted-foreground text-sm">Loading…</div>
          ) : meals.length > 0 ? (
            <div className="space-y-3">
              {meals.map((meal) => {
                const analysis  = meal.meal_analyses?.[0];
                const nutrition = meal.nutrition_data;
                return (
                  <Link key={meal.id} to={analysis ? `/analysis/${analysis.id}` : "#"}>
                    <div className="glass rounded-xl p-4 flex items-center gap-4 hover:shadow-md transition-shadow">
                      <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                        <Utensils className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{meal.description || "Meal"}</p>
                        <div className="flex items-center gap-3 mt-1">
                          {nutrition?.calories && (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Flame className="w-3 h-3" /> {nutrition.calories} kcal
                            </span>
                          )}
                          {analysis?.risk_score != null && (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Activity className="w-3 h-3" /> Risk: {analysis.risk_score}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(meal.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 glass rounded-2xl">
              <Utensils className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No meals logged yet</p>
              <Link to="/meal">
                <Button size="sm" className="mt-3 rounded-xl gradient-primary border-0">Log Your First Meal</Button>
              </Link>
            </div>
          )}
        </div>

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness and lifestyle improvements. It does not provide medical advice or replace your doctor.
        </p>
      </motion.div>
    </AppLayout>
  );
}