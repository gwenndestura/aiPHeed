import { useEffect, useRef, useState } from "react";

export function useCountUp(target: number, duration = 800, decimals = 0) {
  const [v, setV] = useState(target);
  const fromRef = useRef(target);
  const startedRef = useRef(false);

  useEffect(() => {
    const from = startedRef.current ? v : 0;
    fromRef.current = from;
    startedRef.current = true;
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(from + (target - from) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  const factor = Math.pow(10, decimals);
  return Math.round(v * factor) / factor;
}
