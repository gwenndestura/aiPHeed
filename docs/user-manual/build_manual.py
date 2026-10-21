"""Builds docs/user-manual/aiPHeed_User_Manual.docx from the screenshots in img/.

Run from the repository root:  python docs/user-manual/build_manual.py
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

HERE = Path(__file__).parent
IMG = HERE / "img"
CROPS = HERE / "img" / "crops"
LOGO = HERE.parent.parent / "frontend" / "src" / "assets" / "logo-light.png"
OUT = HERE / "aiPHeed_User_Manual.docx"
APP_LINK = "https://aipheed-frontend.vercel.app"
FONT = "Arial"
ORANGE = RGBColor(0xE8, 0x8A, 0x10)


def crop(name, box, out):
    """Cuts a region (in screenshot pixels) out of a full-page screenshot."""
    CROPS.mkdir(exist_ok=True)
    Image.open(IMG / name).crop(box).save(CROPS / out)
    return CROPS / out


def field(run, code):
    """Inserts a Word field (PAGE, TOC ...) that Word fills in when it opens or prints the file."""
    for tag, text in (("begin", None), (None, code), ("separate", None), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


doc = Document()
for s in doc.styles:
    if s.type == 1:  # paragraph styles
        s.font.name = FONT
        s.element.rPr.rFonts.set(qn("w:eastAsia"), FONT) if s.element.rPr is not None and s.element.rPr.rFonts is not None else None
normal = doc.styles["Normal"]
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15
for lvl, size in ((1, 14), (2, 12), (3, 11)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name, h.font.size, h.font.bold = FONT, Pt(size), True
    h.font.color.rgb = RGBColor(0, 0, 0)
    h.paragraph_format.space_before = Pt(12 if lvl == 1 else 8)
    h.paragraph_format.space_after = Pt(4)
    rpr = h.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(a), None)

sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)  # Letter, like the reference
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Cm(2.54))
sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.2)
sec.different_first_page_header_footer = True

# Header logo (top right) and page number (bottom right) on every page but the cover.
hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hp.add_run().add_picture(str(LOGO), width=Cm(3.6))
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
field(fp.add_run(), "PAGE")


def p(text="", bold_prefix=None, style=None, level=0):
    para = doc.add_paragraph(style=style)
    if level:
        para.paragraph_format.left_indent = Cm(1.27 * (level + 1))
    if bold_prefix:
        para.add_run(bold_prefix).bold = True
    # **word** marks a button or label name in bold, as the reference guide does.
    parts = text.split("**")
    for i, part in enumerate(parts):
        if part:
            para.add_run(part).bold = i % 2 == 1
    # A lead-in line ("... the following options:") stays on the page with its list.
    para.paragraph_format.keep_with_next = text.endswith(":")
    return para


def bullet(text, bold_prefix=None, level=0):
    para = p(text, bold_prefix, style="List Bullet 2" if level else "List Bullet")
    return para


def image(path, width_cm=16.0, caption=None):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.add_run().add_picture(str(path), width=Cm(width_cm))
    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(caption)
        r.italic, r.font.size = True, Pt(9)


# ---- Cover -------------------------------------------------------------------
for _ in range(9):
    doc.add_paragraph()
cp = doc.add_paragraph()
cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
cp.add_run().add_picture(str(LOGO), width=Cm(9))
tp = doc.add_paragraph()
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = tp.add_run("User Guide")
tr.bold, tr.font.size = True, Pt(28)
sp = doc.add_paragraph()
sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sp.add_run("Food Insecurity Risk Forecasting System for Region IV-A (CALABARZON)")
sr.font.size = Pt(12)
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ---- Table of contents ---------------------------------------------------------
toc_title = doc.add_paragraph()
r = toc_title.add_run("Table of Contents")
r.bold, r.font.size = True, Pt(14)
field(doc.add_paragraph().add_run(), 'TOC \\o "1-3" \\h \\z \\u')
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ---- 1. Introduction -------------------------------------------------------------
doc.add_heading("1. Introduction", 1)
p("The purpose of this manual is to provide simple, step-by-step instructions for aiPHeed, a "
  "web-based geospatial system that estimates the food insecurity risk of the five CALABARZON "
  "provinces (Batangas, Cavite, Laguna, Quezon and Rizal) one quarter ahead. It is intended for "
  "planning staff of the Department of Agriculture Regional Field Office IV-A.")
p("aiPHeed shows a risk score from 0 to 1 for each province. A score of 0.50 or higher is shown "
  "as **High risk**. The score is a model estimate, not an official statistic.")

# ---- 2. Accessing the System ---------------------------------------------------
doc.add_heading("2. Accessing the System", 1)
p("You may access the aiPHeed web application directly through the following link:")
bullet(APP_LINK, "Application Link: ")
p("The app works best on a desktop or laptop computer. It also works on phones and tablets, "
  "where the panels move into a sheet at the bottom of the screen.")
p("On the home page, click **Explore the map** to open the dashboard, or **How it works** to read "
  "how the forecasts are made.")
image(IMG / "01-landing.png")

# ---- 3. Overview & Navigation --------------------------------------------------
doc.add_heading("3. Overview & Navigation", 1)
doc.add_heading("3.1 Main Menu", 2)
p("The top bar lets you access all the main features of the system:")
bullet("View the risk map of CALABARZON and the details of each province.", "Mapping: ")
bullet("View all provinces in a table that you can filter and export.", "Data: ")
bullet("Draw trend and contribution charts that you can download.", "Visualization: ")
p("The menu button (**☰**) in the upper right corner has the following options:")
bullet("Switch between dark and light mode.", "Dark mode: ")
bullet("Show or hide province labels, municipality boundaries and risk numbers on the map.", "Display preferences: ")
bullet("Replay the guided tour of the page you are on.", "Take the tour: ")
bullet("Sign-in for Department of Agriculture CALABARZON staff only (see Section 5).", "Admin sign in: ")
image(IMG / "11-menu.png", caption="The menu opened from the upper right corner")

doc.add_heading("3.2 Guided Tour", 2)
p("The first time you open the Mapping, Data or Visualization page, a short guided tour explains "
  "each part of the page.")
bullet("Click **Next** to go to the next step, or **Skip** to close the tour.")
bullet("You can replay the tour any time from the menu (**Take the tour**).")
image(IMG / "02-tour.png")

doc.add_heading("3.3 Reading the Colours", 2)
p("Each province on the map is coloured by its forecast risk level:")
bullet("a risk score of 0.50 or higher.", "Red – High risk: ")
bullet("a risk score below 0.50.", "Yellow – Low risk: ")
bullet("no forecast for that province this quarter (for example, a forecast withheld after review).", "Grey – No forecast: ")
p("An **Active alert** label means the score is high enough to call for early action.")

# ---- 4. Main Features ----------------------------------------------------------
doc.add_heading("4. Main Features", 1)
doc.add_heading("4.1 Mapping Tab", 2)
p("The Mapping tab is the main dashboard. It shows the CALABARZON map in the middle, a summary "
  "panel on the left and the reasons behind the risk on the right.")
image(IMG / "03-map.png")

doc.add_heading("4.1.1 Regional Summary", 3)
p("When no province is selected, the left panel shows the whole region:")
bullet("the average score of the five provinces.", "Regional average risk level: ")
bullet("the number of provinces that are High risk, Low risk or have limited data.", "High risk / Low risk / Limited data: ")
bullet("the factors that raise the region's risk, such as employment, climate or prices.", "Why is this province at risk?: ")
bullet("the provinces ordered from highest to lowest risk.", "Province ranking: ")

doc.add_heading("4.1.2 Province Details", 3)
bullet("Click a province on the map (or in the Province ranking) to open its details.")
bullet("The left panel shows its **Risk level score**, **Quarter-on-quarter change**, **Population** "
       "and **Trigger composition** (the share of each factor in the risk).")
bullet("**Cities and municipalities** lists every city and municipality in the province, ranked by "
       "priority. These are relative priorities based on poverty and population density, not "
       "separate forecasts for each city or municipality.")
bullet("The right panel lists the **Factors pushing risk up**, the **Factors pulling risk down**, and "
       "data **Not part of this forecast** (data that was not yet published).")
bullet("Click **Back to CALABARZON** to return to the whole region.")
image(IMG / "04-province.png")

doc.add_heading("4.1.3 News Articles Analyzed", 3)
bullet("Click **News articles analyzed** in the right panel to open it.")
bullet("It shows how many news articles were analyzed for the province and the share of each topic, "
       "such as climate stress or fish kill.")
bullet("The list below shows the news headlines the forecast was built from. Click a headline to open it.")
image(crop("06-news.png", (1655, 905, 2160, 1205), "06-news-panel.png"), 9.0)

doc.add_heading("4.1.4 Search", 3)
bullet("Type the name of a province, city or municipality in the search box at the top of the map.")
bullet("Click a result (or press Enter) to zoom in on that place and open its details.")
image(IMG / "08-search.png", 11.0)
image(IMG / "09-municipality.png", caption="A city selected from the search (Lucena, Quezon)")

doc.add_heading("4.1.5 Choosing a Quarter", 3)
bullet("Use the timeline at the bottom of the map to pick a quarter. The solid line marks observed "
       "quarters, the dashed line marks forecasts, and **Today** marks the current quarter.")
bullet("Click **View history** to see the forecasts of every quarter in a list.")
image(IMG / "07-timeline.png", 13.0)
image(IMG / "10-history.png")

doc.add_heading("4.2 Data Tab", 2)
p("The Data tab lists every province in a table for the chosen quarter.")
bullet("Filter the table by province, risk level or quarter, or type a province name in the search box.")
bullet("Click a column heading to sort the table. Click it again to reverse the order.")
bullet("Click a row to open that province on the map.")
bullet("Click **Export CSV** to download the rows shown as a file for a spreadsheet.")
image(IMG / "14-data.png")

doc.add_heading("4.3 Visualization Tab", 2)
p("The Visualization tab draws charts that you can download for reports.")
doc.add_heading("4.3.1 Province Risk Level Trend", 3)
bullet("Pick a province (or all five), a city or municipality, and the range of quarters (**From** and **To**).")
bullet("Click **Generate Chart** to draw the chart, or **Clear Filters** to start again.")
bullet("Each line is a risk score from 0 to 1. A line at or above the **High risk** line is high risk.")
bullet("Click **Download PNG** to save the chart as an image, or **Download PDF** for a printable report.")
image(IMG / "15-viz-trend.png")
doc.add_heading("4.3.2 Feature Contribution Breakdown", 3)
bullet("Pick a province and a quarter, then click **Generate Chart**.")
bullet("The chart shows how much each group of factors, such as employment, climate or prices, "
       "added to the province's risk in that quarter.")
image(IMG / "16-viz-features.png")

doc.add_heading("4.4 About & Methodology and Feedback", 2)
bullet("Click **About & Methodology** (bottom of the left panel) to read how the forecasts are made, "
       "the data sources used and their limits.")
bullet("Click **Send Feedback** to answer a short usability survey about the system. Fill in the "
       "details, rate each statement from 1 to 5, then submit.")
image(IMG / "12-about.png")
image(IMG / "13-feedback.png")

# ---- 5. Admin Access -------------------------------------------------------------
doc.add_heading("5. Admin Access (DA CALABARZON Staff)", 1)
p("Administrators review each forecast before it is published. Only email addresses ending in "
  "**@calabarzon.da.gov.ph** can have an administrator account.")
bullet("Open the menu (**☰**) and click **Admin sign in**, then enter your email and password.")
bullet("New users click **Request access**. An existing administrator must approve the account before you can sign in.")
bullet("Click **Forgot password?** to receive a password reset link by email.")
image(IMG / "17-login.png", 13.0)

doc.add_heading("5.1 Admin Dashboard", 2)
p("After signing in, an **ADMIN** label appears beside the logo and the top bar adds two pages, "
  "**Review** and **Feedback**:")
bullet("the same map as the public dashboard, with all its features (see Section 4.1).", "Mapping, Data and Visualization: ")
bullet("a red bar at the top warns when a province is forecast as high risk and how many forecasts "
       "are waiting for review. Click **Review** on the bar to open them.", "Early warning: ")
image(IMG / "18-admin-map.png")

doc.add_heading("5.2 Reviewing Forecasts", 2)
p("Every province forecast is shown to the public only after it is reviewed.")
bullet("Click **Review** in the top bar. The **Review Queue** lists each province forecast with its "
       "risk level, score and status (**Staged**, **Approved** or **Rejected**).")
bullet("Use the **Year** and **Quarter** filters to find a forecast.")
bullet("Click **View Details** to open the risk review of a province.")
image(IMG / "19-admin-review.png")
bullet("The risk review shows the score of each city and municipality and the factors (SHAP driver "
       "contributions) behind the forecast.")
bullet("Click **Approve & Publish** to show the forecast to the public, or **Reject** to withhold it. "
       "**Undo Publishing** takes back an approved forecast.")
image(IMG / "20-admin-review-detail.png")
bullet("When rejecting, choose a **Rejection reason**, add notes if needed, then click **Confirm rejection**. "
       "A rejected province is shown in grey on the public map.")
bullet("The **Rejection Log** tab lists every rejected forecast with its reason and time. Click "
       "**Restore** to send a forecast back for review.")
image(IMG / "21-admin-reject.png")

doc.add_heading("5.3 Feedback", 2)
bullet("Click **Feedback** in the top bar to see the usability survey answers sent by users, with the "
       "number of submissions and the average SUS score.")
bullet("Click **View** on a row to read all the answers of that submission.")
image(IMG / "23-admin-feedback.png")

doc.add_heading("5.4 Accounts", 2)
bullet("Open the menu (**☰**) and click **Accounts**. A number beside it shows how many requests are waiting.")
bullet("Under **Waiting for approval**, click **Approve** or **Reject** on each request for a new "
       "administrator account.")
bullet("Under **Active admins**, click **Deactivate** to switch off an account that is no longer needed.")
image(IMG / "25-admin-accounts.png")
bullet("To leave the admin view, open the menu (**☰**) and click **Sign out**.")

doc.save(OUT)
print("saved", OUT)
