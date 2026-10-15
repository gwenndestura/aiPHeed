// Browser storage that never throws. With storage blocked (some private
// modes, "block all cookies"), reading or writing throws a SecurityError;
// the page then simply forgets the setting instead of failing to load.

type Area = "local" | "session";
const store = (area: Area) => (area === "local" ? window.localStorage : window.sessionStorage);

export function readStorage(key: string, area: Area = "local"): string | null {
  try {
    return store(area).getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string, area: Area = "local"): void {
  try {
    store(area).setItem(key, value);
  } catch {
    // Not remembered; nothing else depends on it.
  }
}

export function removeStorage(key: string, area: Area = "local"): void {
  try {
    store(area).removeItem(key);
  } catch {
    // Nothing to remove.
  }
}
