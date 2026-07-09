import os
import csv
import time
import requests

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
query GetCompanies($cursor: String){

  companies(
    first:250,
    after:$cursor,
    sortKey:ID,
    reverse:true
  ){

    pageInfo{
      hasNextPage
      endCursor
    }

    nodes{

      id

      name

      certId:metafield(
        namespace:"custom",
        key:"cert_id"
      ){
        value
      }

      sapId:metafield(
        namespace:"custom",
        key:"sap_id"
      ){
        value
      }

      partnerType:metafield(
        namespace:"custom",
        key:"type"
      ){
        value
      }

    }

  }

}
"""

all_companies = []

cursor = None

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
        raise Exception(
            f"HTTP Error {response.status_code}: {response.text}"
        )

    data = response.json()

    if "errors" in data:
        print(data)
        raise Exception(data["errors"])

    companies = data["data"]["companies"]["nodes"]

    all_companies.extend(companies)

    page_info = data["data"]["companies"]["pageInfo"]

    if not page_info["hasNextPage"]:
        break

    cursor = page_info["endCursor"]

    time.sleep(0.5)

print(
    f"Total Companies Found: {len(all_companies)}"
)
with open(
    "partner_master_report.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as csvfile:

    writer = csv.writer(csvfile)

    writer.writerow([

        "S. No.",

        "Shopify Partner ID",

        "Partner Name",

        "Cert ID",

        "SAP ID",

        "Partner Type"

    ])

    row_no = 1

    for company in all_companies:

        #
        # Convert Shopify GID
        # gid://shopify/Company/4458774593
        # to
        # 4458774593
        #
        company_id = company.get("id", "")

        if company_id.startswith("gid://shopify/Company/"):
            company_id = company_id.split("/")[-1]

        cert_id = (
            company.get("certId") or {}
        ).get("value", "")

        sap_id = (
            company.get("sapId") or {}
        ).get("value", "")

        partner_type = (
            company.get("partnerType") or {}
        ).get("value", "")

        writer.writerow([

            row_no,

            company_id,

            company.get("name", ""),

            cert_id,

            sap_id,

            partner_type

        ])

        row_no += 1

print(
    "Partner Master Report exported successfully -> partner_master_report.csv"
)
