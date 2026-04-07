// src/pages/MealInput.tsx
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input }  from "@/components/ui/input";
import { Utensils, Loader2, X, Plus, Sparkles, Camera, Upload, ImageIcon, Pencil } from "lucide-react";
import { useAuth }    from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { mealsAPI }   from "@/lib/api";
import { toast }      from "@/hooks/use-toast";
import AppLayout from "@/components/AppLayout";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface FoodEntry { name: string; quantity: number; }

export default function MealInput() {
  const { user }      = useAuth();
  const navigate      = useNavigate();
  const [items,       setItems]       = useState<FoodEntry[]>([]);
  const [newName,     setNewName]     = useState("");
  const [newQty,      setNewQty]      = useState("");
  const [analyzing,   setAnalyzing]   = useState(false);
  const [detecting,   setDetecting]   = useState(false);
  const [mode,        setMode]        = useState<"manual"|"image">("manual");
  const [previewUrl,  setPreviewUrl]  = useState<string|null>(null);
  const [editIdx,     setEditIdx]     = useState<number|null>(null);
  const [editName,    setEditName]    = useState("");
  const [editQty,     setEditQty]     = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const addItem = () => {
    const name = newName.trim();
    const qty  = parseInt(newQty) || 100;
    if (!name) { toast({ title: "Enter a food name", variant: "destructive" }); return; }
    setItems([...items, { name, quantity: qty }]);
    setNewName(""); setNewQty("");
  };

  const removeItem  = (i: number) => setItems(items.filter((_, j) => j !== i));
  const startEdit   = (i: number) => { setEditIdx(i); setEditName(items[i].name); setEditQty(String(items[i].quantity)); };
  const saveEdit    = (i: number) => {
    const updated = [...items];
    updated[i] = { name: editName.trim() || updated[i].name, quantity: parseInt(editQty) || updated[i].quantity };
    setItems(updated); setEditIdx(null);
  };

  // ── Image upload + AI detection ────────────────────────────────────────────
  const handleImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { toast({ title: "Upload an image file", variant: "destructive" }); return; }

    setPreviewUrl(URL.createObjectURL(file));
    setDetecting(true);
    try {
      const res = await mealsAPI.detectImage(file);
      const detected: Array<{ name: string; quantity: number }> = res.data.items || [];
      setItems(detected);
      toast({ title: `${detected.length} food items detected`, description: res.data.notes || "Review and edit as needed" });
    } catch {
      toast({ title: "Detection failed", description: "Please add items manually", variant: "destructive" });
      setMode("manual");
    } finally {
      setDetecting(false);
    }
  };

  // ── Analyze meal ───────────────────────────────────────────────────────────
  const analyzeMeal = async () => {
    if (!user || items.length === 0) { toast({ title: "Add at least one food item", variant: "destructive" }); return; }
    setAnalyzing(true);
    try {
      const description = items.map((f) => `${f.name} (${f.quantity}g)`).join(", ");
      const res = await mealsAPI.analyze(items, description, previewUrl || undefined);
      const analysisId = res.data?.analysis?.id;
      if (analysisId) navigate(`/analysis/${analysisId}`);
      else toast({ title: "Analysis complete but no ID returned", variant: "destructive" });
    } catch {
      toast({ title: "Analysis failed", description: "Make sure the backend is running on port 8000.", variant: "destructive" });
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <AppLayout>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Log Your Meal</h1>
          <p className="text-muted-foreground text-sm mt-1">Add food items manually or upload a photo</p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2">
          <Button variant={mode==="manual"?"default":"outline"} onClick={() => setMode("manual")} className="flex-1 rounded-xl">
            <Utensils className="w-4 h-4 mr-2" /> Manual Entry
          </Button>
          <Button variant={mode==="image"?"default":"outline"} onClick={() => setMode("image")} className="flex-1 rounded-xl">
            <Camera className="w-4 h-4 mr-2" /> Upload Image
          </Button>
        </div>

        {/* Image Upload */}
        {mode === "image" && (
          <div className="glass-strong rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-primary" />
              <h3 className="font-semibold">Upload Meal Photo</h3>
            </div>
            <p className="text-xs text-muted-foreground">AI will identify food items. You can edit the results.</p>
            <input ref={fileRef} type="file" accept="image/*" onChange={handleImage} className="hidden" />

            {previewUrl ? (
              <div className="relative rounded-xl overflow-hidden border border-border">
                <img src={previewUrl} alt="Meal" className="w-full max-h-56 object-cover" />
                <button onClick={() => { setPreviewUrl(null); setItems([]); fileRef.current?.click(); }}
                  className="absolute top-2 right-2 bg-background/80 backdrop-blur rounded-full p-1.5">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button onClick={() => fileRef.current?.click()}
                className="w-full h-40 rounded-xl border-2 border-dashed border-border hover:border-primary/50 transition-colors flex flex-col items-center justify-center gap-3 text-muted-foreground hover:text-foreground">
                <Upload className="w-8 h-8" />
                <span className="text-sm font-medium">Click to upload meal photo</span>
                <span className="text-xs">JPG, PNG supported · Max 10MB</span>
              </button>
            )}

            {detecting && (
              <div className="flex items-center justify-center gap-2 py-4 text-primary">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm font-medium">AI is detecting food items…</span>
              </div>
            )}
          </div>
        )}

        {/* Manual Entry */}
        {mode === "manual" && (
          <div className="glass-strong rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Utensils className="w-5 h-5 text-primary" />
              <h3 className="font-semibold">Add Food Items</h3>
            </div>
            <div className="flex gap-2">
              <Input placeholder="Food name (e.g., moong_dal)" value={newName} onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addItem()} className="flex-1 rounded-xl" />
              <Input type="number" placeholder="Grams" value={newQty} onChange={(e) => setNewQty(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addItem()} className="w-24 rounded-xl" />
              <Button variant="outline" size="icon" onClick={addItem} className="rounded-xl flex-shrink-0">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Item List */}
        {items.length > 0 && (
          <div className="glass-strong rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                {mode === "image" ? "Detected Items" : "Food Items"}
                <span className="text-xs text-muted-foreground font-normal ml-2">({items.length} items)</span>
              </h3>
              {mode === "image" && <span className="text-xs text-primary">Tap ✏️ to edit</span>}
            </div>
            <div className="rounded-xl border border-border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Food Item</TableHead>
                    <TableHead className="text-xs text-right">Quantity (g)</TableHead>
                    <TableHead className="text-xs w-20"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item, i) => (
                    <TableRow key={i}>
                      {editIdx === i ? (
                        <>
                          <TableCell><Input value={editName} onChange={(e) => setEditName(e.target.value)} className="h-8 text-sm rounded-lg" /></TableCell>
                          <TableCell className="text-right"><Input type="number" value={editQty} onChange={(e) => setEditQty(e.target.value)} className="h-8 text-sm rounded-lg w-20 ml-auto" /></TableCell>
                          <TableCell className="text-right"><Button size="sm" variant="ghost" onClick={() => saveEdit(i)} className="h-7 text-xs text-primary">Save</Button></TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell className="font-medium text-sm capitalize">{item.name}</TableCell>
                          <TableCell className="text-right text-sm">{item.quantity}g</TableCell>
                          <TableCell className="text-right flex items-center justify-end gap-1">
                            <button onClick={() => startEdit(i)} className="text-muted-foreground hover:text-primary transition-colors"><Pencil className="w-3.5 h-3.5" /></button>
                            <button onClick={() => removeItem(i)} className="text-muted-foreground hover:text-destructive transition-colors"><X className="w-4 h-4" /></button>
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Extra item input in image mode */}
            {mode === "image" && (
              <div className="flex gap-2">
                <Input placeholder="Add more items…" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key==="Enter"&&addItem()} className="flex-1 rounded-xl" />
                <Input type="number" placeholder="Grams" value={newQty} onChange={(e) => setNewQty(e.target.value)} onKeyDown={(e) => e.key==="Enter"&&addItem()} className="w-24 rounded-xl" />
                <Button variant="outline" size="icon" onClick={addItem} className="rounded-xl flex-shrink-0"><Plus className="w-4 h-4" /></Button>
              </div>
            )}
          </div>
        )}

        <Button onClick={analyzeMeal} disabled={analyzing || items.length === 0} className="w-full rounded-xl gradient-primary border-0 h-12">
          {analyzing
            ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Analyzing with AI…</>
            : <><Sparkles className="w-4 h-4 mr-2" /> Analyze Meal</>}
        </Button>
      </motion.div>
    </AppLayout>
  );
}