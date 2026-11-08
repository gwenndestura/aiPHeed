"""Direct food-insecurity labels from official public sources (DOST-FNRI, PSA), kept apart from every predictor.

    hfias      official HFIAS scoring and categories (FNRI 2015 report, following Coates et al. 2007, FANTA v3),
               weighted design-based prevalence with standard errors; ready for FNRI public-use files
    published  CALABARZON estimates extracted from the downloaded FNRI reports and PSA OpenSTAT (2015 HFIAS by
               region and province; FIES 2019/2021 national and 2023 regional)
    manifest   source and download manifest, including what could NOT be acquired and why

Files live in backend/data/fi_labels/raw (unchanged originals) and backend/data/fi_labels/clean (derived).
HFIAS and FIES are different instruments and are never pooled.
"""
