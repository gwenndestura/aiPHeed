# E155 protocol: does broader news (SunStar) help the E151 model?

Written before the run, at the owner's request. **One run; `app/e155/test.py` refuses a second.**

## Evidence status

Another look at the same 72 rows, which have been read and studied before. **Retrospective whatever the result.** GDELT is not included: only 18 of about 546 series had been collected, because of throttling.

## Inputs added to the E151 required model (GNT)

For each province and issue quarter, from SunStar headlines published in the 3 months before the issue date (no release delay; headlines are public on their date):

* the share of headlines on prices, shortage, farming, jobs, disasters and aid (seed phrases fixed in `app/e155/audit.py` before this test);
* each share minus its mean over the province's previous 8 quarters;
* the number of headlines.

SunStar has editions for 13 areas only, mapped to provinces in `audit.EDITION`. **Other provinces get missing values, which LightGBM handles. CALABARZON has no edition, so these inputs say nothing about the five provinces directly.**

## Comparison, same rows, same settings

* **GNT:** E151 required model.
* **GNT+SUN:** the same model plus the SunStar inputs. Res2 settings unchanged, nothing tuned.

## Fixed read-out

Accuracy, recall, Brier, and GNT+SUN minus GNT Brier with a region-bootstrap 95 % interval, on all 72 rows and on rows in provinces with a SunStar edition. **SunStar is said to help only if the all-row interval is below 0 and accuracy does not fall.** Otherwise it is reported as no measurable gain.
