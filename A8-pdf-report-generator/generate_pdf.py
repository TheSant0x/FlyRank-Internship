from app.pdf import render_report

if __name__ == "__main__":
    path = render_report("report.db", "reports/test.pdf")
    print(f"Generated {path}")
