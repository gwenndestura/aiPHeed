// src/lib/demoMode.ts
// -------------------
// "Scenario / Demo mode" for presentations (E178, docs/e178/PROTOCOL.md).
// Off by default, remembered only for this browser session, and offered only
// in the administrator area (admin and demo accounts). Public pages never read
// it, and the scenarios it shows come from their own endpoint
// (/api/v1/demo/scenarios), never from the real outlook.

import { useCallback, useEffect, useState } from "react";
import { readStorage, removeStorage, writeStorage } from "@/lib/storage";

export const DEMO_MODE_KEY = "aipheed_scenario_demo";
export const DEMO_MODE_EVENT = "aipheed:scenario-demo";
export const SYNTHETIC_LABEL = "SYNTHETIC – FOR DEMONSTRATION";

export function readDemoMode(): boolean {
  return readStorage(DEMO_MODE_KEY, "session") === "on";
}

export function writeDemoMode(on: boolean): void {
  if (on) writeStorage(DEMO_MODE_KEY, "on", "session");
  else removeStorage(DEMO_MODE_KEY, "session");
  window.dispatchEvent(new CustomEvent(DEMO_MODE_EVENT, { detail: { on } }));
}

/** The toggle's state, shared by every component that shows it. */
export function useDemoMode(): [boolean, (on: boolean) => void] {
  const [on, setOn] = useState(readDemoMode);
  useEffect(() => {
    const sync = () => setOn(readDemoMode());
    window.addEventListener(DEMO_MODE_EVENT, sync);
    return () => window.removeEventListener(DEMO_MODE_EVENT, sync);
  }, []);
  const set = useCallback((v: boolean) => {
    writeDemoMode(v);
    setOn(v);
  }, []);
  return [on, set];
}
