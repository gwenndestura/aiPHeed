// src/lib/loadError.ts
// ---------------------
// Telling "the data could not be fetched" apart from "the server answered".
//
// A 404 from the dashboard API is a real answer (forecast_not_found,
// forecast_withheld): nothing was published for that quarter, and the panels
// already say so. Everything else -- network failure, timeout, 5xx -- means we
// do not know the value, and showing 0.00 / "Low risk" in its place would read
// as an all-clear.

import { ApiError } from "./api";

export const LOAD_ERROR_MESSAGE = "Data could not be loaded. Try again later.";

export function isLoadFailure(error: unknown): boolean {
  if (!error) return false;
  return !(error instanceof ApiError && error.status === 404);
}
