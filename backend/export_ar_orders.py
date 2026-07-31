import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
from report_utils import write_report_info

load_dotenv()

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
query GetOrders($cursor: String) {
  orders(
    first: 250
    after: $cursor
    sortKey: CREATED_AT
    reverse: true
  ) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      name
      createdAt
      displayFinancialStatus
      presentmentCurrencyCode

      totalShippingPriceSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      customer {
        email
      }

      purchasingEntity {
        ... on PurchasingCompany {
          company {
            name
            certId: metafield(namespace: "custom", key: "cert_id") {
              value
            }
            sapId: metafield(namespace: "custom", key: "sap_id") {
              value
            }
          }
        }
      }

      currentSubtotalPriceSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      currentTotalTaxSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      currentTotalPriceSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      totalOutstandingSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      totalReceivedSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      totalRefundedSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      salesRepOwnerCode: metafield(namespace: "custom", key: "sales_rep_owner_code") {
        value
      }

      salesRepFullName: metafield(namespace: "custom", key: "sales_rep_full_name") {
        value
      }

      divisionName: metafield(namespace: "custom", key: "division_name") {
        value
      }

      divisionCode: metafield(namespace: "custom", key: "division_code") {
        value
      }

      entityName: metafield(namespace: "custom", key: "entity_name") {
        value
      }

      assignPartnerType: metafield(namespace: "custom", key: "assign_partner_type") {
        value
      }

      lineItems(first: 1) {
        nodes {
          sku
          name
          quantity
          product {
            zohoId: metafield(namespace: "custom", key: "zoho_id") {
              value
            }
            productTypeMeta: metafield(namespace: "custom", key: "ec_council_product_type") {
              value
            }
            productCategoryMeta: metafield(namespace: "custom", key: "ec_council_product_category") {
              value
            }
          }
          originalUnitPriceSet {
            presentmentMoney {
              amount
              currencyCode
            }
          }
          originalTotalSet {
            presentmentMoney {
              amount
              currencyCode
            }
          }
        }
      }
    }
  }
}
"""


def generate_ar_report(end_date=None):
    if end_date and isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    all_orders = []
    cursor = None

    EXCLUDED_STATUSES = {
        "PAID",
        "VOIDED",
        "REFUNDED",
        "PARTIALLY_REFUNDED"
    }

    while True:
        response = requests.post(
            URL,
            headers=HEADERS,
            json={
                "query": QUERY,
                "variables": {
                    "cursor": cursor
                }
            }
        )

        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}: {response.text}")

        data = response.json()

        with open(f"page_{cursor or '1'}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        if "errors" in data:
            print(data)
            raise Exception(data["errors"])

        orders = data["data"]["orders"]["nodes"]

        print("=" * 80)
        print("Orders Returned:", len(orders))

        for order in orders:
            print(
                order["name"],
                "|",
                order["displayFinancialStatus"],
                "|",
                order["currentTotalPriceSet"]["presentmentMoney"]["amount"],
                "|",
                order["totalOutstandingSet"]["presentmentMoney"]["amount"],
                "|",
                order["createdAt"]
            )

        print("=" * 80)

        for order in orders:
            created_at = order.get("createdAt")

            if created_at:
                order_date = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ).date()

                if end_date and order_date > end_date:
                    continue

                status = (
                    order.get("displayFinancialStatus", "")
                    .strip()
                    .upper()
                )

                total = float(
                    order.get("currentTotalPriceSet", {})
                    .get("presentmentMoney", {})
                    .get("amount", 0)
                )

                if status not in EXCLUDED_STATUSES and total > 0:
                    print("ADDING", order["name"], status, order["createdAt"])
                    all_orders.append(order)

        page_info = data["data"]["orders"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]
        time.sleep(0.5)

    # Write compiled data to CSV
    with open("ar_aging_report.csv", "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)

        write_report_info(
            writer,
            "AR report",
            to_date=end_date
        )

        writer.writerow([
            "Sr. No.",
            "Order Date",
            "Order Number",
            "Email ID",
            "Payment Status",
            "Product Type",
            "Product Category",
            "Subtotal",
            "Tax Value",
            "Shipping Charge",
            "Grand Total",
            "Paid",
            "Outstanding",
            "Currency",
            "Partner Name",
            "Partner Cert ID",
            "Partner SAP ID",
            "Partner Type",
            "Sales Rep. Name",
            "Sales Rep. Emp Code",
            "Entity",
            "Division Name",
            "Division Code",
            "Order Age",
            "upto 30 Days",
            "31-60 Days",
            "61-90 Days",
            "91-120 Days",
            "121-150 Days",
            "151-180 Days",
            "181-365 Days",
            "365 Above"
        ])

        row_no = 1

        for order in all_orders:
            purchasing_entity = order.get("purchasingEntity") or {}
            company_name = (purchasing_entity.get("company") or {}).get("name", "")
            customer = order.get("customer") or {}

            grand_total = float(
                order.get("currentTotalPriceSet", {})
                .get("presentmentMoney", {})
                .get("amount", 0)
            )

            outstanding = float(
                (order.get("totalOutstandingSet") or {})
                .get("presentmentMoney", {})
                .get("amount", 0)
            )

            paid_amount = float(
                (order.get("totalReceivedSet") or {})
                .get("presentmentMoney", {})
                .get("amount", 0)
            )

            line_items = (order.get("lineItems") or {}).get("nodes", [])

            product_type = ""
            product_category = ""

            if line_items:
                line_item = line_items[0]
                product = line_item.get("product") or {}

                product_type = (
                    product.get("productTypeMeta") or {}
                ).get("value", "")

                product_category = (
                    product.get("productCategoryMeta") or {}
                ).get("value", "")

            company = (order.get("purchasingEntity") or {}).get("company") or {}
            partnerCertId = company.get("certId") or {}
            sapCustomerId = company.get("sapId") or {}

            assignPartnerType = order.get("assignPartnerType") or {}
            salesRepFullName = order.get("salesRepFullName") or {}
            salesRepOwnerCode = order.get("salesRepOwnerCode") or {}
            entityName = order.get("entityName") or {}
            divisionName = order.get("divisionName") or {}
            divisionCode = order.get("divisionCode") or {}

            shipping_charge = (
                (order.get("totalShippingPriceSet") or {})
                .get("presentmentMoney", {})
                .get("amount", "")
            )

            created_at = order.get("createdAt", "")
            order_age = 0

            upto_30 = 0
            days_31_60 = 0
            days_61_90 = 0
            days_91_120 = 0
            days_121_150 = 0
            days_151_180 = 0
            days_181_365 = 0
            days_365_above = 0
            order_date_display = ""

            if created_at:
                order_datetime = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
                order_date = order_datetime.date()
                order_date_display = order_datetime.strftime("%d-%b-%Y")

                days_old = (datetime.now().date() - order_date).days
                order_age = days_old

                if days_old <= 30:
                    upto_30 = grand_total
                elif days_old <= 60:
                    days_31_60 = grand_total
                elif days_old <= 90:
                    days_61_90 = grand_total
                elif days_old <= 120:
                    days_91_120 = grand_total
                elif days_old <= 150:
                    days_121_150 = grand_total
                elif days_old <= 180:
                    days_151_180 = grand_total
                elif days_old <= 365:
                    days_181_365 = grand_total
                else:
                    days_365_above = grand_total

            writer.writerow([
                row_no,
                order_date_display,
                order.get("name", ""),
                customer.get("email", ""),
                order.get("displayFinancialStatus", ""),
                product_type,
                product_category,
                (order.get("currentSubtotalPriceSet", {}).get("presentmentMoney", {}).get("amount", "")),
                (order.get("currentTotalTaxSet", {}).get("presentmentMoney", {}).get("amount", "")),
                shipping_charge,
                (order.get("currentTotalPriceSet", {}).get("presentmentMoney", {}).get("amount", "")),
                round(paid_amount, 2),
                round(outstanding, 2),
                order.get("presentmentCurrencyCode", ""),
                company_name,
                partnerCertId.get("value", ""),
                sapCustomerId.get("value", ""),
                assignPartnerType.get("value", ""),
                salesRepFullName.get("value", ""),
                salesRepOwnerCode.get("value", ""),
                entityName.get("value", ""),
                divisionName.get("value", ""),
                divisionCode.get("value", ""),
                order_age,
                round(upto_30, 2),
                round(days_31_60, 2),
                round(days_61_90, 2),
                round(days_91_120, 2),
                round(days_121_150, 2),
                round(days_151_180, 2),
                round(days_181_365, 2),
                round(days_365_above, 2)
            ])

            row_no += 1

    return "ar_aging_report.csv"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export Shopify AR Aging Orders"
    )

    parser.add_argument(
        "--end-date",
        help="End Date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    generate_ar_report(
        end_date=args.end_date
    )