from datetime import datetime
import os

SHOP = os.getenv("SHOPIFY_STORE")


def format_report_date(date_value):
    """
    Converts date/datetime/string to DD-MMM-YYYY format.
    """

    if not date_value:
        return ""

    if isinstance(date_value, datetime):
        return date_value.strftime("%d-%b-%Y")

    try:
        return datetime.strptime(
            str(date_value),
            "%Y-%m-%d"
        ).strftime("%d-%b-%Y")
    except Exception:
        return str(date_value)


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
            f"{format_report_date(from_date)} to {format_report_date(to_date)}"
        ])

    elif from_date:

        writer.writerow([
            "Export From Date",
            format_report_date(from_date)
        ])

    elif to_date:

        writer.writerow([
            "Export Till Date",
            format_report_date(to_date)
        ])

    # Blank line before column headers
    writer.writerow([])