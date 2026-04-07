// src/pages/DietPlan.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Loader2, Calendar, Leaf, Drumstick, AlertCircle, X, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input }  from "@/components/ui/input";
import { useProfile }   from "@/hooks/useProfile";
import { dietAPI }      from "@/lib/api";
import { toast }        from "@/hooks/use-toast";
import AppLayout from "@/components/AppLayout";

interface Meal    { type:string; name:string; calories:number; notes:string; }
interface DayPlan { day:string;  meals:Meal[]; }

const DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];

export default function DietPlan() {
  const { profile }    = useProfile();
  const [generating,   setGenerating]   = useState(false);
  const [preference,   setPreference]   = useState<"veg"|"nonveg"|null>(null);
  const [allergies,    setAllergies]    = useState<string[]>([]);
  const [newAllergy,   setNewAllergy]   = useState("");
  const [showSetup,    setShowSetup]    = useState(true);
  const [weekPlan,     setWeekPlan]     = useState<DayPlan[]>([]);

  // ── Load existing active plan ──────────────────────────────────────────────
  useEffect(() => {
    dietAPI.getActive().then((res) => {
      const pd = res.data?.plan_data;
      if (!pd) return;
      const parsed = DAYS.map((day) => ({
        day,
        meals: (["breakfast","lunch","dinner"] as const)
          .filter((m) => pd[day]?.[m])
          .map((m) => ({
            type:     m.charAt(0).toUpperCase() + m.slice(1),
            name:     pd[day][m].meal     || "",
            calories: pd[day][m].calories || 0,
            notes:    pd[day][m].rationale|| "",
          })),
      })).filter((d) => d.meals.length > 0);
      if (parsed.length > 0) { setWeekPlan(parsed); setShowSetup(false); }
    }).catch(() => {});
  }, []);

  const addAllergy    = () => { if (newAllergy.trim()) { setAllergies([...allergies, newAllergy.trim()]); setNewAllergy(""); } };
  const removeAllergy = (i: number) => setAllergies(allergies.filter((_,j) => j !== i));

  // ── Generate plan ──────────────────────────────────────────────────────────
  const generatePlan = async () => {
    if (!preference) { toast({ title: "Please select Veg or Non-Veg", variant: "destructive" }); return; }
    setGenerating(true);
    try {
      const res = await dietAPI.generate(preference, allergies);
      const pd  = res.data?.plan_data;
      if (!pd) throw new Error("Empty plan returned");

      const parsed = DAYS.map((day) => ({
        day,
        meals: (["breakfast","lunch","dinner"] as const)
          .filter((m) => pd[day]?.[m])
          .map((m) => ({
            type:     m.charAt(0).toUpperCase() + m.slice(1),
            name:     pd[day][m].meal     || "",
            calories: pd[day][m].calories || 0,
            notes:    pd[day][m].rationale|| "",
          })),
      })).filter((d) => d.meals.length > 0);

      setWeekPlan(parsed);
      setShowSetup(false);
      toast({ title: "7-day diet plan generated!" });
    } catch {
      toast({ title: "Plan generation failed", description: "Check your Gemini API key in the backend.", variant: "destructive" });
    } finally {
      setGenerating(false);
    }
  };

  const hasPlan = weekPlan.length > 0;

  return (
    <AppLayout>
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Diet Plan</h1>
            <p className="text-muted-foreground text-sm mt-1">
              {profile?.conditions?.length
                ? `Tailored for: ${profile.conditions.join(", ")}`
                : "Your personalized weekly plan"}
            </p>
          </div>
          {hasPlan && !showSetup && (
            <Button variant="outline" onClick={() => setShowSetup(true)} className="rounded-xl">Regenerate</Button>
          )}
        </div>

        {/* Setup Form */}
        {(showSetup || !hasPlan) && (
          <div className="glass-strong rounded-2xl p-6 space-y-5">
            <h3 className="font-semibold">Dietary Preferences</h3>

            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Food Preference</p>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => setPreference("veg")}
                  className={`flex items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all ${preference==="veg" ? "border-success bg-success/10 text-success" : "border-border hover:border-muted-foreground/30"}`}>
                  <Leaf className="w-5 h-5" /><span className="font-medium">Vegetarian</span>
                </button>
                <button onClick={() => setPreference("nonveg")}
                  className={`flex items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all ${preference==="nonveg" ? "border-nutri-peach bg-nutri-peach/10 text-nutri-peach" : "border-border hover:border-muted-foreground/30"}`}>
                  <Drumstick className="w-5 h-5" /><span className="font-medium">Non-Vegetarian</span>
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-warning" />
                <p className="text-sm text-muted-foreground">Any food allergies?</p>
              </div>
              <div className="flex gap-2">
                <Input placeholder="e.g., peanuts, dairy…" value={newAllergy}
                  onChange={(e) => setNewAllergy(e.target.value)}
                  onKeyDown={(e) => e.key==="Enter" && addAllergy()}
                  className="flex-1 rounded-xl" />
                <Button variant="outline" size="icon" onClick={addAllergy} className="rounded-xl">
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {allergies.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {allergies.map((a,i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-warning/10 text-warning text-sm font-medium">
                      {a}<button onClick={() => removeAllergy(i)}><X className="w-3 h-3" /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <Button onClick={generatePlan} disabled={generating || !preference} className="w-full rounded-xl gradient-primary border-0 h-12">
              {generating
                ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Generating with AI…</>
                : "Generate My Plan"}
            </Button>
          </div>
        )}

        {/* Week Plan */}
        {hasPlan && !showSetup && (
          <div className="space-y-4">
            {weekPlan.map((day, i) => (
              <motion.div key={i} initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay: i*0.05 }}
                className="glass-strong rounded-2xl p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold">{day.day}</h3>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {day.meals.reduce((t,m) => t + m.calories, 0)} kcal
                  </span>
                </div>
                <div className="grid gap-2">
                  {day.meals.map((meal, j) => (
                    <div key={j} className="p-3 rounded-xl bg-secondary/50">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-primary uppercase">{meal.type}</span>
                        <span className="text-xs text-muted-foreground">{meal.calories} kcal</span>
                      </div>
                      <p className="text-sm font-medium mt-1">{meal.name}</p>
                      {meal.notes && <p className="text-xs text-muted-foreground mt-1">{meal.notes}</p>}
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness. Not medical advice.
        </p>
      </motion.div>
    </AppLayout>
  );
}