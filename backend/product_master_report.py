from dotenv import load_dotenv
load_dotenv()

import os
import csv
import time
import requests


# ---------------------------------------------------------
# SHOPIFY CONFIGURATION
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# GENERIC GRAPHQL FUNCTION
# ---------------------------------------------------------

def graphql(query, variables=None):

    response = requests.post(
        URL,
        headers=HEADERS,
        json={
            "query": query,
            "variables": variables or {}
        }
    )

    if response.status_code != 200:
        raise Exception(
            f"HTTP Error {response.status_code}: {response.text}"
        )

    data = response.json()

    if "errors" in data:
        raise Exception(data["errors"])

    return data["data"]


# ---------------------------------------------------------
# PRODUCT QUERY
# ---------------------------------------------------------

PRODUCT_QUERY = """
query GetProducts($cursor: String) {

  products(
    first: 250,
    after: $cursor,
    query: "status:ACTIVE"
  ) {

    pageInfo {
      hasNextPage
      endCursor
    }

    nodes {

      id

      title

      productCode: metafield(
        namespace: "custom"
        key: "product_code"
      ) {
        value
      }

      skuMeta: metafield(
        namespace: "custom"
        key: "zoho_id"
      ) {
        value
      }

      variants(first: 1) {
        nodes {
          id
          sku
        }
      }

      productTypeMeta: metafield(
        namespace: "custom"
        key: "ec_council_product_type"
      ) {
        value
      }

      productCategoryMeta: metafield(
        namespace: "custom"
        key: "ec_council_product_category"
      ) {
        value
      }

    }

  }

}
"""


# ---------------------------------------------------------
# FETCH ACTIVE CATALOGS
# ---------------------------------------------------------

CATALOG_QUERY = """
{
  catalogs(first: 100) {
    nodes {

      id

      title

      ... on CompanyLocationCatalog {

        priceList {
          id
          name
        }

      }

    }
  }
}
"""


# ---------------------------------------------------------
# PRICE LIST QUERY
# ---------------------------------------------------------

PRICE_LIST_QUERY = """
query GetPriceList(
    $priceListId: ID!,
    $cursor: String
){

  priceList(id: $priceListId){

    id

    name

    prices(
      first:250,
      after:$cursor
    ){

      pageInfo{
        hasNextPage
        endCursor
      }

      nodes{

        variant{
          id
        }

        price{
          amount
        }

      }

    }

  }

}
"""


# ---------------------------------------------------------
# CATALOG PRODUCT QUERY
# ---------------------------------------------------------

CATALOG_PRODUCTS_QUERY = """
query GetCatalogProducts(
    $catalogId: ID!,
    $cursor: String
){

  catalog(id:$catalogId){

    ... on CompanyLocationCatalog{

      publication{

        includedProducts(
          first:250,
          after:$cursor
        ){

          pageInfo{
            hasNextPage
            endCursor
          }

          nodes{

            id

            variants(first:250){
              nodes{
                id
              }
            }

          }

        }

      }

    }

  }

}
"""


# ---------------------------------------------------------
# FETCH PRICE LIST
# ---------------------------------------------------------

def fetch_price_list(price_list_id):

    prices = {}

    cursor = None

    while True:

        data = graphql(
            PRICE_LIST_QUERY,
            {
                "priceListId": price_list_id,
                "cursor": cursor
            }
        )

        price_list = data.get("priceList")

        if not price_list:
            break

        result = price_list["prices"]

        for node in result["nodes"]:

            variant = node.get("variant")

            if not variant:
                continue

            prices[
                variant["id"]
            ] = node["price"]["amount"]

        if not result["pageInfo"]["hasNextPage"]:
            break

        cursor = result["pageInfo"]["endCursor"]

        time.sleep(0.2)

    return prices


# ---------------------------------------------------------
# FETCH PRODUCTS INCLUDED IN A CATALOG
# ---------------------------------------------------------

def fetch_catalog_products(catalog_id):

    variants = set()

    cursor = None

    while True:

        data = graphql(
            CATALOG_PRODUCTS_QUERY,
            {
                "catalogId": catalog_id,
                "cursor": cursor
            }
        )

        catalog = data.get("catalog")

        if not catalog:
            break

        publication = catalog.get("publication")

        if not publication:
            break

        result = publication["includedProducts"]

        for product in result["nodes"]:

            for variant in product["variants"]["nodes"]:

                variants.add(
                    variant["id"]
                )

        if not result["pageInfo"]["hasNextPage"]:
            break

        cursor = result["pageInfo"]["endCursor"]

        time.sleep(0.2)

    return variants
def generate_product_master_report():

    # ---------------------------------------------------------
    # FETCH PRODUCTS
    # ---------------------------------------------------------

    print("Fetching Products...")

    all_products = []

    cursor = None

    while True:

        data = graphql(
            PRODUCT_QUERY,
            {
                "cursor": cursor
            }
        )

        all_products.extend(
            data["products"]["nodes"]
        )

        page_info = data["products"]["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]

        time.sleep(0.3)

    print(f"Products Found : {len(all_products)}")


    # ---------------------------------------------------------
    # FETCH ACTIVE CATALOGS
    # ---------------------------------------------------------

    print()
    print("Fetching Active Catalogs...")

    catalog_data = graphql(CATALOG_QUERY)

    catalogs = catalog_data["catalogs"]["nodes"]

    catalog_price_lists = {}

    for catalog in catalogs:

        price_list = catalog.get("priceList")

        if not price_list:
            continue

        title = catalog["title"]

        catalog_price_lists[title] = {
            "catalog_id": catalog["id"],
            "price_list_id": price_list["id"],
            "price_list_name": price_list["name"]
        }

        print(f"Found Catalog : {title}")

    print()
    print("--------------------------------------")
    print(f"Total Catalogs : {len(catalog_price_lists)}")
    print("--------------------------------------")


    # ---------------------------------------------------------
    # LOAD ALL PRICE LISTS
    # ---------------------------------------------------------

    print()
    print("Loading Catalog Prices...")

    catalog_prices = {}
    catalog_products = {}
    price_list_cache = {}

    for catalog_name, info in catalog_price_lists.items():

        catalog_id = info["catalog_id"]
        price_list_id = info["price_list_id"]

        print(f"Catalog     : {catalog_name}")
        print(f"Price List  : {info['price_list_name']}")
        print(f"PriceListID : {price_list_id}")

        # -----------------------------------------
        # Load Price List (cached)
        # -----------------------------------------

        if price_list_id not in price_list_cache:

            price_list_cache[price_list_id] = fetch_price_list(
                price_list_id
            )

        catalog_prices[catalog_name] = price_list_cache[
            price_list_id
        ]

        # -----------------------------------------
        # Load Products Assigned to Catalog
        # -----------------------------------------

        catalog_products[catalog_name] = fetch_catalog_products(
            catalog_id
        )

        print(
            f"Variants in Price List : "
            f"{len(catalog_prices[catalog_name])}"
        )

        print(
            f"Products in Catalog : "
            f"{len(catalog_products[catalog_name])}"
        )

        print("--------------------------------")

        time.sleep(0.2)

    print()
    print("--------------------------------------")
    print("All Catalog Data Loaded Successfully")
    print("--------------------------------------")

        # ---------------------------------------------------------
    # EXPORT CSV
    # ---------------------------------------------------------

    print()
    print("Generating Product Master Report...")

    with open(
        "product_master_report.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csvfile:

        writer = csv.writer(csvfile)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        headers = [
            "S. No.",
            "Shopify ID",
            "Product Code",
            "SKU",
            "Zoho ID",
            "Product Name",
            "Product Type",
            "Product Category"
        ]

        catalog_names = sorted(
            catalog_price_lists.keys()
        )

        headers.extend(catalog_names)

        writer.writerow(headers)

        row_no = 1

        # -------------------------------------------------
        # PRODUCTS
        # -------------------------------------------------

        for product in all_products:

            shopify_id = product["id"].split("/")[-1]

            product_code = (
                product.get("productCode") or {}
            ).get("value", "")

            sku = (
                product.get("skuMeta") or {}
            ).get("value", "")

            product_type = (
                product.get("productTypeMeta") or {}
            ).get("value", "")

            product_category = (
                product.get("productCategoryMeta") or {}
            ).get("value", "")

            variants = (
                product.get("variants") or {}
            ).get("nodes", [])

            variant_id = None
            zoho_id = ""

            if variants:
                variant_id = variants[0]["id"]
                zoho_id = variants[0].get(
                    "sku",
                    ""
                )

            # -----------------------------------------
            # Catalog Prices
            # -----------------------------------------

            catalog_values = []

            for catalog_name in catalog_names:

                # Product has no variant

                if variant_id is None:
                    catalog_values.append("NA")
                    continue

                # Product not assigned to catalog

                if (
                    variant_id
                    not in catalog_products[catalog_name]
                ):
                    catalog_values.append("NA")
                    continue

                # Product belongs to catalog

                price = catalog_prices[catalog_name].get(
                    variant_id,
                    "NA"
                )

                catalog_values.append(price)

            writer.writerow([

                row_no,

                shopify_id,

                product_code,

                sku,

                zoho_id,

                product.get("title", ""),

                product_type,

                product_category,

                *catalog_values

            ])

            row_no += 1

    print()
    print("--------------------------------------")
    print("Product Master Report Generated Successfully")
    print("--------------------------------------")
    print(f"Total Products Exported : {row_no - 1}")
    print("Output File : product_master_report.csv")
    print("--------------------------------------")

    return "product_master_report.csv"


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    try:
        generate_product_master_report()

    except Exception as e:
        print()
        print("--------------------------------------")
        print("ERROR")
        print("--------------------------------------")
        print(str(e))
        raise