import os
import csv
import requests
import time
import argparse
from datetime import datetime, timezone

SHOP = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

if not SHOP:
    raise Exception("SHOPIFY_STORE secret not found")

if not TOKEN:
    raise Exception("SHOPIFY_ACCESS_TOKEN secret not found")

parser = argparse.ArgumentParser(
    description="Export Shopify AR aging orders."
)
parser.add_argument(
    "--start-date",
    help="Start date in YYYY-MM-DD format"
)
parser.add_argument(
    "--end-date",
    help="End date in YYYY-MM-DD format"
)

args = parser.parse_args()

search_query = ""

try:
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date
        else None
    )

    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if args.end_date
        else None
    )

except ValueError as exc:
    raise ValueError(
        "Dates must be in YYYY-MM-DD format"
    ) from exc

if start_date and end_date and start_date > end_date:
    raise ValueError(
        "--start-date must be on or before --end-date"
    )

start_iso = None
end_iso = None

if start_date:
    start_iso = (
        datetime.combine(
            start_date,
            datetime.min.time()
        )
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

if end_date:
    end_iso = (
        datetime.combine(
            end_date,
            datetime.max.time()
        )
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

if start_iso and end_iso:
    search_query = (
        f"created_at:>={start_iso} "
        f"created_at:<={end_iso}"
    )
elif start_iso:
    search_query = f"created_at:>={start_iso}"
elif end_iso:
    search_query = f"created_at:<={end_iso}"

print(
    "DEBUG: export_ar_orders args -> start-date:",
    args.start_date,
    "end-date:",
    args.end_date
)

print("DEBUG: search_query ->", repr(search_query))

URL = f"https://{SHOP}/admin/api/2025-10/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

QUERY = """
query GetOrders($cursor: String, $query: String) {
  orders(
    first: 250,
    after: $cursor,
    sortKey: CREATED_AT,
    reverse: true,
    query: $query
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

      partnerCertId: metafield(
        namespace: "custom",
        key: "partner_cert_id"
      ) {
        value
      }

      sapCustomerId: metafield(
        namespace: "custom",
        key: "sap_customer_id"
      ) {
        value
      }

      salesRepOwnerCode: metafield(
        namespace: "custom",
        key: "sales_rep_owner_code"
      ) {
        value
      }

      salesRepFullName: metafield(
        namespace: "custom",
        key: "sales_rep_full_name"
      ) {
        value
      }

      divisionName: metafield(
        namespace: "custom",
        key: "division_name"
      ) {
        value
      }

      divisionCode: metafield(
        namespace: "custom",
        key: "division_code"
      ) {
        value
      }

      entityName: metafield(
        namespace: "custom",
        key: "entity_name"
      ) {
        value
      }

      assignPartnerType: metafield(
        namespace: "custom",
        key: "assign_partner_type"
      ) {
        value
      }

      lineItems(first: 1) {
        nodes {

          sku
          name
          quantity

          product {

            zohoId: metafield(
              namespace: "custom",
              key: "zoho_id"
            ) {
              value
            }

            productTypeMeta: metafield(
              namespace: "custom",
              key: "ec_council_product_type"
            ) {
              value
            }

            productCategoryMeta: metafield(
              namespace: "custom",
              key: "ec_council_product_category"
            ) {
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


all_orders = []
cursor = None

ALLOWED_STATUSES = {
    "PARTIALLY_PAID",
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
            f"HTTP Error {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if "errors" in data:
        print("GRAPHQL ERROR:")
        print(data)
        raise Exception(data["errors"])

    orders = data["data"]["orders"]["nodes"]

    for order in orders:

        status = order.get(
            "displayFinancialStatus",
            ""
        )

        total = float(
            (
                order.get(
                    "currentTotalPriceSet",
                    {}
                )
                .get("presentmentMoney", {})
                .get("amount", 0)
            )
        )

        if status in ALLOWED_STATUSES and total > 0:
            all_orders.append(order)

    page_info = data["data"]["orders"]["pageInfo"]

    if not page_info["hasNextPage"]:
        break

    cursor = page_info["endCursor"]

    time.sleep(0.5)

print(f"Total Orders Found: {len(all_orders)}")

with open(
    "ar_aging_report.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as csvfile:

    writer = csv.writer(csvfile)

    writer.writerow([
        "S. No",
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
        "Currency",
        "Company / Partner Name",
        "Cert ID",
        "SAP ID",
        "Partner Type",
        "Sales Rep. Name",
        "Sales Rep. Emp Code",
        "Entity",
        "Division Name",
        "Division Code",
        "upto 30 Days",
        "31-60 days",
        "61-90 days",
        "91-120 days",
        "121-150 days",
        "151-360 days"
    ])

    row_no = 1

    for order in all_orders:

        purchasing_entity = (
            order.get("purchasingEntity")
            or {}
        )

        company_name = (
            purchasing_entity.get("company")
            or {}
        ).get("name", "")

        customer = order.get("customer") or {}

        line_items = (
            order.get("lineItems")
            or {}
        ).get("nodes", [])

        product_type = ""
        product_category = ""

        if line_items:

            line_item = line_items[0]

            product = (
                line_item.get("product")
                or {}
            )

            product_type = (
                (
                    product.get("productTypeMeta")
                    or {}
                ).get("value", "")
            )

            product_category = (
                (
                    product.get(
                        "productCategoryMeta"
                    )
                    or {}
                ).get("value", "")
            )

        partnerCertId = (
            order.get("partnerCertId")
            or {}
        )

        sapCustomerId = (
            order.get("sapCustomerId")
            or {}
        )

        assignPartnerType = (
            order.get("assignPartnerType")
            or {}
        )

        salesRepFullName = (
            order.get("salesRepFullName")
            or {}
        )

        salesRepOwnerCode = (
            order.get("salesRepOwnerCode")
            or {}
        )

        entityName = (
            order.get("entityName")
            or {}
        )

        divisionName = (
            order.get("divisionName")
            or {}
        )

        divisionCode = (
            order.get("divisionCode")
            or {}
        )

        shipping_charge = (
            (
                order.get(
                    "totalShippingPriceSet"
                )
                or {}
            )
            .get("presentmentMoney", {})
            .get("amount", "")
        )

        created_at = order.get(
            "createdAt",
            ""
        )

        upto_30 = "No"
        days_31_60 = "No"
        days_61_90 = "No"
        days_91_120 = "No"
        days_121_150 = "No"
        days_151_360 = "No"

        if created_at:

            order_date = datetime.fromisoformat(
                created_at.replace(
                    "Z",
                    "+00:00"
                )
            )

            days_old = (
                datetime.now(timezone.utc)
                - order_date
            ).days

            upto_30 = (
                "Yes"
                if days_old <= 30
                else "No"
            )

            days_31_60 = (
                "Yes"
                if 31 <= days_old <= 60
                else "No"
            )

            days_61_90 = (
                "Yes"
                if 61 <= days_old <= 90
                else "No"
            )

            days_91_120 = (
                "Yes"
                if 91 <= days_old <= 120
                else "No"
            )

            days_121_150 = (
                "Yes"
                if 121 <= days_old <= 150
                else "No"
            )

            days_151_360 = (
                "Yes"
                if days_old >= 151
                else "No"
            )

        writer.writerow([
            row_no,
            order.get("createdAt", ""),
            order.get("name", ""),
            customer.get("email", ""),
            order.get(
                "displayFinancialStatus",
                ""
            ),
            product_type,
            product_category,
            (
                order.get(
                    "currentSubtotalPriceSet",
                    {}
                )
                .get("presentmentMoney", {})
                .get("amount", "")
            ),
            
            (
                order.get(
                    "currentTotalTaxSet",
                    {}
                )
                .get("presentmentMoney", {})
                .get("amount", "")
            ),
            
            shipping_charge,
            
            (
                order.get(
                    "currentTotalPriceSet",
                    {}
                )
                .get("presentmentMoney", {})
                .get("amount", "")
            ),
            order.get(
                "presentmentCurrencyCode",
                ""
            ),
            company_name,
            partnerCertId.get("value", ""),
            sapCustomerId.get("value", ""),
            assignPartnerType.get("value", ""),
            salesRepFullName.get("value", ""),
            salesRepOwnerCode.get("value", ""),
            entityName.get("value", ""),
            divisionName.get("value", ""),
            divisionCode.get("value", ""),
            upto_30,
            days_31_60,
            days_61_90,
            days_91_120,
            days_121_150,
            days_151_360
        ])

        row_no += 1

print(
    "AR Aging CSV exported successfully -> "
    "ar_report.csv"
)
