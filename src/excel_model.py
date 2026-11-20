"""Build excel/retention_economics_model.xlsx: delivery, retention and voucher economics.

Every calculated cell is a formula over the Inputs and Data sheets. Colour code:
blue = typed input or pasted analysis result, black = formula, green = link to another
sheet, yellow fill = assumption to review.
"""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src import config

ARIAL = "Arial"
BLUE, BLACK, GREEN, WHITE = "0000FF", "000000", "008000", "FFFFFF"
HEADER = PatternFill("solid", fgColor="1F3864")
YELLOW = PatternFill("solid", fgColor="FFFF00")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BRL = '"R$"#,##0;("R$"#,##0);"-"'
BRL2 = '"R$"#,##0.00;("R$"#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
PCT2 = '0.00%;(0.00%);"-"'
SRC = "Source: reports/results.json (src/run_pipeline.py), Olist orders up to " + config.CUTOFF


def _c(ws, ref, value, color=BLACK, fmt=None, bold=False, fill=None, note=None, italic=False, size=10):
    cell = ws[ref]
    cell.value = value
    cell.font = Font(name=ARIAL, color=color, bold=bold, italic=italic, size=size)
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    if note:
        cell.comment = Comment(note, "pipeline")
    return cell


def _head(ws, row, labels, col=1):
    for i, text in enumerate(labels):
        cell = ws.cell(row=row, column=col + i, value=text)
        cell.font = Font(name=ARIAL, color=WHITE, bold=True)
        cell.fill = HEADER
        cell.border = BOX
        cell.alignment = Alignment(horizontal="center", wrap_text=True)


def _title(ws, text, sub=None):
    _c(ws, "A1", text, bold=True, size=14)
    if sub:
        _c(ws, "A2", sub, italic=True)


def build(results: dict) -> str:
    b, rv, rp = results["business"], results["review_vs_lateness"], results["repeat_vs_first_delivery"]
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    _title(ws, "Olist retention economics model", "Delivery quality, repeat purchases and second-order vouchers")
    for i, text in enumerate([
        "Purpose: size what better delivery and retention programmes are worth, using measured Olist behaviour.",
        "Inputs sheet: assumptions to review (yellow). Data sheet: figures measured by the Python pipeline (blue).",
        "Delivery: on-time rate needed to reach a target average review score.",
        "Retention: value of higher repeat rates; value if late first orders had been on time.",
        "Voucher: repeat-rate lift a second-order voucher needs to break even, with a sensitivity grid.",
        "All amounts are Brazilian reais (R$). Contribution margin and voucher value are assumptions, not data.",
        "Colour code: blue = input or pasted result; black = formula; green = link to another sheet.",
    ], start=4):
        _c(ws, f"A{i}", text)
    ws.column_dimensions["A"].width = 105

    inp = wb.create_sheet("Inputs")
    _title(inp, "Inputs", "Edit the yellow cells; everything else recalculates.")
    _head(inp, 4, ["Assumption", "Value", "Note"])
    rows = [("Contribution margin on GMV", config.CONTRIBUTION_MARGIN, PCT, "Olist's contribution per R$ of GMV. Assumption."),
            ("Target average review score", config.TARGET_REVIEW, "0.00", "Goal for the delivery scenario."),
            ("Second-order voucher value (R$)", config.VOUCHER_COST, BRL2, "Paid on every repeat order by voucher holders.")]
    for i, (label, value, fmt, note) in enumerate(rows, start=5):
        _c(inp, f"A{i}", label)
        _c(inp, f"B{i}", value, BLUE, fmt, fill=YELLOW)
        _c(inp, f"C{i}", note, italic=True)
    inp.column_dimensions["A"].width, inp.column_dimensions["B"].width, inp.column_dimensions["C"].width = 34, 14, 60
    margin, target, voucher = "Inputs!$B$5", "Inputs!$B$6", "Inputs!$B$7"

    dat = wb.create_sheet("Data")
    _title(dat, "Measured figures (pasted from the analysis)", SRC)
    _head(dat, 4, ["Metric", "Value", "Definition"])
    drows = [
        ("Customers, last 12 months", b["customers_last_12m"], "#,##0", "Unique customers (customer_unique_id) ordering in the last 12 months"),
        ("Orders, last 12 months", b["orders_last_12m"], "#,##0", "Non-canceled orders in the last 12 months"),
        ("Average order value (R$)", b["avg_order_value_last_12m"], BRL2, "Payment value per order, last 12 months"),
        ("Share of deliveries late", rv["late_share"], PCT2, "Delivered after the promised date (delivered, reviewed orders)"),
        ("Average review, on-time orders", rv["mean_review_ontime"], "0.00", "1-5 stars"),
        ("Average review, late orders", rv["mean_review_late"], "0.00", "1-5 stars"),
        ("180-day repeat rate, all first orders", rp["repeat_rate_overall"], PCT2, "Second order within 180 days of the first"),
        ("180-day repeat rate, first order on time", rp["repeat_rate_ontime"], PCT2, "Customers whose first order arrived on time"),
        ("180-day repeat rate, first order late", rp["repeat_rate_late"], PCT2,
         f"p = {rp['z_p_value']:.2f} for the difference, so treat the retention upside as uncertain"),
    ]
    for i, (label, value, fmt, note) in enumerate(drows, start=5):
        _c(dat, f"A{i}", label)
        _c(dat, f"B{i}", value, BLUE, fmt)
        _c(dat, f"C{i}", note, italic=True)
    dat.column_dimensions["A"].width, dat.column_dimensions["B"].width, dat.column_dimensions["C"].width = 40, 14, 80
    D = {k: f"Data!$B${r}" for k, r in zip(["cust", "orders", "aov", "late", "rev_on", "rev_late", "rep", "rep_on",
                                            "rep_late"], range(5, 14))}

    dl = wb.create_sheet("Delivery")
    _title(dl, "Delivery quality and reviews", "What on-time rate reaches the target review score?")
    _head(dl, 4, ["Line", "Value", "How it is calculated"])
    lines = [
        ("Share of deliveries on time", f"=1-{D['late']}", PCT2, GREEN, "1 - late share"),
        ("Current average review (model)", f"=B5*{D['rev_on']}+{D['late']}*{D['rev_late']}", "0.00", BLACK,
         "Mix of on-time and late review averages"),
        ("Target average review", f"={target}", "0.00", GREEN, "Inputs"),
        ("On-time share needed for the target",
         f'=IF({target}>={D["rev_on"]},"Not reachable",({target}-{D["rev_late"]})/({D["rev_on"]}-{D["rev_late"]}))',
         PCT2, BLACK, "(target - late avg) / (on-time avg - late avg); capped by the on-time average"),
        ("Gap in on-time share (pts)", '=IF(ISNUMBER(B8),B8-B5,"-")', PCT2, BLACK, "Needed minus current"),
        ("Late orders to fix per year", f'=IF(ISNUMBER(B9),MAX(0,B9)*{D["orders"]},"-")', "#,##0", BLACK,
         "Gap x orders per year"),
    ]
    for i, (label, f, fmt, color, note) in enumerate(lines, start=5):
        _c(dl, f"A{i}", label)
        _c(dl, f"B{i}", f, color, fmt)
        _c(dl, f"C{i}", note, italic=True)
    dl.column_dimensions["A"].width, dl.column_dimensions["B"].width, dl.column_dimensions["C"].width = 38, 16, 70

    rt = wb.create_sheet("Retention")
    _title(rt, "Repeat purchases", "Annual value of repeat orders and of better first deliveries")
    _head(rt, 4, ["Line", "Value", "How it is calculated"])
    lines = [
        ("Customers per year", f"={D['cust']}", "#,##0", GREEN),
        ("180-day repeat rate", f"={D['rep']}", PCT2, GREEN),
        ("Repeat customers per year", "=B5*B6", "#,##0", BLACK),
        ("Repeat GMV per year (R$)", f"=B7*{D['aov']}", BRL, BLACK),
        ("Repeat contribution per year (R$)", f"=B8*{margin}", BRL, BLACK),
        ("Extra repeat customers if late first orders were on time", f"=B5*{D['late']}*({D['rep_on']}-{D['rep_late']})",
         "#,##0", BLACK),
        ("Extra contribution per year (R$)", f"=B10*{D['aov']}*{margin}", BRL, BLACK),
    ]
    for i, (label, f, fmt, color) in enumerate(lines, start=5):
        _c(rt, f"A{i}", label)
        _c(rt, f"B{i}", f, color, fmt)
    _c(rt, "C10", "Uses the measured repeat gap; its 95% confidence interval includes zero", italic=True)
    _c(rt, "A14", "Annual contribution from a higher repeat rate (R$)", bold=True)
    _c(rt, "A15", "Repeat-rate lift \\ AOV change", bold=True)
    aov_changes, lifts = [-0.10, 0.0, 0.10], [0.005, 0.01, 0.015, 0.02, 0.03]
    for j, ch in enumerate(aov_changes):
        _c(rt, f"{get_column_letter(2 + j)}15", ch, BLUE, '+0%;-0%;0%', bold=True)
    for i, lift in enumerate(lifts):
        r = 16 + i
        _c(rt, f"A{r}", lift, BLUE, PCT)
        for j in range(len(aov_changes)):
            col = get_column_letter(2 + j)
            _c(rt, f"{col}{r}", f"=$B$5*$A{r}*{D['aov']}*(1+{col}$15)*{margin}", BLACK, BRL)
    rt.column_dimensions["A"].width = 52
    for col in "BCD":
        rt.column_dimensions[col].width = 16
    rt.column_dimensions["C"].width = 18

    vo = wb.create_sheet("Voucher")
    _title(vo, "Second-order voucher break-even",
           "The voucher is paid on every repeat order by holders, including orders that would have happened anyway.")
    _head(vo, 4, ["Line", "Value", "How it is calculated"])
    lines = [
        ("Voucher value (R$)", f"={voucher}", BRL2, GREEN, "Inputs"),
        ("Base 180-day repeat rate", f"={D['rep']}", PCT2, GREEN, "Data"),
        ("Contribution per repeat order before voucher (R$)", f"={D['aov']}*{margin}", BRL2, BLACK, "AOV x margin"),
        ("Break-even repeat-rate lift (pts)", '=IF(B7<=B5,"Never breaks even",B6*B5/(B7-B5))', PCT2, BLACK,
         "base x voucher / (contribution - voucher)"),
        ("Break-even repeat rate", '=IF(ISNUMBER(B8),B6+B8,"-")', PCT2, BLACK, "Base + lift"),
    ]
    for i, (label, f, fmt, color, note) in enumerate(lines, start=5):
        _c(vo, f"A{i}", label)
        _c(vo, f"B{i}", f, color, fmt)
        _c(vo, f"C{i}", note, italic=True)
    _c(vo, "A12", "Break-even lift by voucher value and margin", bold=True)
    _c(vo, "A13", "Voucher (R$) \\ Margin", bold=True)
    margins, vouchers = [0.10, 0.15, 0.20, 0.25], [5, 10, 15, 20]
    for j, mg in enumerate(margins):
        _c(vo, f"{get_column_letter(2 + j)}13", mg, BLUE, PCT, bold=True)
    for i, v in enumerate(vouchers):
        r = 14 + i
        _c(vo, f"A{r}", v, BLUE, BRL2)
        for j in range(len(margins)):
            col = get_column_letter(2 + j)
            _c(vo, f"{col}{r}", f'=IF({D["aov"]}*{col}$13<=$A{r},"Never",$B$6*$A{r}/({D["aov"]}*{col}$13-$A{r}))',
               BLACK, PCT2)
    rng = f"B14:{get_column_letter(1 + len(margins))}{13 + len(vouchers)}"
    vo.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0.02"],
                                                  fill=PatternFill("solid", fgColor="C6EFCE")))
    vo.column_dimensions["A"].width = 46
    for col in "BCDE":
        vo.column_dimensions[col].width = 14

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
    config.EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(config.EXCEL_PATH)
    return str(config.EXCEL_PATH.relative_to(config.ROOT))
