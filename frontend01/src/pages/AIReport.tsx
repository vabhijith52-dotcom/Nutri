// src/pages/AIReport.tsx
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Brain, ArrowRight, AlertTriangle, BookOpen, Lightbulb, FileText } from "lucide-react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button }    from "@/components/ui/button";
import AppLayout from "@/components/AppLayout";
import { mealsAPI } from "@/lib/api";

interface Section {
  title: string;
  icon:  React.ReactNode;
  items: string[];
  type:  "assessment"|"flags"|"guidelines"|"alternatives";
}

function parseExplanation(text: string): Section[] {
  const sections: Section[] = [];
  let cur: Section | null   = null;
  for (const line of text.split("\n")) {
    if (line.startsWith("## ")) {
      if (cur && cur.items.length > 0) sections.push(cur);
      const title = line.replace("## ", "");
      let icon: React.ReactNode = <FileText className="w-5 h-5" />;
      let type: Section["type"] = "assessment";
      if (title.includes("Flagged"))     { icon = <AlertTriangle className="w-5 h-5" />; type = "flags"; }
      if (title.includes("Guidelines"))  { icon = <BookOpen      className="w-5 h-5" />; type = "guidelines"; }
      if (title.includes("Alternative")) { icon = <Lightbulb     className="w-5 h-5" />; type = "alternatives"; }
      cur = { title, icon, items: [], type };
    } else if (line.startsWith("---") || (line.startsWith("*") && line.endsWith("*"))) {
      // skip
    } else if (line.trim()) {
      cur?.items.push(line);
    }
  }
  if (cur && cur.items.length > 0) sections.push(cur);
  return sections;
}

function renderItem(line: string, i: number) {
  const flag = line.match(/^(🔴|🟡|🟢)\s*\*\*(.+?)\*\*:\s*(.+)/);
  if (flag) {
    const [, emoji, label, msg] = flag;
    const bg = emoji==="🔴" ? "bg-destructive/10 border-destructive/20" : emoji==="🟡" ? "bg-warning/10 border-warning/20" : "bg-success/10 border-success/20";
    return <div key={i} className={`p-3 rounded-xl border ${bg}`}><p className="text-sm"><span className="mr-1">{emoji}</span><strong className="text-foreground">{label}</strong>: <span className="text-muted-foreground">{msg}</span></p></div>;
  }
  if (line.includes("*Recommendation*")) {
    const rec = line.replace(/.*\*Recommendation\*:\s*/, "");
    return <div key={i} className="ml-4 p-2.5 rounded-lg bg-primary/5 border-l-2 border-primary"><p className="text-xs text-primary">→ {rec}</p></div>;
  }
  const bold = line.match(/^- \*\*(.+?)\*\*:\s*(.+)/);
  if (bold) return <div key={i} className="flex gap-2 pl-1"><span className="text-primary mt-0.5 text-sm">•</span><p className="text-sm"><strong className="text-foreground">{bold[1]}</strong>: <span className="text-muted-foreground">{bold[2]}</span></p></div>;
  if (line.startsWith("- ")) return <div key={i} className="flex gap-2 pl-1"><span className="text-primary mt-0.5 text-sm">•</span><p className="text-sm text-muted-foreground">{line.replace("- ","")}</p></div>;
  return <p key={i} className="text-sm text-muted-foreground">{line}</p>;
}

const sectionStyles: Record<Section["type"], { border:string; iconBg:string; iconColor:string }> = {
  assessment:  { border:"border-primary/20",     iconBg:"bg-primary/10",     iconColor:"text-primary"     },
  flags:       { border:"border-destructive/20",  iconBg:"bg-destructive/10", iconColor:"text-destructive" },
  guidelines:  { border:"border-accent/20",       iconBg:"bg-accent/10",      iconColor:"text-accent"      },
  alternatives:{ border:"border-success/20",      iconBg:"bg-success/10",     iconColor:"text-success"     },
};

export default function AIReport() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [explanation, setExplanation] = useState<string>("");
  const [foodSwaps,   setFoodSwaps]   = useState<Array<{ from:string; to:string; reason:string }>>([]);
  const [error,       setError]       = useState(false);

  useEffect(() => {
    if (!id) return;
    mealsAPI.getHistory(50).then((res) => {
      for (const m of (res.data || [])) {
        const a = (m.meal_analyses||[]).find((x: { id:string }) => x.id === id);
        if (a) { setExplanation(a.ai_explanation || ""); setFoodSwaps(a.food_swaps || []); return; }
      }
      setError(true);
    }).catch(() => setError(true));
  }, [id]);

  if (error) return (
    <AppLayout><div className="text-center py-12"><p className="text-muted-foreground">Report not found</p><Link to="/meal"><Button className="mt-4 rounded-xl">Log a Meal</Button></Link></div></AppLayout>
  );
  if (!explanation) return (
    <AppLayout><div className="flex items-center justify-center py-20"><div className="w-8 h-8 rounded-lg gradient-primary animate-pulse-soft" /></div></AppLayout>
  );

  const sections = parseExplanation(explanation);

  return (
    <AppLayout>
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
            <Brain className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">AI Report</h1>
            <p className="text-muted-foreground text-sm">Detailed explanation and recommendations</p>
          </div>
        </div>

        {sections.map((sec, si) => {
          const s = sectionStyles[sec.type];
          return (
            <motion.div key={si} initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay: si*0.1 }}
              className={`glass-strong rounded-2xl border ${s.border} overflow-hidden`}>
              <div className={`flex items-center gap-3 px-5 py-4 border-b border-border/30`}>
                <div className={`w-9 h-9 rounded-lg ${s.iconBg} flex items-center justify-center ${s.iconColor}`}>
                  {sec.icon}
                </div>
                <h2 className="font-semibold text-base">{sec.title}</h2>
              </div>
              <div className="px-5 py-4 space-y-2.5">
                {sec.items.map((item, i) => renderItem(item, i))}
              </div>
            </motion.div>
          );
        })}

        {/* Food Swaps */}
        {foodSwaps.length > 0 && (
          <div className="glass-strong rounded-2xl p-6 space-y-3">
            <h3 className="font-semibold">🔄 Smart Food Swaps</h3>
            {foodSwaps.map((s, i) => (
              <div key={i} className="glass rounded-xl p-4 space-y-1">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-destructive line-through">{s.from}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-success font-semibold">{s.to}</span>
                </div>
                <p className="text-xs text-muted-foreground">{s.reason}</p>
              </div>
            ))}
          </div>
        )}

        <Button onClick={() => navigate("/diet-plan")} className="w-full rounded-xl gradient-primary border-0 h-12">
          Generate Diet Plan <ArrowRight className="w-4 h-4 ml-2" />
        </Button>

        <p className="text-xs text-center text-muted-foreground py-2">
          NutriSense supports dietary awareness. Not medical advice.
        </p>
      </motion.div>
    </AppLayout>
  );
}