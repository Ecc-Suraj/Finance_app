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


# ---------------------------------------------------------
# Generic GraphQL Function
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
query GetProducts($cursor: String){

  products(
    first:250,
    after:$cursor,
    query:"status:ACTIVE"
  ){

    pageInfo{
      hasNextPage
      endCursor
    }

    nodes{

      id

      title

      productCode: metafield(
        namespace:"custom"
        key:"product_code"
      ){
        value
      }

      productType: metafield(
        namespace:"custom"
        key:"ec_council_product_type"
      ){
        value
      }

      productCategory: metafield(
        namespace:"custom"
        key:"ec_council_product_category"
      ){
        value
      }

      variants(first:1){
        nodes{
          id
        }
      }

    }

  }

}
"""


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

    products = data["products"]["nodes"]

    all_products.extend(products)

    page_info = data["products"]["pageInfo"]

    if not page_info["hasNextPage"]:
        break

    cursor = page_info["endCursor"]

    time.sleep(0.3)

print(f"Products Found : {len(all_products)}")


# ---------------------------------------------------------
# FETCH ALL CATALOGS
# ---------------------------------------------------------

CATALOG_QUERY = """
{

  catalogs(first:100){

    nodes{

      id

      title

      ... on CompanyLocationCatalog{

        priceList{

          id

          name

        }

      }

    }

  }

}
"""

print("Fetching Catalogs...")

catalog_data = graphql(CATALOG_QUERY)

catalogs = catalog_data["catalogs"]["nodes"]


# ---------------------------------------------------------
# MARKET BUCKETS
# ---------------------------------------------------------

USA_CATALOGS = {
    "USA- Academia",
    "USA- ATC",
    "USA- Reseller"
}

CANADA_CATALOGS = {
    "Canada- Academia",
    "Canada- ATC",
    "Canada- Reseller"
}

LATAM_CATALOGS = {
    "LATAM- Academia"
}


usa_price_lists = []

canada_price_lists = []

latam_price_lists = []


for catalog in catalogs:

    title = catalog["title"]

    price_list = catalog.get("priceList")

    if not price_list:
        continue

    if title in USA_CATALOGS:

        usa_price_lists.append(price_list["id"])

        print("USA :", title)

    elif title in CANADA_CATALOGS:

        canada_price_lists.append(price_list["id"])

        print("Canada :", title)

    elif title in LATAM_CATALOGS:

        latam_price_lists.append(price_list["id"])

        print("LATAM :", title)


print()

print("USA Price Lists :", len(usa_price_lists))
print("Canada Price Lists :", len(canada_price_lists))
print("LATAM Price Lists :", len(latam_price_lists))

print()

# ---------------------------------------------------------
# PRICE LIST QUERY
# ---------------------------------------------------------

PRICE_LIST_QUERY = """
query GetPriceList(
    $priceListId: ID!,
    $cursor: String
){

  priceList(id:$priceListId){

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
# FETCH ALL PRICES FROM ONE PRICE LIST
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

        price_list = data["priceList"]

        if not price_list:
            break

        result = price_list["prices"]

        for node in result["nodes"]:

            variant = node.get("variant")

            if not variant:
                continue

            variant_id = variant["id"]

            price = node["price"]["amount"]

            prices[variant_id] = price

        if not result["pageInfo"]["hasNextPage"]:
            break

        cursor = result["pageInfo"]["endCursor"]

        time.sleep(0.2)

    return prices


# ---------------------------------------------------------
# BUILD MARKET DICTIONARIES
# ---------------------------------------------------------

usa_prices = {}

canada_prices = {}

latam_prices = {}


print()

print("Loading USA Catalog Prices...")

for price_list_id in usa_price_lists:

    print(price_list_id)

    data = fetch_price_list(price_list_id)

    usa_prices.update(data)


print()

print("Loading Canada Catalog Prices...")

for price_list_id in canada_price_lists:

    print(price_list_id)

    data = fetch_price_list(price_list_id)

    canada_prices.update(data)


print()

print("Loading LATAM Catalog Prices...")

for price_list_id in latam_price_lists:

    print(price_list_id)

    data = fetch_price_list(price_list_id)

    latam_prices.update(data)


print()

print("------------------------------------")
print("USA Products :", len(usa_prices))
print("Canada Products :", len(canada_prices))
print("LATAM Products :", len(latam_prices))
print("------------------------------------")

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

    writer.writerow([
        "S. No.",
        "Shopify ID",
        "Product Code",
        "Product Name",
        "Product Type",
        "Product Category",
        "USA Price",
        "Canada Price",
        "LATAM Price"
    ])

    row_no = 1

    for product in all_products:

        product_code = (
            product.get("productCode") or {}
        ).get("value", "")

        product_type = (
            product.get("productType") or {}
        ).get("value", "")

        product_category = (
            product.get("productCategory") or {}
        ).get("value", "")

        variants = (
            product.get("variants") or {}
        ).get("nodes", [])

        variant_id = ""

        if variants:
            variant_id = variants[0]["id"]

        shopify_id = product["id"].split("/")[-1]

        usa_price = usa_prices.get(
            variant_id,
            "NA"
        )

        canada_price = canada_prices.get(
            variant_id,
            "NA"
        )

        latam_price = latam_prices.get(
            variant_id,
            "NA"
        )

        writer.writerow([

            row_no,

            shopify_id,

            product_code,

            product.get("title", ""),

            product_type,

            product_category,

            usa_price,

            canada_price,

            latam_price

        ])

        row_no += 1


print()

print("-------------------------------------")
print("Product Master Report Exported Successfully")
print("File : product_master_report.csv")
print("-------------------------------------")
