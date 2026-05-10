import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { MessageSquare, Send } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { PROVINCE_LIST, MUNICIPALITIES_BY_PROVINCE, type ProvinceName } from "@/data/calabarzonProvinces";

const SUS_QUESTIONS = [
  "I think that I would like to use aiPHeed frequently.",
  "I found aiPHeed unnecessarily complex.",
  "I thought aiPHeed was easy to use.",
  "I think I would need support to use aiPHeed.",
  "I found the various functions in aiPHeed well integrated.",
  "I thought there was too much inconsistency in aiPHeed.",
  "I would imagine most people would learn to use aiPHeed quickly.",
  "I found aiPHeed very cumbersome to use.",
  "I felt very confident using aiPHeed.",
  "I needed to learn a lot of things before I could use aiPHeed.",
];

const LIKERT_LABELS = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"];

// SUS scoring: odd index (1,3,5,...) = (resp - 1); even index (2,4,6,...) = (5 - resp)
// Standard 10-question SUS, scaled by 2.5 → 0-100
function scoreSUS(answers: Record<number, number>) {
  let sum = 0;
  let answered = 0;
  for (let i = 0; i < SUS_QUESTIONS.length; i++) {
    const r = answers[i];
    if (!r) continue;
    answered++;
    sum += i % 2 === 0 ? r - 1 : 5 - r;
  }
  if (!answered) return 0;
  return Math.round((sum / answered) * SUS_QUESTIONS.length * 2.5);
}

interface Demographics {
  fullName: string;
  email: string;
  agency: string;
  designation: string;
  age: string;
  sex: string;
  clientType: string;
  province: string;
  municipality: string;
}

const DEFAULT_DEMOGRAPHICS: Demographics = {
  fullName: "", email: "", agency: "", designation: "",
  age: "", sex: "", clientType: "", province: "", municipality: "",
};

export interface FeedbackSubmission {
  id: string;
  date: string;
  demographics: Demographics;
  answers: Record<number, number>;
  liked: string;
  improvements: string;
  comment: string; // legacy alias
  score: number;
}

export const FEEDBACK_STORAGE_KEY = "aipheed_feedback_v2";

export function loadFeedback(): FeedbackSubmission[] {
  try {
    return JSON.parse(localStorage.getItem(FEEDBACK_STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function FeedbackModal() {
  const [demo, setDemo] = useState<Demographics>(DEFAULT_DEMOGRAPHICS);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [liked, setLiked] = useState("");
  const [improvements, setImprovements] = useState("");
  const [open, setOpen] = useState(false);

  const submit = () => {
    if (Object.keys(answers).length < SUS_QUESTIONS.length) {
      toast({
        title: "Please complete all 10 SUS questions",
        description: `${Object.keys(answers).length} of ${SUS_QUESTIONS.length} answered.`,
        variant: "destructive",
      });
      return;
    }
    const score = scoreSUS(answers);
    const entry: FeedbackSubmission = {
      id: `f${Date.now()}`,
      date: new Date().toISOString().slice(0, 10),
      demographics: demo,
      answers,
      liked,
      improvements,
      comment: [liked, improvements].filter(Boolean).join(" — "),
      score,
    };
    const all = loadFeedback();
    all.unshift(entry);
    localStorage.setItem(FEEDBACK_STORAGE_KEY, JSON.stringify(all));

    toast({ title: "Thank you for your feedback!", description: `SUS ${score}/100 recorded.` });
    setAnswers({});
    setLiked("");
    setImprovements("");
    setDemo(DEFAULT_DEMOGRAPHICS);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
        <MessageSquare className="h-3 w-3" />
        Send Feedback
      </DialogTrigger>
      <DialogContent className="z-[1200] max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-sm">aiPHeed System Usability Feedback</DialogTitle>
          <DialogDescription className="text-[11px]">
            Please fill in all fields and select the box that best reflects your perception. The scale ranges from strongly disagree (1) to strongly agree (5). None of the fields are required.
          </DialogDescription>
        </DialogHeader>

        {/* Demographics */}
        <section className="space-y-3 mt-2 pb-3 border-b border-border/40">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Demographics</h3>
          <div className="grid grid-cols-2 gap-2">
            <Input label="Full Name" value={demo.fullName} onChange={(v) => setDemo({ ...demo, fullName: v })} />
            <Input label="Email Address (optional)" value={demo.email} onChange={(v) => setDemo({ ...demo, email: v })} />
            <Input label="Agency Name" value={demo.agency} onChange={(v) => setDemo({ ...demo, agency: v })} />
            <Input label="Designation" value={demo.designation} onChange={(v) => setDemo({ ...demo, designation: v })} />
          </div>
          <RadioGroup label="Age" options={["≤25", "26-35", "36-45", "46-60", ">60"]} value={demo.age} onChange={(v) => setDemo({ ...demo, age: v })} />
          <RadioGroup label="Sex" options={["Male", "Female"]} value={demo.sex} onChange={(v) => setDemo({ ...demo, sex: v })} />
          <RadioGroup label="Client Type" options={["Citizen", "Business", "Government", "Others"]} value={demo.clientType} onChange={(v) => setDemo({ ...demo, clientType: v })} />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">Province</label>
              <select
                value={demo.province}
                onChange={(e) => setDemo({ ...demo, province: e.target.value, municipality: "" })}
                className="mt-1 w-full h-9 px-2 text-[12px] bg-secondary/50 border border-border/40 rounded-md focus:outline-none focus:border-primary/50"
              >
                <option value="">Select province…</option>
                {PROVINCE_LIST.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">Municipality / City</label>
              <select
                value={demo.municipality}
                onChange={(e) => setDemo({ ...demo, municipality: e.target.value })}
                disabled={!demo.province}
                className="mt-1 w-full h-9 px-2 text-[12px] bg-secondary/50 border border-border/40 rounded-md focus:outline-none focus:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">{demo.province ? "Select…" : "Pick a province first"}</option>
                {demo.province &&
                  MUNICIPALITIES_BY_PROVINCE[demo.province as ProvinceName]?.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
              </select>
            </div>
          </div>
        </section>

        {/* SUS questions */}
        <section className="space-y-4 mt-2">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">System Usability Scale</h3>
          {SUS_QUESTIONS.map((q, i) => (
            <div key={i} className="space-y-1.5">
              <p className="text-[11px] font-medium leading-snug">
                <span className="text-muted-foreground mr-1.5">{i + 1}.</span>{q}
              </p>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((v) => {
                  const active = answers[i] === v;
                  return (
                    <button
                      key={v}
                      onClick={() => setAnswers((p) => ({ ...p, [i]: v }))}
                      title={LIKERT_LABELS[v - 1]}
                      className={`flex-1 h-8 rounded-md text-[11px] font-bold transition-all border ${
                        active
                          ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/30"
                          : "border-border/40 bg-secondary/30 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                      }`}
                    >
                      {v}
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-between text-[8px] text-muted-foreground/70 px-0.5">
                <span>Strongly disagree</span>
                <span>Strongly agree</span>
              </div>
            </div>
          ))}
        </section>

        {/* Open ended */}
        <section className="pt-3 border-t border-border/40 space-y-3">
          <div>
            <label className="text-[11px] font-medium block mb-1">What did you like most about aiPHeed?</label>
            <textarea
              value={liked}
              onChange={(e) => setLiked(e.target.value)}
              rows={2}
              className="w-full text-[11px] p-2 rounded-md bg-secondary/40 border border-border/40 focus:outline-none focus:border-primary/50 resize-none"
            />
          </div>
          <div>
            <label className="text-[11px] font-medium block mb-1">What improvements would you suggest?</label>
            <textarea
              value={improvements}
              onChange={(e) => setImprovements(e.target.value)}
              rows={2}
              className="w-full text-[11px] p-2 rounded-md bg-secondary/40 border border-border/40 focus:outline-none focus:border-primary/50 resize-none"
            />
          </div>
        </section>

        <DialogFooter>
          <button
            onClick={submit}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-[11px] font-semibold hover:bg-primary/90 transition-colors"
          >
            <Send className="h-3 w-3" />
            Submit Feedback
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-2 text-[12px] bg-secondary/50 border border-border/40 rounded-md focus:outline-none focus:border-primary/50"
      />
    </div>
  );
}

function RadioGroup({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold mb-1">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button
            key={o}
            onClick={() => onChange(o)}
            className={`px-3 py-1.5 rounded-md text-[10px] font-semibold border transition-colors ${
              value === o
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border/50 hover:bg-secondary/60"
            }`}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  );
}

export { SUS_QUESTIONS };
