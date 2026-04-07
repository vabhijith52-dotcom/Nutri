// src/lib/nutrition-engine.ts
// Local flag display logic — used ONLY for rendering flags that came from the backend.
// The backend ScoringEngine does all clinical scoring; this file just defines the types
// and helpers used to colour/label them in the UI.

export interface NutritionData {
  calories: number;
  carbs:    number;
  sugar:    number;
  protein:  number;
  fat:      number;
  sodium:   number;
  fiber:    number;
}

export interface HealthProfile {
  conditions:     string[];
  hba1c?:         number;
  fasting_sugar?: number;
  weight?:        number;
  bmi?:           number;
  systolic_bp?:   number;
  diastolic_bp?:  number;
  ldl?:           number;
  hdl?:           number;
  triglycerides?: number;
  age?:           number;
  gender?:        string;
}

export interface FlagResult {
  label:       string;
  severity:    "low" | "medium" | "high";
  message:     string;
  category:    string;
  moderation?: string;
}

export function getRiskColor(score: number): string {
  if (score <= 35) return "text-success";
  if (score <= 65) return "text-warning";
  return "text-destructive";
}

export function getRiskLabel(score: number): string {
  if (score <= 35) return "Low Risk";
  if (score <= 65) return "Moderate Risk";
  return "High Risk";
}

export function getRiskBgColor(score: number): string {
  if (score <= 35) return "bg-success/10";
  if (score <= 65) return "bg-warning/10";
  return "bg-destructive/10";
}