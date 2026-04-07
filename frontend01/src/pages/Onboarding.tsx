// src/pages/Onboarding.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button }   from "@/components/ui/button";
import { Input }    from "@/components/ui/input";
import { Label }    from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Leaf, ArrowRight, ArrowLeft, Upload, Loader2, Check, Activity, Heart, Scale, Beaker } from "lucide-react";
import { useProfile } from "@/hooks/useProfile";
import { metricsAPI } from "@/lib/api";
import { toast }       from "@/hooks/use-toast";

const CONDITIONS = [
  { id: "diabetes",    label: "Diabetes / Prediabetes", icon: Activity, color: "bg-nutri-blue/10 text-nutri-blue border-nutri-blue/30"         },
  { id: "obesity",     label: "Obesity",                icon: Scale,    color: "bg-nutri-peach/10 text-nutri-peach border-nutri-peach/30"       },
  { id: "hypertension",label: "Hypertension",           icon: Heart,    color: "bg-nutri-rose/10 text-nutri-rose border-nutri-rose/30"          },
  { id: "cholesterol", label: "High Cholesterol",       icon: Beaker,   color: "bg-nutri-lavender/10 text-nutri-lavender border-nutri-lavender/30"},
];

// Capitalise first letter to match backend condition names
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export default function Onboarding() {
  const navigate           = useNavigate();
  const { updateProfile }  = useProfile();
  const [step,      setStep]      = useState(1);
  const [conditions,setConditions]= useState<string[]>([]);
  const [healthData,setHealthData]= useState({
    hba1c:"", fasting_sugar:"", weight:"", bmi:"",
    systolic_bp:"", diastolic_bp:"",
    ldl:"", hdl:"", triglycerides:"",
  });
  const [basicInfo, setBasicInfo] = useState({ age:"", gender:"" });
  const [inputMode, setInputMode] = useState<"manual"|"upload">("manual");
  const [uploading, setUploading] = useState(false);
  const [uploaded,  setUploaded]  = useState<File|null>(null);
  const [detectedConditions, setDetectedConditions] = useState<string[]>([]);

  const totalSteps = 3;
  const progress   = (step / totalSteps) * 100;

  const toggle = (id: string) =>
    setConditions((p) => p.includes(id) ? p.filter((c) => c !== id) : [...p, id]);

  // ── Lab report upload ──────────────────────────────────────────────────────
  const handleFileUpload = async (file: File) => {
    setUploaded(file);
    setUploading(true);
    try {
      const res = await metricsAPI.extractLab(file);
      const { extracted, detected_conditions } = res.data;

      setHealthData({
        hba1c:         extracted.hba1c         ? String(extracted.hba1c)         : "",
        fasting_sugar: extracted.fasting_sugar  ? String(extracted.fasting_sugar) : "",
        weight:        extracted.weight         ? String(extracted.weight)         : "",
        bmi:           extracted.bmi            ? String(extracted.bmi)            : "",
        systolic_bp:   extracted.systolic_bp    ? String(extracted.systolic_bp)   : "",
        diastolic_bp:  extracted.diastolic_bp   ? String(extracted.diastolic_bp)  : "",
        ldl:           extracted.ldl            ? String(extracted.ldl)            : "",
        hdl:           extracted.hdl            ? String(extracted.hdl)            : "",
        triglycerides: extracted.triglycerides  ? String(extracted.triglycerides)  : "",
      });

      if (detected_conditions?.length > 0) {
        // Map backend condition names back to lowercase IDs for the toggle UI
        const ids = detected_conditions.map((c: string) => c.toLowerCase());
        setConditions(ids);
        setDetectedConditions(ids);
      }

      toast({ title: "Lab report analyzed!", description: "Values pre-filled. Review and edit as needed." });
    } catch {
      toast({ title: "Upload failed", description: "Please enter values manually.", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  // ── Complete onboarding ────────────────────────────────────────────────────
  const handleComplete = async () => {
    try {
      // Build metrics list for time-series storage
      const addMetric = (type: string, val: string, unit: string) =>
        val ? [{ metric_type: type, value: Number(val), unit }] : [];

      const metrics = [
        ...addMetric("hba1c",         healthData.hba1c,         "%"),
        ...addMetric("fasting_sugar", healthData.fasting_sugar, "mg/dL"),
        ...addMetric("weight",        healthData.weight,         "kg"),
        ...addMetric("bmi",           healthData.bmi,            "kg/m2"),
        ...addMetric("systolic_bp",   healthData.systolic_bp,   "mmHg"),
        ...addMetric("diastolic_bp",  healthData.diastolic_bp,  "mmHg"),
        ...addMetric("ldl",           healthData.ldl,            "mg/dL"),
        ...addMetric("hdl",           healthData.hdl,            "mg/dL"),
        ...addMetric("triglycerides", healthData.triglycerides,  "mg/dL"),
      ];

      // Confirm conditions + save metrics in one call
      await metricsAPI.confirmExtracted(
        conditions.map(cap),   // ["Diabetes","Hypertension",…]
        {},
        metrics,
      );

      // Mark onboarding complete + save basic info
      await updateProfile.mutateAsync({
        age:                 basicInfo.age    ? Number(basicInfo.age) : null,
        gender:              basicInfo.gender || null,
        onboarding_complete: true,
      } as Parameters<typeof updateProfile.mutateAsync>[0]);

      navigate("/dashboard");
    } catch {
      toast({ title: "Error saving profile", variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen bg-background p-4 flex flex-col items-center justify-center">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full gradient-primary opacity-10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full gradient-cool opacity-10 blur-3xl" />
      </div>

      <div className="w-full max-w-lg space-y-6 relative z-10">
        <div className="flex items-center gap-2 justify-center mb-2">
          <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
            <Leaf className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg">NutriSense</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Step {step} of {totalSteps}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2 rounded-full" />
        </div>

        <AnimatePresence mode="wait">

          {/* ── Step 1: Conditions ── */}
          {step === 1 && (
            <motion.div key="s1" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }}
              className="glass-strong rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="text-xl font-bold">Health Conditions</h2>
                <p className="text-sm text-muted-foreground mt-1">Select any conditions that apply to you</p>
              </div>
              <div className="space-y-3">
                {CONDITIONS.map(({ id, label, icon: Icon, color }) => (
                  <button key={id} onClick={() => toggle(id)}
                    className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                      conditions.includes(id) ? `${color} border-current` : "border-border hover:border-muted-foreground/30"
                    }`}>
                    <Icon className="w-5 h-5" />
                    <span className="font-medium flex-1 text-left">{label}</span>
                    {conditions.includes(id) && <Check className="w-5 h-5" />}
                  </button>
                ))}
              </div>
              <Button onClick={() => setStep(2)} className="w-full rounded-xl gradient-primary border-0">
                Continue <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </motion.div>
          )}

          {/* ── Step 2: Metrics ── */}
          {step === 2 && (
            <motion.div key="s2" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }}
              className="glass-strong rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="text-xl font-bold">Health Metrics</h2>
                <p className="text-sm text-muted-foreground mt-1">Enter your values or upload a lab report</p>
              </div>

              <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as "manual"|"upload")}>
                <TabsList className="w-full rounded-xl">
                  <TabsTrigger value="manual"  className="flex-1 rounded-lg">Enter Manually</TabsTrigger>
                  <TabsTrigger value="upload"  className="flex-1 rounded-lg">Upload Lab Report</TabsTrigger>
                </TabsList>
              </Tabs>

              {inputMode === "upload" && (
                <label
                  className="flex flex-col items-center gap-3 p-8 border-2 border-dashed border-border rounded-xl cursor-pointer hover:border-primary/50 transition-colors"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if(f) handleFileUpload(f); }}
                >
                  {uploading ? (
                    <><Loader2 className="w-8 h-8 text-primary animate-spin" /><span className="text-sm text-muted-foreground">Analyzing your report…</span></>
                  ) : uploaded ? (
                    <><Check className="w-8 h-8 text-success" /><span className="text-sm text-muted-foreground">{uploaded.name}</span></>
                  ) : (
                    <><Upload className="w-8 h-8 text-muted-foreground" /><span className="text-sm text-muted-foreground">Drop PDF, JPG, or PNG here</span><span className="text-xs text-muted-foreground">Max 15MB</span></>
                  )}
                  <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => { const f = e.target.files?.[0]; if(f) handleFileUpload(f); }} />
                </label>
              )}

              {detectedConditions.length > 0 && (
                <div className="p-3 rounded-xl bg-success/10 border border-success/20 text-sm text-success">
                  ✅ Detected: {detectedConditions.map(cap).join(", ")}
                </div>
              )}

              <div className="space-y-3">
                {conditions.includes("diabetes") && (
                  <div className="space-y-3 p-4 rounded-xl bg-nutri-blue/5 border border-nutri-blue/20">
                    <p className="text-sm font-medium text-nutri-blue">Diabetes Metrics</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label className="text-xs">HbA1c (%)</Label><Input type="number" step="0.1" placeholder="5.7" value={healthData.hba1c} onChange={e=>setHealthData({...healthData,hba1c:e.target.value})} className="rounded-lg" /></div>
                      <div><Label className="text-xs">Fasting Sugar (mg/dL)</Label><Input type="number" placeholder="100" value={healthData.fasting_sugar} onChange={e=>setHealthData({...healthData,fasting_sugar:e.target.value})} className="rounded-lg" /></div>
                    </div>
                  </div>
                )}
                {conditions.includes("obesity") && (
                  <div className="space-y-3 p-4 rounded-xl bg-nutri-peach/5 border border-nutri-peach/20">
                    <p className="text-sm font-medium text-nutri-peach">Weight Metrics</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label className="text-xs">Weight (kg)</Label><Input type="number" step="0.1" placeholder="75" value={healthData.weight} onChange={e=>setHealthData({...healthData,weight:e.target.value})} className="rounded-lg" /></div>
                      <div><Label className="text-xs">BMI</Label><Input type="number" step="0.1" placeholder="25.0" value={healthData.bmi} onChange={e=>setHealthData({...healthData,bmi:e.target.value})} className="rounded-lg" /></div>
                    </div>
                  </div>
                )}
                {conditions.includes("hypertension") && (
                  <div className="space-y-3 p-4 rounded-xl bg-nutri-rose/5 border border-nutri-rose/20">
                    <p className="text-sm font-medium text-nutri-rose">Blood Pressure</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label className="text-xs">Systolic (mmHg)</Label><Input type="number" placeholder="120" value={healthData.systolic_bp} onChange={e=>setHealthData({...healthData,systolic_bp:e.target.value})} className="rounded-lg" /></div>
                      <div><Label className="text-xs">Diastolic (mmHg)</Label><Input type="number" placeholder="80" value={healthData.diastolic_bp} onChange={e=>setHealthData({...healthData,diastolic_bp:e.target.value})} className="rounded-lg" /></div>
                    </div>
                  </div>
                )}
                {conditions.includes("cholesterol") && (
                  <div className="space-y-3 p-4 rounded-xl bg-nutri-lavender/5 border border-nutri-lavender/20">
                    <p className="text-sm font-medium text-nutri-lavender">Cholesterol Metrics</p>
                    <div className="grid grid-cols-3 gap-3">
                      <div><Label className="text-xs">LDL (mg/dL)</Label><Input type="number" placeholder="100" value={healthData.ldl} onChange={e=>setHealthData({...healthData,ldl:e.target.value})} className="rounded-lg" /></div>
                      <div><Label className="text-xs">HDL (mg/dL)</Label><Input type="number" placeholder="50" value={healthData.hdl} onChange={e=>setHealthData({...healthData,hdl:e.target.value})} className="rounded-lg" /></div>
                      <div><Label className="text-xs">Triglycerides</Label><Input type="number" placeholder="150" value={healthData.triglycerides} onChange={e=>setHealthData({...healthData,triglycerides:e.target.value})} className="rounded-lg" /></div>
                    </div>
                  </div>
                )}
                {conditions.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">No conditions selected. You can go back and select conditions, or continue.</p>
                )}
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)} className="rounded-xl"><ArrowLeft className="w-4 h-4 mr-2" /> Back</Button>
                <Button onClick={() => setStep(3)} className="flex-1 rounded-xl gradient-primary border-0">Continue <ArrowRight className="w-4 h-4 ml-2" /></Button>
              </div>
            </motion.div>
          )}

          {/* ── Step 3: Basic Info ── */}
          {step === 3 && (
            <motion.div key="s3" initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-20 }}
              className="glass-strong rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="text-xl font-bold">Basic Information</h2>
                <p className="text-sm text-muted-foreground mt-1">Almost done! Tell us a bit about yourself</p>
              </div>
              <div className="space-y-4">
                <div>
                  <Label>Age</Label>
                  <Input type="number" placeholder="30" value={basicInfo.age}
                    onChange={(e) => setBasicInfo({ ...basicInfo, age: e.target.value })}
                    className="rounded-xl mt-1" />
                </div>
                <div>
                  <Label>Gender</Label>
                  <div className="grid grid-cols-3 gap-3 mt-2">
                    {["male","female","other"].map((g) => (
                      <button key={g} onClick={() => setBasicInfo({ ...basicInfo, gender: g })}
                        className={`p-3 rounded-xl border-2 text-sm font-medium capitalize transition-all ${
                          basicInfo.gender === g ? "border-primary bg-primary/10 text-primary" : "border-border hover:border-muted-foreground/30"
                        }`}>{g}</button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)} className="rounded-xl"><ArrowLeft className="w-4 h-4 mr-2" /> Back</Button>
                <Button onClick={handleComplete} className="flex-1 rounded-xl gradient-primary border-0">
                  Complete Setup <Check className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}