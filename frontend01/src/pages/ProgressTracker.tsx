// src/pages/ProgressTracker.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Award, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { progressAPI } from "@/lib/api";
import { getRiskColor } from "@/lib/nutrition-engine";
import AppLayout from "@/components/AppLayout";

interface DayData { day: string; calories: number; }

export default function ProgressTracker() {
  const [streak,     setStreak]     = useState(0);
  const [longest,    setLongest]    = useState(0);
  const [weeklyData, setWeeklyData] = useState<DayData[]>([]);
  const [hasPlan,    setHasPlan]    = useState(false);
  const [thisMonth,  setThisMonth]  = useState(0);
  const [lastMonth,  setLastMonth]  = useState(0);
  const [trend,      setTrend]      = useState<"better"|"worse"|"same">("same");

  useEffect(() => {
    progressAPI.getStreak().then((r) => {
      setStreak(r.data.current_streak || 0);
      setLongest(r.data.longest_streak || 0);
    }).catch(() => {});

    progressAPI.getWeeklyNutrients().then((r) => {
      setHasPlan(r.data.has_plan || false);
      if (r.data.data?.length > 0) setWeeklyData(r.data.data);
    }).catch(() => {});

    progressAPI.getMonthlySummary().then((r) => {
      setThisMonth(r.data.this_month?.avg_risk || 0);
      setLastMonth(r.data.last_month?.avg_risk || 0);
      setTrend(r.data.trend || "same");
    }).catch(() => {});
  }, []);

  const TrendIcon  = trend === "better" ? TrendingDown : trend === "worse" ? TrendingUp : Minus;
  const trendColor = trend === "better" ? "text-success" : trend === "worse" ? "text-destructive" : "text-muted-foreground";
  const trendText  = trend === "better" ? "Improving! Lower risk than last month." : trend === "worse" ? "Risk increased from last month." : "Consistent with last month.";

  return (
    <AppLayout>
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Track Progress</h1>
          <p className="text-muted-foreground text-sm mt-1">Your nutrition journey at a glance</p>
        </div>

        {/* Streak Card */}
        <div className="glass-strong rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center">
              <Award className="w-7 h-7 text-primary-foreground" />
            </div>
            <div>
              <p className="text-3xl font-bold">{streak}</p>
              <p className="text-sm text-muted-foreground">Day Streak 🔥</p>
            </div>
            {longest > 0 && (
              <div className="ml-auto text-right">
                <p className="text-lg font-bold">{longest}</p>
                <p className="text-xs text-muted-foreground">Best streak</p>
              </div>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {streak === 0
              ? "Log a meal and have an active diet plan to start your streak!"
              : streak >= 7
              ? "Amazing consistency! Keep going!"
              : "Keep logging meals daily to build your streak!"}
          </p>
        </div>

        {/* Weekly Graph */}
        {hasPlan && weeklyData.length > 0 ? (
          <div className="glass-strong rounded-2xl p-6 space-y-4">
            <div>
              <h3 className="font-semibold">Weekly Calorie Targets</h3>
              <p className="text-xs text-muted-foreground mt-1">From your active diet plan (what you should eat)</p>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="day" tick={{ fontSize:11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize:11 }} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip
                    contentStyle={{ borderRadius:12, border:"none", boxShadow:"0 4px 12px rgba(0,0,0,0.1)", background:"hsl(var(--background))" }}
                    formatter={(v) => [`${v} kcal`, "Target"]} />
                  <Bar dataKey="calories" name="Target Calories" fill="hsl(var(--primary))" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <div className="glass-strong rounded-2xl p-6 text-center text-muted-foreground">
            <p className="font-medium mb-1">No diet plan yet</p>
            <p className="text-sm">Generate a diet plan to see your weekly calorie targets here.</p>
          </div>
        )}

        {/* Monthly Comparison */}
        <div className="glass-strong rounded-2xl p-6 space-y-4">
          <h3 className="font-semibold">Monthly Risk Analysis</h3>
          {thisMonth > 0 || lastMonth > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-secondary/50 text-center">
                  <p className="text-xs text-muted-foreground mb-1">This Month Avg Risk</p>
                  <p className={`text-2xl font-bold ${getRiskColor(thisMonth)}`}>{thisMonth}</p>
                </div>
                <div className="p-4 rounded-xl bg-secondary/50 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Last Month Avg Risk</p>
                  <p className={`text-2xl font-bold ${getRiskColor(lastMonth)}`}>{lastMonth}</p>
                </div>
              </div>
              <div className={`flex items-center gap-2 p-3 rounded-xl ${trend==="better" ? "bg-success/10" : trend==="worse" ? "bg-destructive/10" : "bg-secondary/50"}`}>
                <TrendIcon className={`w-5 h-5 ${trendColor}`} />
                <p className={`text-sm font-medium ${trendColor}`}>{trendText}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Log meals to see your monthly comparison.</p>
          )}
        </div>

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness. Not medical advice.
        </p>
      </motion.div>
    </AppLayout>
  );
}