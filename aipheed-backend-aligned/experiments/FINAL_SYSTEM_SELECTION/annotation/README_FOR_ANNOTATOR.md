# Instructions for the second news annotator (a person)

You will label 126 news headlines about food security in the Philippines. Labelling them independently is what turns the current single-reviewer result into a real inter-annotator agreement score.

1. **Read the guide first.** Read `NEWS_ANNOTATION_GUIDE.md` in full before you start. It defines the four labels: TYPE, RELEVANT, GEO and EVIDENCE.
2. **Make your working file.** Copy `news_review_human_TEMPLATE.csv` to `news_review_human.csv` in this folder.
3. **Label every row.** For each row, fill in:
   - `type`: one of DIRECT, PRICE, SUPPLY, DISASTER, LIVELIHOOD, ASSIST, OTHER;
   - `relevant`: Y or N;
   - `geo`: one of CALA, PH, OTHER_PH, FOREIGN;
   - `evidence`: one of EVENT, FORECAST, GENERAL;
   - `note` (optional): anything you were unsure about.
4. **Work from the headline only.** Use the headline, date and outlet. Do not open the article; the system also sees headlines only.
5. **Stay blind.** Do not open any other file in `DASHBOARD_SELECTION/out/` or `FINAL_SYSTEM_SELECTION/out/`. Those files hold the system's labels and the first reviewer's labels, and seeing them would bias your answers.
6. **Return the file.** Save `news_review_human.csv` in this folder and hand it back.

**Scoring** (done afterwards, from `backend/`):

```
python ../aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/runner/score_news.py
```

This reports:
- Cohen's κ between your labels and the first reviewer's labels;
- the news classifier's precision, recall and F1 under your labels.
