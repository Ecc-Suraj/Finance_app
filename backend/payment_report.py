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

      purchasingEntity{
        ... on PurchasingCompany{
          company{
            name
          }
        }
      }

      partnerCertId:metafield(
        namespace:"custom",
        key:"partner_cert_id"
      ){
        value
      }

      sapCustomerId:metafield(
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

    search_query = ""

    if start_date and end_date:

        if isinstance(start_date, str):
            start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        if isinstance(end_date, str):
            end_date = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

        if start_date > end_date:
            raise Exception(
                "Start Date cannot be greater than End Date"
            )

        search_query = (
            f"created_at:>={start_date.isoformat()} "
            f"created_at:<={end_date.isoformat()}"
        )

    all_orders = []
    cursor = None

    ALLOWED_STATUSES = {
        "PAID",
        "PENDING"
    }

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

        for order in orders:

            payment_status = order.get(
                "displayFinancialStatus",
                ""
            )

            invoice_amount = float(
                (
                    order.get("currentTotalPriceSet", {})
                    .get("presentmentMoney", {})
                    .get("amount", 0)
                )
            )

            if (
                payment_status in ALLOWED_STATUSES
                and invoice_amount > 0
            ):
                all_orders.append(order)

        page_info = data["data"]["orders"]["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]

        time.sleep(0.5)

    print(f"Total Payment Records Found: {len(all_orders)}")

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

        row_no = 1

        for order in all_orders:
            purchasing_entity = order.get("purchasingEntity") or {}
            company = purchasing_entity.get("company") or {}

            partner_name = company.get("name", "")

            billing = order.get("billingAddress") or {}
            partner_country = billing.get("country", "")

            sap_customer = order.get("sapCustomerId") or {}
            partner_cert = order.get("partnerCertId") or {}

            transactions = order.get("transactions") or []

            payment_date = order.get("createdAt", "")
            payment_reference = ""
            payment_method = ""

            invoice_amount = float(
                (
                    order.get("currentTotalPriceSet", {})
                    .get("presentmentMoney", {})
                    .get("amount", 0)
                )
            )

            payment_received = 0.0

            financial_status = order.get(
                "displayFinancialStatus",
                ""
            )

            #
            # Only calculate received payment
            # for invoices that are not pending
            #
            if financial_status != "PENDING":

                for transaction in transactions:

                    transaction_kind = transaction.get(
                        "kind",
                        ""
                    )

                    transaction_status = transaction.get(
                        "status",
                        ""
                    )

                    #
                    # Ignore pending/failed/refund/etc.
                    #
                    if (
                        transaction_kind not in (
                            "SALE",
                            "CAPTURE"
                        )
                        or transaction_status != "SUCCESS"
                    ):
                        continue

                    #
                    # First successful payment
                    #
                    if payment_reference == "":

                        payment_reference = transaction.get(
                            "paymentId",
                            ""
                        )

                        payment_method = transaction.get(
                            "gateway",
                            ""
                        )

                        payment_date = (
                            transaction.get("processedAt")
                            or payment_date
                        )

                    #
                    # Sum successful payments
                    #
                    payment_received += float(
                        (
                            transaction.get("amountSet", {})
                            .get("presentmentMoney", {})
                            .get("amount", 0)
                        )
                    )

            writer.writerow([

                row_no,

                payment_date,

                payment_reference,

                payment_method,

                f"{invoice_amount:.2f}",

                f"{payment_received:.2f}",

                order.get(
                    "presentmentCurrencyCode",
                    ""
                ),

                order.get(
                    "name",
                    ""
                ),

                order.get(
                    "displayFinancialStatus",
                    ""
                ),

                sap_customer.get(
                    "value",
                    ""
                ),

                partner_cert.get(
                    "value",
                    ""
                ),

                partner_name,

                partner_country

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