from dotenv import load_dotenv
load_dotenv()

import os
import csv
import time
import argparse
import requests
from datetime import datetime

SHOP = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

if not SHOP:
    raise Exception("SHOPIFY_STORE secret not found")

if not TOKEN:
    raise Exception("SHOPIFY_ACCESS_TOKEN secret not found")

URL = f"https://{SHOP}/admin/api/2025-10/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

QUERY = """
query GetOrders($cursor:String,$query:String){

  orders(
    first:250,
    after:$cursor,
    sortKey:CREATED_AT,
    reverse:true,
    query:$query
  ){

    pageInfo{
      hasNextPage
      endCursor
    }

    nodes{

      id
      name
      createdAt
      displayFinancialStatus
      presentmentCurrencyCode

      currentTotalPriceSet{
        presentmentMoney{
          amount
          currencyCode
        }
      }

      billingAddress{
        country
      }

      purchasingEntity {
        ... on PurchasingCompany {
          company {

            name

            certId: metafield(
              namespace:"custom"
              key:"cert_id"
            ){
              value
            }

            sapId: metafield(
              namespace:"custom"
              key:"sap_id"
            ){
              value
            }

          }
        }
      }

      partnerCertId: metafield(
        namespace:"custom",
        key:"partner_cert_id"
      ){
        value
      }

      sapCustomerId: metafield(
        namespace:"custom",
        key:"sap_customer_id"
      ){
        value
      }

      transactions{

        kind
        status
        gateway
        paymentId
        processedAt

        amountSet{
          presentmentMoney{
            amount
            currencyCode
          }
        }

      }

    }

  }

}
"""

def generate_payment_report(start_date=None, end_date=None):

    if start_date and isinstance(start_date, str):
        start_date = datetime.strptime(
            start_date,
            "%Y-%m-%d"
        ).date()

    if end_date and isinstance(end_date, str):
        end_date = datetime.strptime(
            end_date,
            "%Y-%m-%d"
        ).date()

    if (
        start_date
        and end_date
        and start_date > end_date
    ):
        raise Exception(
            "Start Date cannot be greater than End Date"
        )

    #
    # Revenue Report
    # We intentionally DO NOT filter Shopify
    # using created_at because payments may
    # happen after invoice creation.
    #
    search_query = ""

    all_orders = []

    cursor = None

    while True:

        response = requests.post(

            URL,

            headers=HEADERS,

            json={
                "query": QUERY,
                "variables": {
                    "cursor": cursor,
                    "query": search_query
                }
            }

        )

        if response.status_code != 200:
            raise Exception(
                f"HTTP Error {response.status_code}: {response.text}"
            )

        data = response.json()

        if "errors" in data:
            print(data)
            raise Exception(data["errors"])

        orders = data["data"]["orders"]["nodes"]

        all_orders.extend(orders)

        page_info = data["data"]["orders"]["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]

        time.sleep(0.5)

    print(
        f"Orders Retrieved : {len(all_orders)}"
    )

    with open(
        "payment_report.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "S. No.",
            "Payment Date",
            "Payment Reference",
            "Payment Method",
            "Invoice Amount",
            "Payment Received Amount",
            "Currency",
            "Original Invoice Number",
            "Payment/Order Status",
            "Partner Code",
            "Partner Shopify ID",
            "Partner Name",
            "Partner Country"
        ])

        report_rows = []

        ALLOWED_STATUSES = {
            "PAID",
            "PARTIALLY_PAID"
        }

        #
        # Process every order
        #
        for order in all_orders:

            financial_status = (
                order.get("displayFinancialStatus", "")
                .strip()
                .upper()
            )

            if financial_status not in ALLOWED_STATUSES:
                continue

            purchasing_entity = order.get("purchasingEntity") or {}
            company = purchasing_entity.get("company") or {}

            partner_name = company.get("name", "")

            billing = order.get("billingAddress") or {}
            partner_country = billing.get("country", "")

            sap_customer = company.get("sapId") or {}
            partner_cert = company.get("certId") or {}

            invoice_amount = float(
                (
                    order.get("currentTotalPriceSet", {})
                    .get("presentmentMoney", {})
                    .get("amount", 0)
                )
            )

            transactions = order.get("transactions") or []

            #
            # Every successful payment transaction
            #
            for transaction in transactions:

                transaction_kind = (
                    transaction.get("kind", "")
                    .upper()
                )

                transaction_status = (
                    transaction.get("status", "")
                    .upper()
                )

                #
                # Revenue transactions only
                #
                if transaction_kind not in (
                    "SALE",
                    "CAPTURE"
                ):
                    continue

                if transaction_status != "SUCCESS":
                    continue

                transaction_date = transaction.get("processedAt")

                if not transaction_date:
                    continue

                transaction_datetime = datetime.fromisoformat(
                    transaction_date.replace("Z", "+00:00")
                )

                transaction_dt = transaction_datetime.date()

                #
                # Filter by selected date
                #
                if (
                    start_date
                    and transaction_dt < start_date
                ):
                    continue

                if (
                    end_date
                    and transaction_dt > end_date
                ):
                    continue

                formatted_payment_date = transaction_datetime.strftime(
                    "%d-%m-%Y"
                )

                payment_received = float(
                    (
                        transaction.get("amountSet", {})
                        .get("presentmentMoney", {})
                        .get("amount", 0)
                    )
                )

                payment_reference = (
                    transaction.get("paymentId")
                    or ""
                )

                payment_method = (
                    transaction.get("gateway")
                    or ""
                )

                report_rows.append({

                    #
                    # Used only for sorting
                    #
                    "transaction_date": transaction_datetime,

                    #
                    # CSV columns
                    #
                    "payment_date": formatted_payment_date,

                    "payment_reference": payment_reference,

                    "payment_method": payment_method,

                    "invoice_amount": f"{invoice_amount:.2f}",

                    "payment_received": f"{payment_received:.2f}",

                    "currency": order.get(
                        "presentmentCurrencyCode",
                        ""
                    ),

                    "invoice_number": order.get(
                        "name",
                        ""
                    ),

                    "payment_status": order.get(
                        "displayFinancialStatus",
                        ""
                    ),

                    "partner_code": sap_customer.get(
                        "value",
                        ""
                    ),

                    "partner_shopify_id": partner_cert.get(
                        "value",
                        ""
                    ),

                    "partner_name": partner_name,

                    "partner_country": partner_country

                })

        #
        # Sort ALL transactions by payment date
        #
        report_rows.sort(
            key=lambda x: x["transaction_date"],
            reverse=True
        )

        row_no = 1

        for row in report_rows:

            writer.writerow([

                row_no,

                row["payment_date"],

                row["payment_reference"],

                row["payment_method"],

                row["invoice_amount"],

                row["payment_received"],

                row["currency"],

                row["invoice_number"],

                row["payment_status"],

                row["partner_code"],

                row["partner_shopify_id"],

                row["partner_name"],

                row["partner_country"]

            ])

            row_no += 1

            print(
        "Payment Report exported successfully -> payment_report.csv"
    )

    return "payment_report.csv"


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Export Shopify Payment Report"
    )

    parser.add_argument(
        "--start-date",
        help="Start Date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end-date",
        help="End Date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    generate_payment_report(
        start_date=args.start_date,
        end_date=args.end_date
    )