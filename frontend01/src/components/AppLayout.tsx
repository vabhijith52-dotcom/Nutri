// src/components/AppLayout.tsx
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Leaf, Utensils, BarChart3, Calendar, TrendingUp, LogOut, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/hooks/useAuth";

const NAV_ITEMS = [
  { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { path: "/meal",      label: "Log Meal",  icon: Utensils  },
  { path: "/diet-plan", label: "Diet Plan", icon: Calendar  },
  { path: "/progress",  label: "Progress",  icon: TrendingUp},
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const location     = useLocation();
  const navigate     = useNavigate();
  const { signOut }  = useAuth();
  const [open, setOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  const NavLinks = ({ onClick }: { onClick?: () => void }) => (
    <>
      {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
        <Link
          key={path} to={path} onClick={onClick}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all
            ${location.pathname === path
              ? "gradient-primary text-primary-foreground shadow-md"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </Link>
      ))}
    </>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-64 glass-strong border-r border-border/50 p-4 fixed h-full z-30">
        <div className="flex items-center gap-2 mb-8 px-2">
          <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
            <Leaf className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg">NutriSense</span>
        </div>
        <nav className="flex-1 space-y-1">
          <NavLinks />
        </nav>
        <Button
          variant="ghost" onClick={handleSignOut}
          className="justify-start gap-3 text-muted-foreground rounded-xl"
        >
          <LogOut className="w-4 h-4" /> Sign Out
        </Button>
      </aside>

      {/* Mobile Top Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 glass-strong border-b border-border/50 z-30 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg gradient-primary flex items-center justify-center">
            <Leaf className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-bold">NutriSense</span>
        </div>
        <button onClick={() => setOpen(!open)}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="md:hidden fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
              className="w-64 h-full glass-strong p-4 flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-2 mb-8 px-2 pt-2">
                <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                  <Leaf className="w-5 h-5 text-primary-foreground" />
                </div>
                <span className="font-bold text-lg">NutriSense</span>
              </div>
              <nav className="flex-1 space-y-1">
                <NavLinks onClick={() => setOpen(false)} />
              </nav>
              <Button
                variant="ghost" onClick={handleSignOut}
                className="justify-start gap-3 text-muted-foreground rounded-xl"
              >
                <LogOut className="w-4 h-4" /> Sign Out
              </Button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 md:ml-64 pt-16 md:pt-0">
        <div className="p-4 md:p-8 max-w-5xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}