from dotenv import load_dotenv
load_dotenv()

import os
import csv
import requests
import time
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
      note
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

            certId: metafield(
              namespace: "custom"
              key: "cert_id"
            ) {
              value
            }

            sapId: metafield(
              namespace: "custom"
              key: "sap_id"
            ) {
              value
            }
          }
        }
      }

      subtotalPriceSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      totalTaxSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      totalPriceSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }

      billingAddress {
        address1
        address2
        city
        province
        provinceCode
        country
        countryCodeV2
        zip
      }

      shippingAddress {
        address1
        address2
        city
        province
        provinceCode
        country
        countryCodeV2
        zip
      }

      transactions {
        kind
        gateway
        paymentId
        processedAt
      }

      fulfillments {
        status
        createdAt
      }

      salesRepOwnerCode: metafield(
        namespace: "custom",
        key: "sales_rep_owner_code"
      ) {
        value
      }

      businessEntityName: metafield(
        namespace: "custom",
        key: "business_entity_name"
      ) {
        value
      }

      salesRepFullName: metafield(
        namespace: "custom",
        key: "sales_rep_full_name"
      ) {
        value
      }

      salesOrgCode: metafield(
        namespace: "custom",
        key: "sales_org_code"
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

      paymentTermsName: metafield(
        namespace: "custom",
        key: "payment_terms_name"
      ) {
        value
      }

      entityName: metafield(
        namespace: "custom",
        key: "entity_name"
      ) {
        value
      }

      profitCenterName: metafield(
        namespace: "custom",
        key: "profit_center_code"
      ) {
        value
      }

      nextPaymentDueAt: metafield(
        namespace: "custom",
        key: "next_payment_due_at"
      ) {
        value
      }

      discountCodeMeta: metafield(
        namespace: "custom",
        key: "discount_code"
      ) {
        value
      }

      assignPartnerType: metafield(
        namespace: "custom",
        key: "assign_partner_type"
      ) {
        value
      }

      lineItems(first: 100) {
        nodes {

          sku
          name
          quantity

          product {

            productType

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

          discountAllocations {
            allocatedAmountSet {
              presentmentMoney {
                amount
                currencyCode
              }
            }
          }

          taxLines {
            priceSet {
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

}
"""



def generate_order_report(start_date=None, end_date=None):

    search_query = ""

    if start_date and end_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        if start_date > end_date:
            raise Exception("Start Date cannot be greater than End Date")
        search_query = (
            f"created_at:>={start_date.isoformat()} "
            f"created_at:<={end_date.isoformat()}"
        )

        
        all_orders = []
        cursor = None

        # ✅ Pagination loop
        while True:
            response = requests.post(
                URL,
                headers=HEADERS,
                json={"query": QUERY, "variables": {"cursor": cursor, "query": search_query}}
            )

            # ✅ HTTP error check
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")

            data = response.json()

            # ✅ GraphQL error check
            if "errors" in data:
                print("GRAPHQL ERROR:")
                print(data)
                raise Exception(data["errors"])

            orders = data["data"]["orders"]["nodes"]

            ALLOWED_STATUSES = {
                "PAID",
                "PARTIALLY_PAID",
                "PENDING",
                "PARTIALLY_REFUNDED"
            }

            for order in orders:

                status = order.get("displayFinancialStatus", "")

                total = float(
                    (
                        order.get("totalPriceSet", {})
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
            "orders_report.csv",
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
            "SKU Code",
            "Product Name",
            "Product Type",
            "Product Category",
            "Qty",
            "List Price",
            "Order Value",
            "Discount Value",
            "Subtotal",
            "Tax Value",
            "Shipping Charge",
            "Grand Total",
            "Currency",
            "Partner code",
            "Shopify Partner ID",
            "Partner Name",
            "Partner Type",
            "Billing Address",
            "Billing City",
            "Billing State Name",
            "Billing State",
            "Billing Country Name",
            "Billing Country",
            "Billing Zip Code",
            "Shipping Address",
            "Shipping City",
            "Shipping State Name",
            "Shipping State",
            "Shipping Country Name",
            "Shipping Country",
            "Shipping Zip Code",
            "Sales Rep Name",
            "Sales Rep Emp Code",
            "Payment Terms",
            "Payment Reference",
            "Payment Method",
            "Next Payment Due At",
            "Entity Name",
            "Sales Org Code",
            "Entity",
            "Division Name",
            "Division Code",
            "Profit Center",
            "Comments",
            "Fulfillment Status",
            "Fulfilled At",
            "Discount Code"
        ])
    
    

            row_no = 1
            
            for order in all_orders:
                
                purchasing_entity = order.get("purchasingEntity") or {}
                
                company_name = (
                    purchasing_entity.get("company") or {}
                ).get("name", "")
            
                customer = order.get("customer") or {}
                billing = order.get("billingAddress") or {}
                shipping = order.get("shippingAddress") or {}
            
                entityName = order.get("entityName") or {}
                assignPartnerType = order.get("assignPartnerType") or {}
                salesRepFullName = order.get("salesRepFullName") or {}
                salesRepOwnerCode = order.get("salesRepOwnerCode") or {}
                paymentTermsName = order.get("paymentTermsName") or {}
                nextPaymentDueAt = order.get("nextPaymentDueAt") or {}
                businessEntityName = order.get("businessEntityName") or {}
                salesOrgCode = order.get("salesOrgCode") or {}
                divisionName = order.get("divisionName") or {}
                divisionCode = order.get("divisionCode") or {}
                profitCenterName = order.get("profitCenterName") or {}
                discountCodeMeta = order.get("discountCodeMeta") or {}
            
                company = (
                    (order.get("purchasingEntity") or {})
                    .get("company") or {}
                )

                partnerCertId = company.get("certId") or {}
                sapCustomerId = company.get("sapId") or {}
            
                shipping_charge = (
                    order.get("totalShippingPriceSet") or {}
                ).get("presentmentMoney", {}).get("amount", "")
            
                transactions = order.get("transactions") or []
                transaction = (
                    transactions[-1]
                    if transactions
                    else {}
                )
            
                fulfillments = order.get("fulfillments") or []
                fulfillment = (
                    fulfillments[-1]
                    if fulfillments
                    else {}
                )
            
                line_items = (
                    order.get("lineItems") or {}
                ).get("nodes", [])

                if not line_items:
                    line_items = [{}]

                for item in line_items:
                    product = item.get("product") or {}
                    
                    zohoIdMeta = product.get("zohoId") or {}
                    productTypeMeta = product.get("productTypeMeta") or {}
                    productCategoryMeta = product.get("productCategoryMeta") or {}
                    
                    zoho_id = zohoIdMeta.get("value", "")
                    
                    product_type = productTypeMeta.get(
                        "value",
                        ""
                    )
                    
                    product_category = productCategoryMeta.get(
                        "value",
                        ""
                    )

                    discount_value = sum(
                        float(
                            (
                                d.get("allocatedAmountSet", {})
                                .get("presentmentMoney", {})
                                .get("amount", 0)
                            )
                        )
                        for d in item.get("discountAllocations", [])
                    )

                    tax_value = sum(
                        float(
                            (
                                t.get("priceSet", {})
                                .get("presentmentMoney", {})
                                .get("amount", 0)
                            )
                        )
                        for t in item.get("taxLines", [])
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
                    
                        zoho_id,
                    
                        item.get("name", ""),
                    
                        product_type,
                    
                        product_category,
                    
                        item.get("quantity", ""),
                    
                        (
                            item.get(
                                "originalUnitPriceSet",
                                {}
                            )
                            .get("presentmentMoney", {})
                            .get("amount", "")
                        ),
                    
                        (
                            item.get(
                                "originalTotalSet",
                                {}
                            )
                            .get("presentmentMoney", {})
                            .get("amount", "")
                        ),
                    
                        discount_value,
                    
                        (
                            order.get(
                                "subtotalPriceSet",
                                {}
                            )
                            .get("presentmentMoney", {})
                            .get("amount", "")
                        ),
                    
                        (
                            order.get(
                                "totalTaxSet",
                                {}
                            )
                            .get("presentmentMoney", {})
                            .get("amount", "")
                        ),
                    
                        shipping_charge,
                    
                        (
                            order.get(
                                "totalPriceSet",
                                {}
                            )
                            .get("presentmentMoney", {})
                            .get("amount", "")
                        ),
                    
                        order.get(
                            "presentmentCurrencyCode",
                            ""
                        ),
                    
                        sapCustomerId.get("value", ""),
                    
                        partnerCertId.get("value", ""),
                    
                        company_name,
                    
                        assignPartnerType.get("value", ""),
                    
                        " ".join(
                            filter(
                                None,
                                [
                                    billing.get("address1", ""),
                                    billing.get("address2", "")
                                ]
                            )
                        ),
                    
                        billing.get("city", ""),
                        billing.get("province", ""),
                        billing.get("provinceCode", ""),
                        billing.get("country", ""),
                        billing.get("countryCodeV2", ""),
                        billing.get("zip", ""),
                    
                        " ".join(
                            filter(
                                None,
                                [
                                    shipping.get("address1", ""),
                                    shipping.get("address2", "")
                                ]
                            )
                        ),
                    
                        shipping.get("city", ""),
                        shipping.get("province", ""),
                        shipping.get("provinceCode", ""),
                        shipping.get("country", ""),
                        shipping.get("countryCodeV2", ""),
                        shipping.get("zip", ""),
                    
                        salesRepFullName.get("value", ""),
                        salesRepOwnerCode.get("value", ""),
                    
                        paymentTermsName.get("value", ""),
                    
                        transaction.get("paymentId", ""),
                    
                        transaction.get("gateway", ""),
                    
                        nextPaymentDueAt.get("value", ""),
                    
                        businessEntityName.get("value", ""),
                    
                        salesOrgCode.get("value", ""),
                    
                        entityName.get("value", ""),
                    
                        divisionName.get("value", ""),
                    
                        divisionCode.get("value", ""),
                    
                        profitCenterName.get("value", ""),
                    
                        order.get("note", ""),
                    
                        fulfillment.get("status", ""),
                    
                        fulfillment.get("createdAt", ""),
                    
                        discountCodeMeta.get("value", "")
                    ])

                    row_no += 1

        print("Finance CSV exported successfully -> orders_report.csv")

        return "orders_report.csv"
    

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Export Shopify Order Report"
    )

    parser.add_argument("--start-date")
    parser.add_argument("--end-date")

    args = parser.parse_args()

    generate_order_report(
        start_date=args.start_date,
        end_date=args.end_date
    )


