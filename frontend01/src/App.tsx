// src/App.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster }           from "@/components/ui/sonner";
import { TooltipProvider }   from "@/components/ui/tooltip";
import { useAuth }     from "@/hooks/useAuth";
import { useProfile }  from "@/hooks/useProfile";
import Auth             from "./pages/Auth";
import Onboarding       from "./pages/Onboarding";
import Dashboard        from "./pages/Dashboard";
import MealInput        from "./pages/MealInput";
import AnalysisDashboard from "./pages/AnalysisDashboard";
import HealthAnalysis   from "./pages/HealthAnalysis";
import AIReport         from "./pages/AIReport";
import DietPlan         from "./pages/DietPlan";
import ProgressTracker  from "./pages/ProgressTracker";
import NotFound         from "./pages/NotFound";
import NutriCoach       from "./components/NutriCoach";

const queryClient = new QueryClient();

function AppRoutes() {
  const { user, loading }               = useAuth();
  const { profile, isLoading: profLoad } = useProfile();

  // Show spinner while auth resolves
  if (loading || (user && profLoad)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-8 h-8 rounded-lg gradient-primary animate-pulse-soft" />
      </div>
    );
  }

  // Not logged in — show Auth page for every route
  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Auth />} />
      </Routes>
    );
  }

  // Logged in but onboarding not done → force to onboarding
  if (profile && !profile.onboarding_complete) {
    return (
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="*"           element={<Navigate to="/onboarding" replace />} />
      </Routes>
    );
  }

  // Fully onboarded → normal app
  return (
    <Routes>
      <Route path="/"                     element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard"            element={<Dashboard />} />
      <Route path="/meal"                 element={<MealInput />} />
      <Route path="/analysis/:id"         element={<AnalysisDashboard />} />
      <Route path="/health-analysis/:id"  element={<HealthAnalysis />} />
      <Route path="/ai-report/:id"        element={<AIReport />} />
      <Route path="/diet-plan"            element={<DietPlan />} />
      <Route path="/progress"             element={<ProgressTracker />} />
      <Route path="/onboarding"           element={<Onboarding />} />
      <Route path="*"                     element={<NotFound />} />
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppRoutes />
        <NutriCoach />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;