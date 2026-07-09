import os
import requests
from rdflib import Graph, Namespace, URIRef, Literal


DATABUS_ENDPOINT = "https://databus.dbpedia.org/sparql"

MOSS_ENDPOINT = "https://moss.dev.dbpedia.link"

KG_CATALOG = "https://databus.dbpedia.org/knowledge-graph-catalog"


DATACATALOG = Namespace("http://www.w3.org/ns/dcat#")


MOSS_KEY = os.environ["MOSS_KG_CATALOG"]



def sparql(query):
    """
    Execute SPARQL query against Databus
    """

    r = requests.get(
        DATABUS_ENDPOINT,
        params={
            "query": query,
            "format": "json"
        },
        timeout=60
    )

    r.raise_for_status()

    return r.json()



def get_kgs():

    query = f"""
PREFIX databus: <https://dataid.dbpedia.org/databus#>

SELECT DISTINCT ?kg
WHERE {{
    ?kg databus:account <{KG_CATALOG}> .
    ?kg a databus:Group .
}}
"""

    result = sparql(query)

    return [
        x["kg"]["value"]
        for x in result["results"]["bindings"]
    ]



def get_latest_size(kg):

    query = f"""
PREFIX databus: <https://dataid.dbpedia.org/databus#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?latestVersion (SUM(?size) AS ?totalBytes)
WHERE {{

  {{
    SELECT ?latestVersion
    WHERE {{
        ?version databus:group <{kg}> ;
                 dct:hasVersion ?latestVersion .
    }}
    ORDER BY DESC(STR(?latestVersion))
    LIMIT 1
  }}

  ?version databus:group <{kg}> ;
           dct:hasVersion ?latestVersion ;
           dcat:distribution ?distribution .

  ?distribution dcat:byteSize ?size .

}}
GROUP BY ?latestVersion
"""


    result = sparql(query)


    bindings = result["results"]["bindings"]

    if not bindings:
        return None


    return int(
        bindings[0]["totalBytes"]["value"]
    )



def get_moss_metadata(kg):

    url = (
        f"{MOSS_ENDPOINT}/entries/"
        f"{kg.replace('https://','')}"
        "/kg-metadata"
    )


    r = requests.get(
        url,
        headers={
            "Accept": "text/turtle"
        },
        timeout=60
    )

    r.raise_for_status()

    return r.text



def update_byte_size(turtle, kg, size):

    g = Graph()

    g.parse(
        data=turtle,
        format="turtle"
    )


    subject = URIRef(kg)

    # remove existing values

    g.remove(
        (
            subject,
            DATACATALOG.byteSize,
            None
        )
    )


    # add new value

    g.add(
        (
            subject,
            DATACATALOG.byteSize,
            Literal(str(size))
        )
    )


    return g.serialize(
        format="turtle"
    )



def publish_to_moss(kg, turtle):

    url = (
        f"{MOSS_ENDPOINT}"
        f"/api/v1/save-entry"
        f"?module=kg-metadata"
        f"&resource={kg}/"
    )


    r = requests.post(
        url,
        headers={
            "accept": "application/json",
            "X-API-KEY": MOSS_KEY,
            "Content-Type": "text/turtle"
        },
        data=turtle,
        timeout=60
    )


    if not r.ok:
        print(r.text)

    r.raise_for_status()



def main():

    print("Retrieving KG catalog...")

    kgs = get_kgs()

    print(f"Found {len(kgs)} KGs")


    for kg in kgs:

        try:

            print("\nProcessing:", kg)


            size = get_latest_size(kg)


            if size is None:
                print("No size information")
                continue


            print(
                "Latest size:",
                size
            )


            moss_data = get_moss_metadata(kg)


            updated = update_byte_size(
                moss_data,
                kg,
                size
            )


            publish_to_moss(
                kg,
                updated
            )


            print("Published successfully")


        except Exception as e:

            print(
                "FAILED:",
                kg,
                e
            )



if __name__ == "__main__":
    main()
