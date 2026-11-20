"""Create notebooks/olist_analysis.ipynb (executed by `make notebook`)."""
import nbformat as nbf

from src import config

CELLS = [
    ("md", "# Olist: retention, CLV and delivery experience\nWalk-through of the analysis behind the README. "
           "Queries run live against the DuckDB warehouse built by `src/run_pipeline.py`."),
    ("code", "import os, sys, json, pathlib\nROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' "
             "else pathlib.Path.cwd()\nos.chdir(ROOT); sys.path.insert(0, str(ROOT))\nimport pandas as pd\n"
             "from IPython.display import Image, Markdown, display\nfrom src import analysis, config, data\n"
             "pd.set_option('display.float_format', lambda x: f'{x:,.4f}')\nresults = json.loads(config.RESULTS_JSON.read_text())"),
    ("md", "## 1. Data quality and row counts"),
    ("code", "display(pd.read_csv('reports/tables/quality_checks.csv'))\ndata.row_counts()"),
    ("md", "## 2. The business at a glance (SQL window functions)"),
    ("code", "data.query('08_monthly_kpis.sql').tail(12)"),
    ("code", "display(Image(filename='reports/figures/01_monthly_gmv_late_rate.png'))"),
    ("md", "## 3. Retention: monthly cohorts"),
    ("code", "coh = data.query('05_cohort_retention.sql')\ncoh.pivot_table(index='cohort_month', columns='months_since_first', "
             "values='retention_rate').iloc[:, :7]"),
    ("code", "display(Image(filename='reports/figures/02_cohort_retention.png'))"),
    ("md", "## 4. Delivery and reviews"),
    ("code", "orders = data.table('fact_orders')\nd = analysis.delivered_reviewed(orders)\nanalysis.review_by_lateness(d)"),
    ("code", "analysis.review_by_delay_bucket(d)"),
    ("code", "display(Image(filename='reports/figures/03_review_by_delay.png'))\nresults['ordinal_model']"),
    ("code", "data.query('06_delivery_kpis.sql').head(10)"),
    ("md", "## 5. Does a late first order reduce repeat purchases?"),
    ("code", "results['repeat_vs_first_delivery']"),
    ("md", "## 6. Segments and CLV"),
    ("code", "display(pd.read_csv('reports/tables/rfm_segments.csv'))\ndisplay(pd.read_csv('reports/tables/kmeans_k_selection.csv'))"),
    ("code", "display(Image(filename='reports/figures/05_rfm_segments.png'))\nresults['clv']['holdout']"),
    ("code", "display(Image(filename='reports/figures/06_clv_holdout.png'))\npd.read_csv('reports/tables/top_1000_customers_by_clv.csv').head(10)"),
    ("md", "## 7. Memo"),
    ("code", "display(Markdown(open('reports/memo.md').read()))"),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if k == "md" else nbf.v4.new_code_cell(s) for k, s in CELLS]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbf.write(nb, config.ROOT / "notebooks" / "olist_analysis.ipynb")


if __name__ == "__main__":
    main()
