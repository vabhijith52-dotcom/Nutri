// src/pages/AnalysisDashboard.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Flame, Wheat, Droplets, Zap, Leaf, Activity, ArrowRight } from "lucide-react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button }    from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import AppLayout from "@/components/AppLayout";
import { mealsAPI } from "@/lib/api";

interface NRow { calories:number; carbs:number; protein:number; fat:number; fiber:number; sugar:number; sodium:number; }

export default function AnalysisDashboard() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [meal,   setMeal]   = useState<{ description:string|null; nutrition_data:NRow|null; per_item_nutrition:Record<string,NRow>|null } | null>(null);
  const [aId,    setAId]    = useState<string>("");
  const [error,  setError]  = useState(false);

  useEffect(() => {
    if (!id) return;
    mealsAPI.getHistory(50).then((res) => {
      for (const m of (res.data || [])) {
        const analysis = (m.meal_analyses || []).find((a: { id: string }) => a.id === id);
        if (analysis) { setMeal(m); setAId(analysis.id); return; }
      }
      setError(true);
    }).catch(() => setError(true));
  }, [id]);

  if (error) return (
    <AppLayout><div className="text-center py-12"><p className="text-muted-foreground">Analysis not found</p><Link to="/meal"><Button className="mt-4 rounded-xl">Log a Meal</Button></Link></div></AppLayout>
  );
  if (!meal) return (
    <AppLayout><div className="flex items-center justify-center py-20"><div className="w-8 h-8 rounded-lg gradient-primary animate-pulse-soft" /></div></AppLayout>
  );

  const per   = (meal.per_item_nutrition || {}) as Record<string, NRow>;
  const total = (meal.nutrition_data     || {}) as NRow;
  const names = Object.keys(per);

  const nutrients = [
    { key:"calories", label:"Calories", unit:"kcal", icon:Flame,    color:"text-nutri-peach"   },
    { key:"carbs",    label:"Carbs",    unit:"g",    icon:Wheat,    color:"text-nutri-blue"    },
    { key:"protein",  label:"Protein",  unit:"g",    icon:Zap,      color:"text-primary"       },
    { key:"fat",      label:"Fat",      unit:"g",    icon:Droplets, color:"text-nutri-lavender"},
    { key:"fiber",    label:"Fiber",    unit:"g",    icon:Leaf,     color:"text-success"       },
    { key:"sugar",    label:"Sugar",    unit:"g",    icon:Activity, color:"text-nutri-rose"    },
    { key:"sodium",   label:"Sodium",   unit:"mg",   icon:Droplets, color:"text-warning"       },
  ];

  return (
    <AppLayout>
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Nutrient Breakdown</h1>
          <p className="text-muted-foreground text-sm mt-1">{meal.description || "Per-item nutrition details"}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {nutrients.slice(0,4).map(({ key, label, unit, icon:Icon, color }) => (
            <div key={key} className="glass rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-secondary/50">
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-bold">{(total as Record<string,number>)[key] || 0}<span className="text-xs text-muted-foreground ml-0.5">{unit}</span></p>
              </div>
            </div>
          ))}
        </div>

        {names.length > 0 && (
          <div className="glass-strong rounded-2xl p-6 space-y-4">
            <h3 className="font-semibold">Per-Item Breakdown</h3>
            <div className="rounded-xl border border-border overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs font-semibold">Food</TableHead>
                    <TableHead className="text-xs text-right">Cal</TableHead>
                    <TableHead className="text-xs text-right">Carbs</TableHead>
                    <TableHead className="text-xs text-right">Protein</TableHead>
                    <TableHead className="text-xs text-right">Fat</TableHead>
                    <TableHead className="text-xs text-right">Fiber</TableHead>
                    <TableHead className="text-xs text-right">Sodium</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {names.map((name) => { const n = per[name]; return (
                    <TableRow key={name}>
                      <TableCell className="font-medium text-sm capitalize">{name}</TableCell>
                      <TableCell className="text-right text-sm">{n.calories}</TableCell>
                      <TableCell className="text-right text-sm">{n.carbs}g</TableCell>
                      <TableCell className="text-right text-sm">{n.protein}g</TableCell>
                      <TableCell className="text-right text-sm">{n.fat}g</TableCell>
                      <TableCell className="text-right text-sm">{n.fiber}g</TableCell>
                      <TableCell className="text-right text-sm">{n.sodium}mg</TableCell>
                    </TableRow>
                  ); })}
                  <TableRow className="bg-muted/30 font-semibold">
                    <TableCell className="text-sm">Total</TableCell>
                    <TableCell className="text-right text-sm">{total.calories}</TableCell>
                    <TableCell className="text-right text-sm">{total.carbs}g</TableCell>
                    <TableCell className="text-right text-sm">{total.protein}g</TableCell>
                    <TableCell className="text-right text-sm">{total.fat}g</TableCell>
                    <TableCell className="text-right text-sm">{total.fiber}g</TableCell>
                    <TableCell className="text-right text-sm">{total.sodium}mg</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        <Button onClick={() => navigate(`/health-analysis/${aId}`)} className="w-full rounded-xl gradient-primary border-0 h-12">
          Run Health Analysis <ArrowRight className="w-4 h-4 ml-2" />
        </Button>

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness. Not medical advice.
        </p>
      </motion.div>
    </AppLayout>
  );
}