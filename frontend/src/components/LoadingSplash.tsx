import logoFull from "@/assets/logo-dark.png";

interface Props {
  message?: string;
}

export function LoadingSplash({ message = "Loading aiPHeed…" }: Props) {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden" style={{ background: "#0D0D0F" }}>
      {/* Blurred backdrop */}
      <div
        className="absolute inset-0 opacity-30 blur-2xl"
        style={{
          background:
            "radial-gradient(ellipse at 30% 40%, hsl(35 90% 55% / 0.25), transparent 50%), radial-gradient(ellipse at 70% 60%, hsl(0 72% 50% / 0.2), transparent 50%)",
        }}
      />
      <div className="relative flex flex-col items-center gap-6 px-6">
        <img
          src={logoFull}
          alt="aiPHeed — Food Insecurity Forecasting"
          className="h-20 sm:h-24 w-auto object-contain animate-fade-in drop-shadow-[0_0_30px_rgba(232,69,60,0.35)]"
        />
        <p className="text-[11px] text-white/70 tracking-wide">{message}</p>
        {/* Thin progress bar */}
        <div className="w-48 h-[2px] bg-white/10 overflow-hidden rounded-full">
          <div
            className="h-full bg-primary"
            style={{
              width: "40%",
              animation: "splash-progress 1.6s ease-in-out infinite",
            }}
          />
        </div>
        <style>{`
          @keyframes splash-progress {
            0% { transform: translateX(-120%); }
            100% { transform: translateX(320%); }
          }
        `}</style>
      </div>
    </div>
  );
}
