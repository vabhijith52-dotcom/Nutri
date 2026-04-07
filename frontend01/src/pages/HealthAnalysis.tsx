// src/pages/HealthAnalysis.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight, Shield } from "lucide-react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getRiskColor, getRiskLabel, getRiskBgColor, type FlagResult } from "@/lib/nutrition-engine";
import { Button }    from "@/components/ui/button";
import AppLayout from "@/components/AppLayout";
import { mealsAPI } from "@/lib/api";

function RiskGauge({ score }: { score: number }) {
  const color = getRiskColor(score);
  const label = getRiskLabel(score);
  const bg    = getRiskBgColor(score);
  const circ  = 2 * Math.PI * 45;
  const off   = circ - (score / 100) * circ;
  return (
    <div className={`flex flex-col items-center gap-3 p-6 rounded-2xl ${bg}`}>
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="8" className="text-border opacity-30" />
          <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="8"
            className={color} strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={off}
            style={{ transition: "stroke-dashoffset 1s ease-out" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${color}`}>{score}</span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>
      </div>
      <span className={`text-sm font-semibold ${color}`}>{label}</span>
    </div>
  );
}

function FlagCard({ flag }: { flag: FlagResult }) {
  const colors = { low: "bg-success/10 text-success border-success/20", medium: "bg-warning/10 text-warning border-warning/20", high: "bg-destructive/10 text-destructive border-destructive/20" };
  const icons  = { low: "🟢", medium: "🟡", high: "🔴" };
  return (
    <div className={`p-4 rounded-xl border ${colors[flag.severity]}`}>
      <div className="flex items-center gap-2">
        <span>{icons[flag.severity]}</span>
        <span className="text-sm font-semibold">{flag.label}</span>
      </div>
      <p className="text-xs mt-1 opacity-80">{flag.message}</p>
      {flag.moderation && (
        <div className="mt-2 p-2 rounded-lg bg-background/50 border border-current/10">
          <p className="text-xs font-medium flex items-center gap-1"><Shield className="w-3 h-3" /> Moderation:</p>
          <p className="text-xs mt-0.5">{flag.moderation}</p>
        </div>
      )}
    </div>
  );
}

export default function HealthAnalysis() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data,  setData]  = useState<{ risk_score:number; flags:{ flags:FlagResult[] } } | null>(null);
  const [desc,  setDesc]  = useState<string|null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    mealsAPI.getHistory(50).then((res) => {
      for (const m of (res.data || [])) {
        const a = (m.meal_analyses||[]).find((x: { id:string }) => x.id === id);
        if (a) { setData(a); setDesc(m.description); return; }
      }
      setError(true);
    }).catch(() => setError(true));
  }, [id]);

  if (error) return (
    <AppLayout><div className="text-center py-12"><p className="text-muted-foreground">Analysis not found</p><Link to="/meal"><Button className="mt-4 rounded-xl">Log a Meal</Button></Link></div></AppLayout>
  );
  if (!data) return (
    <AppLayout><div className="flex items-center justify-center py-20"><div className="w-8 h-8 rounded-lg gradient-primary animate-pulse-soft" /></div></AppLayout>
  );

  const flags      = data.flags?.flags || [];
  const universal  = flags.filter((f) => f.category === "universal");
  const diabetes   = flags.filter((f) => f.category === "diabetes");
  const obesity    = flags.filter((f) => f.category === "obesity");
  const htn        = flags.filter((f) => f.category === "hypertension");
  const chol       = flags.filter((f) => f.category === "cholesterol");

  return (
    <AppLayout>
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Health Analysis</h1>
          <p className="text-muted-foreground text-sm mt-1">{desc || "Flags and moderation for your meal"}</p>
        </div>

        <div className="glass-strong rounded-2xl p-6"><RiskGauge score={data.risk_score || 0} /></div>

        {universal.length > 0 && <div className="glass-strong rounded-2xl p-6 space-y-3"><h3 className="font-semibold">General Flags</h3><div className="grid gap-2">{universal.map((f,i) => <FlagCard key={i} flag={f} />)}</div></div>}
        {diabetes.length > 0  && <div className="glass-strong rounded-2xl p-6 space-y-3"><h3 className="font-semibold text-nutri-blue">Diabetes Flags</h3><div className="grid gap-2">{diabetes.map((f,i) => <FlagCard key={i} flag={f} />)}</div></div>}
        {obesity.length > 0   && <div className="glass-strong rounded-2xl p-6 space-y-3"><h3 className="font-semibold text-nutri-peach">Obesity Flags</h3><div className="grid gap-2">{obesity.map((f,i) => <FlagCard key={i} flag={f} />)}</div></div>}
        {htn.length > 0       && <div className="glass-strong rounded-2xl p-6 space-y-3"><h3 className="font-semibold text-nutri-rose">Hypertension Flags</h3><div className="grid gap-2">{htn.map((f,i) => <FlagCard key={i} flag={f} />)}</div></div>}
        {chol.length > 0      && <div className="glass-strong rounded-2xl p-6 space-y-3"><h3 className="font-semibold text-nutri-lavender">Cholesterol Flags</h3><div className="grid gap-2">{chol.map((f,i) => <FlagCard key={i} flag={f} />)}</div></div>}

        {flags.length === 0 && (
          <div className="glass-strong rounded-2xl p-8 text-center">
            <p className="text-success font-semibold">✅ No health flags detected!</p>
            <p className="text-sm text-muted-foreground mt-1">This meal looks great for your health profile.</p>
          </div>
        )}

        <Button onClick={() => navigate(`/ai-report/${id}`)} className="w-full rounded-xl gradient-primary border-0 h-12">
          AI Explanation <ArrowRight className="w-4 h-4 ml-2" />
        </Button>

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness. Not medical advice.
        </p>
      </motion.div>
    </AppLayout>
  );
}