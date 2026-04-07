// src/components/NutriCoach.tsx
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Utensils, Lightbulb, BarChart3, Leaf } from "lucide-react";
import { Button }   from "@/components/ui/button";
import { Input }    from "@/components/ui/input";
import { useNavigate } from "react-router-dom";
import { botAPI }   from "@/lib/api";
import { useAuth }  from "@/hooks/useAuth";

interface ChatMessage {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  badges?:   Array<{ label: string; type: "safe" | "moderate" | "avoid" | "info" }>;
  timestamp: Date;
}

const QUICK_ACTIONS = [
  { label: "Log Meal",      icon: Utensils,   action: "log_meal"   },
  { label: "Ask Suggestion",icon: Lightbulb,  action: "suggestion" },
  { label: "Today Summary", icon: BarChart3,  action: "summary"    },
];

const badgeStyles: Record<string, string> = {
  safe:     "bg-success/15 text-success border-success/20",
  moderate: "bg-warning/15 text-warning border-warning/20",
  avoid:    "bg-destructive/15 text-destructive border-destructive/20",
  info:     "bg-accent/15 text-accent border-accent/20",
};

function makeMsg(content: string, badges?: ChatMessage["badges"]): ChatMessage {
  return { id: crypto.randomUUID(), role: "assistant", content, badges, timestamp: new Date() };
}

export default function NutriCoach() {
  const [open,     setOpen]     = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    makeMsg(
      "Hi! I'm your **NutriSense AI Coach** 🌱\n\nTell me what you ate, ask if a food is safe, or check today's summary!",
      [{ label: "Welcome", type: "safe" }]
    ),
  ]);
  const [input,    setInput]    = useState("");
  const [typing,   setTyping]   = useState(false);
  const scrollRef  = useRef<HTMLDivElement>(null);
  const navigate   = useNavigate();
  const { user }   = useAuth();

  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, typing]);

  // Load today's saved conversation from backend on open
  useEffect(() => {
    if (!open || !user) return;
    botAPI.getConversation()
      .then((res) => {
        const history: Array<{ role: string; content: string }> = res.data.messages || [];
        if (history.length > 0) {
          setMessages([
            makeMsg("Hi! I'm your **NutriSense AI Coach** 🌱"),
            ...history.map((m) => ({
              id:        crypto.randomUUID(),
              role:      m.role as "user" | "assistant",
              content:   m.content,
              timestamp: new Date(),
            })),
          ]);
        }
      })
      .catch(() => {});
  }, [open, user]);

  const sendMessage = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg) return;

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: msg, timestamp: new Date() },
    ]);
    setInput("");
    setTyping(true);

    try {
      if (!user) {
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            makeMsg(
              "Please **sign in** to use the AI Coach — I need your diet plan and health profile to give personalised advice!",
              [{ label: "Login required", type: "info" }]
            ),
          ]);
          setTyping(false);
        }, 600);
        return;
      }

      const res  = await botAPI.sendMessage(msg);
      const data = res.data;

      const badges: ChatMessage["badges"] = [];
      if (data.food_logged)  badges.push({ label: `${data.food_logged.name} logged`, type: "info" });
      if (data.streak > 0)   badges.push({ label: `🔥 ${data.streak} day streak`,   type: "safe" });

      setMessages((prev) => [
        ...prev,
        {
          id:        crypto.randomUUID(),
          role:      "assistant",
          content:   data.reply,
          badges:    badges.length > 0 ? badges : undefined,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        makeMsg(
          "Sorry, I couldn't connect to the server right now. Make sure the backend is running on port 8000.",
          [{ label: "Error", type: "avoid" }]
        ),
      ]);
    } finally {
      setTyping(false);
    }
  };

  const handleQuickAction = (action: string) => {
    if (action === "log_meal")   { setOpen(false); navigate("/meal"); return; }
    if (action === "suggestion") sendMessage("Give me a healthy food suggestion for today");
    if (action === "summary")    sendMessage("Show today's nutrition summary");
  };

  const renderContent = (content: string) =>
    content.split("\n").map((line, i) => {
      if (!line.trim()) return <br key={i} />;
      const parts = line.split(/\*\*(.+?)\*\*/g);
      return (
        <p key={i} className="text-sm leading-relaxed">
          {parts.map((p, j) =>
            j % 2 === 1 ? <strong key={j} className="font-semibold">{p}</strong> : p
          )}
        </p>
      );
    });

  return (
    <>
      {/* Floating Button */}
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}
            onClick={() => setOpen(true)}
            className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full gradient-primary shadow-lg flex items-center justify-center hover:shadow-xl transition-shadow"
          >
            <MessageCircle className="w-6 h-6 text-primary-foreground" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0,  scale: 1    }}
            exit={{   opacity: 0, y: 20, scale: 0.95  }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed bottom-6 right-6 z-50 w-[360px] max-w-[calc(100vw-3rem)] h-[520px] max-h-[calc(100vh-6rem)] flex flex-col rounded-2xl shadow-2xl border border-border/50 overflow-hidden bg-background"
          >
            {/* Header */}
            <div className="gradient-primary px-4 py-3 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-primary-foreground/20 flex items-center justify-center">
                  <Leaf className="w-4 h-4 text-primary-foreground" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-primary-foreground">NutriSense AI Coach</h3>
                  <p className="text-[10px] text-primary-foreground/70">Your personal diet assistant</p>
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-primary-foreground/70 hover:text-primary-foreground transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl shadow-sm ${
                    msg.role === "user"
                      ? "gradient-primary text-primary-foreground rounded-br-md"
                      : "bg-secondary text-secondary-foreground rounded-bl-md"
                  }`}>
                    <div className="space-y-1">{renderContent(msg.content)}</div>
                    {msg.badges && msg.badges.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {msg.badges.map((b, i) => (
                          <span key={i} className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${badgeStyles[b.type]}`}>
                            {b.label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}

              {typing && (
                <div className="flex justify-start">
                  <div className="bg-secondary rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="w-2 h-2 rounded-full bg-muted-foreground/50"
                          animate={{ y: [0, -6, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="px-3 py-2 border-t border-border/30 flex gap-2 flex-shrink-0">
              {QUICK_ACTIONS.map(({ label, icon: Icon, action }) => (
                <button
                  key={action} onClick={() => handleQuickAction(action)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 text-secondary-foreground transition-colors"
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="text-[11px] font-medium">{label}</span>
                </button>
              ))}
            </div>

            {/* Input */}
            <div className="px-3 pb-3 flex gap-2 flex-shrink-0">
              <Input
                value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Tell me what you ate or ask about your diet…"
                className="flex-1 rounded-xl text-sm h-10"
              />
              <Button
                size="icon" onClick={() => sendMessage()} disabled={!input.trim()}
                className="rounded-xl h-10 w-10 gradient-primary border-0"
              >
                <Send className="w-4 h-4 text-primary-foreground" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}