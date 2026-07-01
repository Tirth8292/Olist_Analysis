from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


OUT = Path(r"C:\Users\tirth\Documents\Codex\2026-06-23\hi-2\outputs\Olist_Analytics_Engineering_Project_Report.pdf")


def p(text, style):
    return Paragraph(text, style)


def kv_table(rows):
    data = [["Area", "Details"]] + rows
    table = Table(data, colWidths=[1.7 * inch, 4.6 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D2DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def bullet(text, styles):
    return Paragraph(f"&bull; {text}", styles["Body"])


def build():
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        rightMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleBlue", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#1F4D78"), spaceAfter=8))
    styles.add(ParagraphStyle(name="H1Blue", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#2E74B5"), spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13, spaceAfter=6))
    styles.add(ParagraphStyle(name="Callout", parent=styles["Body"], backColor=colors.HexColor("#F4F6F9"), borderColor=colors.HexColor("#D8E0EA"), borderWidth=0.5, borderPadding=8, leading=13, spaceAfter=10))

    story = []
    story.append(p("Olist Analytics Engineering Project Report", styles["TitleBlue"]))
    story.append(p("<i>Modern data analytics platform for e-commerce marketplace intelligence</i>", styles["Body"]))
    story.append(Spacer(1, 6))
    story.append(p("<b>Short summary:</b> This project converts 9 disconnected Olist e-commerce CSV files into a clean analytics system. It builds warehouse tables, business metrics, seller scoring, customer analysis, repeat-order insights, and a local API that can be tested through localhost.", styles["Callout"]))

    story.append(p("1. Project Motive", styles["H1Blue"]))
    story.append(p("The main motive of this project is to solve a common business problem: data exists in many separate files, but business teams need simple answers. Olist has data about customers, orders, sellers, products, payments, reviews, and delivery locations. Without a proper data model, teams must manually join files every time they need an answer.", styles["Body"]))
    story.append(p("This project creates a repeatable pipeline that turns raw data into useful information for Growth, Operations, and Customer teams. It is designed like a real analytics engineering project, not only a notebook or one-time report.", styles["Body"]))

    story.append(p("2. Data Used", styles["H1Blue"]))
    story.append(kv_table([
        ["Dataset", "Brazilian E-Commerce Public Dataset by Olist"],
        ["Source files", "9 CSV files: customers, orders, order items, payments, reviews, products, sellers, geolocation, and product category translation"],
        ["Scale", "99,441 orders, 112,650 order items, 3,095 sellers, and about 1,000,000 geolocation rows"],
        ["Time period", "Historical e-commerce orders from 2016 to 2018"],
        ["Storage created", "Local SQLite warehouse: data/warehouse/olist.db"],
    ]))
    story.append(Spacer(1, 8))

    story.append(p("3. What Was Built", styles["H1Blue"]))
    for item in [
        "A raw ingestion layer that loads all CSV files into a local warehouse.",
        "A staging layer that cleans column names, data types, dates, city names, and product categories.",
        "A star schema with fact and dimension tables for orders, order items, payments, customers, sellers, products, dates, and geolocation.",
        "Business views for category revenue, seller performance, and delivery SLA analysis.",
        "Feature outputs for seller scores, customer RFM segments, cohort retention, delivery lanes, and repeat order patterns.",
        "A FastAPI localhost API where users can test seller score, seller leaderboard, delivery estimate, and repeat-order endpoints.",
    ]:
        story.append(bullet(item, styles))

    story.append(p("4. Project Architecture", styles["H1Blue"]))
    story.append(kv_table([
        ["Step 1: Ingest", "Python reads the raw CSV files and loads them into the local database."],
        ["Step 2: Transform", "SQL creates clean staging tables and modeled fact/dimension tables."],
        ["Step 3: Analyze", "Python and SQL calculate seller scores, RFM, cohort retention, delivery lanes, and repeat orders."],
        ["Step 4: Serve", "FastAPI exposes selected insights through localhost endpoints."],
        ["Step 5: Present", "CSV reports and dashboard guidance can be used in Power BI."],
    ]))

    story.append(PageBreak())
    story.append(p("5. Tools and Their Use", styles["H1Blue"]))
    story.append(kv_table([
        ["Python", "Used for loading CSV files, feature engineering, quality checks, and API logic."],
        ["SQL", "Used for staging, fact tables, dimension tables, and business views."],
        ["SQLite", "Used as the local data warehouse so the project runs easily on one computer."],
        ["FastAPI", "Used to expose seller and delivery insights through localhost."],
        ["Apache Airflow", "Included as the orchestration layer to automate the pipeline steps in production."],
        ["Docker", "Included to make the project reproducible and easier to run in a clean environment."],
        ["dbt", "Included as the analytics engineering structure for production-style transformations and tests."],
        ["Power BI", "Planned for dashboard pages using generated CSV reports and warehouse tables."],
        ["Polars", "Not used in the current working version; it can be added later for faster large CSV processing."],
    ]))

    story.append(p("6. Seller Performance Score", styles["H1Blue"]))
    story.append(p("The seller leaderboard is based on a weighted performance score. This score helps identify strong sellers, watchlist sellers, and high-risk sellers before they hurt customer experience.", styles["Body"]))
    story.append(kv_table([
        ["On-time delivery rate", "40% of the score. Sellers who deliver before or on the estimated date perform better."],
        ["Average review score", "30% of the score. Better customer reviews increase the seller score."],
        ["Order cancellation rate", "20% of the score. Lower cancellation improves the score."],
        ["Average order value growth", "10% of the score. Sellers with better revenue growth receive a small boost."],
    ]))

    story.append(p("7. API Features on Localhost", styles["H1Blue"]))
    story.append(p("The API runs locally at http://127.0.0.1:8000/docs. This means it works on the same computer where the project is running. The docs page is not a public website; it is a testing page for the local API.", styles["Body"]))
    story.append(kv_table([
        ["GET /health", "Checks whether the API is running."],
        ["POST /seller/score", "Accepts a seller_id and returns score, risk tier, GMV, metrics, and recommendation."],
        ["GET /sellers/leaderboard", "Shows best or worst sellers based on the weighted performance score."],
        ["GET /seller/{seller_id}", "Shows detailed information for one seller, including rank and score breakdown."],
        ["GET /delivery/estimate", "Returns estimated delivery days for a historical origin and destination zip route."],
        ["GET /orders/repeat-by-city", "Shows which product categories are repeatedly ordered by customers in each city."],
    ]))

    story.append(PageBreak())
    story.append(p("8. Important Files Used", styles["H1Blue"]))
    story.append(kv_table([
        ["extract_load.py", "Loads all raw Olist CSV files into the local warehouse."],
        ["01_staging.sql", "Cleans and standardizes raw tables."],
        ["02_marts.sql", "Builds fact and dimension tables."],
        ["03_views.sql", "Creates business views for analytics."],
        ["feature_engineering.py", "Creates seller scores, RFM, cohort retention, and delivery lane reports."],
        ["api/main.py", "Runs the FastAPI localhost endpoints."],
        ["olist_pipeline_dag.py", "Shows how Airflow would automate the pipeline."],
        ["docker-compose.yml", "Shows how Docker can run project services."],
        ["reports folder", "Stores generated CSV outputs for dashboard and API use."],
    ]))

    story.append(p("9. Business Value", styles["H1Blue"]))
    for item in [
        "Operations teams can find seller regions and delivery routes with high late-delivery risk.",
        "Growth teams can identify strong sellers and categories that deserve more marketplace visibility.",
        "Customer teams can understand repeat buying behavior by city and product category.",
        "Analysts can use modeled tables instead of manually joining many CSV files again and again.",
        "The API proves that the project can serve insights, not only create static reports.",
    ]:
        story.append(bullet(item, styles))

    story.append(p("10. Easy Interview Explanation", styles["H1Blue"]))
    story.append(p("I built an end-to-end analytics engineering project using the Olist e-commerce dataset. I ingested 9 raw CSV files, cleaned and modeled them into fact and dimension tables, created SQL business views, engineered seller risk, customer RFM, cohort retention, delivery lane, and repeat-order features, and exposed key insights through a FastAPI localhost API. The project demonstrates data modeling, pipeline design, analytics, and dashboard readiness.", styles["Body"]))
    story.append(p("<b>Final project story:</b> This project turns raw marketplace data into decision-ready insights. It helps teams understand seller quality, delivery performance, customer behavior, repeat orders by city, and product category performance using a repeatable analytics pipeline.", styles["Callout"]))

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()

