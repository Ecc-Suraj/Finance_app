from datetime import datetime
import os

SHOP = os.getenv("SHOPIFY_STORE")


def write_report_info(
    writer,
    report_name,
    from_date=None,
    to_date=None
):
    """
    Writes common report metadata at the top of every CSV report.
    """

    writer.writerow([
        "Report Name",
        report_name
    ])

    writer.writerow([
        "Store Name",
        SHOP
    ])

    writer.writerow([
        "Generated On",
        datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")
    ])

    if from_date and to_date:
        writer.writerow([
            "Export Time Range",
            f"{from_date} to {to_date}"
        ])

    # Blank line before column headers
    writer.writerow([])