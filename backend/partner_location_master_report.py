from dotenv import load_dotenv
load_dotenv()

import os
import csv
import time
import argparse
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
query GetCompanies($cursor: String) {

  companies(
    first: 10,
    after: $cursor
  ) {

    pageInfo {
      hasNextPage
      endCursor
    }

    nodes {

      locations(first: 10) {

        nodes {

          id
          name
          totalSpent {
            amount
            currencyCode
        }

        storeCreditAccounts(first: 1) {
            nodes {
                balance {
                amount
                currencyCode
                }
            }
        }

          billingAddress {
            address1
            address2
            city
            province
            country
            countryCode
            zip
          }

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

          partnerType: metafield(
            namespace: "custom"
            key: "assign_partner_type"
          ) {
            value
          }

          salesRepName: metafield(
            namespace: "custom"
            key: "sales_rep_full_name"
          ) {
            value
          }

          salesRepCode: metafield(
            namespace: "custom"
            key: "sales_rep_owner_code"
          ) {
            value
          }

          paymentTerms: metafield(
            namespace: "custom"
            key: "original_payment_term"
          ) {
            value
          }

          roleAssignments(first: 10) {

            nodes {

              companyContact {

                customer {

                  email
                  firstName
                  lastName

                }

              }

            }

          }

        }

      }

    }

  }

}
"""


def get_metafield_value(node, field_name):
    """
    Safely returns the metafield value.
    """
    return (node.get(field_name) or {}).get("value", "")


def clean_location_id(gid):
    """
    Converts:
    gid://shopify/CompanyLocation/123456789

    into:

    123456789
    """
    if not gid:
        return ""

    return gid.replace(
        "gid://shopify/CompanyLocation/",
        ""
    )


def unique_emails(role_assignments):
    """
    Returns unique emails while preserving order.
    """
    emails = []
    seen = set()

    for assignment in role_assignments:

        company_contact = (
            assignment.get("companyContact") or {}
        )

        customer = (
            company_contact.get("customer") or {}
        )

        email = customer.get("email")

        if email and email not in seen:
            seen.add(email)
            emails.append(email)

    return ", ".join(emails)


def build_address(billing):

    if not billing:
        return ""

    address = []

    if billing.get("address1"):
        address.append(billing["address1"])

    if billing.get("address2"):
        address.append(billing["address2"])

    return ", ".join(address)
def generate_partner_location_master_report():

    all_companies = []

    cursor = None

    #
    # Fetch all companies using pagination
    #
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

        company_data = (
            data.get("data", {})
                .get("companies", {})
        )

        companies = company_data.get("nodes", [])

        all_companies.extend(companies)

        page_info = company_data.get("pageInfo", {})

        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

        time.sleep(0.5)

    print(
        f"Companies Retrieved : {len(all_companies)}"
    )

    output_file = "partner_location_master_report.csv"

    with open(

        output_file,

        "w",

        newline="",

        encoding="utf-8-sig"

    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([

            "S. No.",

            "Shopify Partner ID",

            "Location Name",

            "Cert ID",

            "SAP ID",

            "Partner Type",

            "Email ID",

            "Amount",

            "Store Credits",

            "Billing Address",

            "Billing City",

            "Billing State",

            "Billing Country",

            "Billing Country code",

            "Billing Zip Code",

            "Sales Rep. Name",

            "Sales Rep. Emp Code",

            "Payment Terms"

        ])

        row_no = 1

                #
        # Process every company and every location
        #
        for company in all_companies:

            locations = (
                company.get("locations") or {}
            ).get("nodes", [])

            for location in locations:

                #
                # Location Details
                #
                location_id = clean_location_id(
                    location.get("id")
                )

                location_name = location.get(
                    "name",
                    ""
                )
                total_spent = (
                    location.get("totalSpent") or {}
                ).get("amount", "")

                store_credit = ""

                credit_accounts = (
                    location.get("storeCreditAccounts") or {}
                ).get("nodes", [])

                if credit_accounts:

                    store_credit = (
                        credit_accounts[0]
                        .get("balance", {})
                        .get("amount", "")
                    )


                billing = (
                    location.get("billingAddress") or {}
                )

                billing_address = build_address(billing)

                billing_city = billing.get(
                    "city",
                    ""
                )

                billing_state_name = billing.get(
                    "province",
                    ""
                )

                billing_state = ""

                billing_country_name = billing.get(
                    "country",
                    ""
                )

                billing_country = billing.get(
                    "countryCode",
                    ""
                )

                billing_zip = billing.get(
                    "zip",
                    ""
                )

                #
                # Metafields
                #
                cert_id = get_metafield_value(
                    location,
                    "certId"
                )

                sap_id = get_metafield_value(
                    location,
                    "sapId"
                )

                partner_type = get_metafield_value(
                    location,
                    "partnerType"
                )

                sales_rep_name = get_metafield_value(
                    location,
                    "salesRepName"
                )

                sales_rep_code = get_metafield_value(
                    location,
                    "salesRepCode"
                )

                payment_terms = get_metafield_value(
                    location,
                    "paymentTerms"
                )

                #
                # Emails
                #
                role_assignments = (
                    location.get("roleAssignments") or {}
                ).get("nodes", [])

                emails = unique_emails(
                    role_assignments
                )

                #
                # Write CSV Row
                #
                writer.writerow([

                    row_no,

                    location_id,

                    location_name,

                    cert_id,

                    sap_id,

                    partner_type,

                    emails,

                    total_spent,

                    store_credit,

                    billing_address,

                    billing_city,

                    billing_state_name,

                    billing_country_name,

                    billing_country,

                    billing_zip,

                    sales_rep_name,

                    sales_rep_code,

                    payment_terms

                ])

                row_no += 1
        print(
        f"Partner Location Master Report exported successfully -> {output_file}"
    )

    return output_file


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Export Shopify Partner Location Master Report"
    )

    parser.parse_args()

    generate_partner_location_master_report()