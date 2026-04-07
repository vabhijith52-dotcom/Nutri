// src/pages/Auth.tsx
import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input }  from "@/components/ui/input";
import { Label }  from "@/components/ui/label";
import { Leaf }   from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { toast }   from "@/hooks/use-toast";

export default function AuthPage() {
  const [isLogin,  setIsLogin]  = useState(true);
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [name,     setName]     = useState("");
  const [loading,  setLoading]  = useState(false);
  const { signIn, signUp } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) {
        const { error } = await signIn(email, password);
        if (error) throw error;
      } else {
        const { error } = await signUp(email, password, name);
        if (error) throw error;
        toast({ title: "Account created!", description: "Setting up your profile…" });
      }
    } catch (err: unknown) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full gradient-primary opacity-10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full gradient-cool opacity-10 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
        className="glass-strong rounded-2xl p-8 w-full max-w-md space-y-6 relative z-10"
      >
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Leaf className="w-6 h-6 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-bold">NutriSense</h1>
          </div>
          <p className="text-muted-foreground text-sm">AI Metabolic Health Assistant</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name" placeholder="Your name" value={name}
                onChange={(e) => setName(e.target.value)} className="rounded-xl"
              />
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email" type="email" placeholder="you@example.com" value={email}
              onChange={(e) => setEmail(e.target.value)} required className="rounded-xl"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password" type="password" placeholder="••••••••" value={password}
              onChange={(e) => setPassword(e.target.value)} required minLength={6} className="rounded-xl"
            />
          </div>
          <Button type="submit" className="w-full rounded-xl gradient-primary border-0" disabled={loading}>
            {loading ? "Please wait…" : isLogin ? "Sign In" : "Create Account"}
          </Button>
        </form>

        <div className="text-center">
          <button type="button" onClick={() => setIsLogin(!isLogin)}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>

        <p className="text-xs text-center text-muted-foreground">
          NutriSense supports dietary awareness and lifestyle improvements. It does not provide medical advice or replace your doctor.
        </p>
      </motion.div>
    </div>
  );
}