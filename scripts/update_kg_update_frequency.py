import os
import requests
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import XSD


DATABUS_ENDPOINT = "https://databus.dbpedia.org/sparql"

MOSS_ENDPOINT = "https://moss.dev.dbpedia.link"

KG_CATALOG = "https://databus.dbpedia.org/knowledge-graph-catalog"

MOSS = Namespace("https://moss.dev.dbpedia.link/ontology/")

MOSS_KEY = os.environ["MOSS_KG_CATALOG"]


def sparql(query):
    """
    Execute SPARQL query against Databus
    """

    print("\n========== SPARQL REQUEST ==========")
    print(query)

    r = requests.get(
        DATABUS_ENDPOINT,
        params={
            "query": query,
            "format": "json"
        },
        timeout=60
    )

    print("STATUS:", r.status_code)

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


def get_updates_last_180_days(kg):

    query = f"""
PREFIX databus: <https://dataid.dbpedia.org/databus#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT (COUNT(DISTINCT ?versionNum) AS ?updatesLast180Days)
WHERE {{

  ?version databus:group <{kg}> ;
           dct:hasVersion ?versionNum ;
           dct:issued ?issued .

  FILTER(?issued >= NOW() - "P180D"^^xsd:dayTimeDuration)

}}
"""

    result = sparql(query)

    bindings = result["results"]["bindings"]

    if not bindings:
        return 0

    return int(bindings[0]["updatesLast180Days"]["value"])


def get_moss_metadata(kg):

    url = (
        f"{MOSS_ENDPOINT}/entries/"
        f"{kg.replace('https://','')}"
        "/kg-metadata"
    )

    headers = {
        "Accept": "text/turtle"
    }

    print("\n========== MOSS GET REQUEST ==========")
    print(url)

    r = requests.get(
        url,
        headers=headers,
        timeout=60
    )

    print("STATUS:", r.status_code)

    r.raise_for_status()

    return r.text


def update_frequency(turtle, kg, updates):

    g = Graph()

    g.parse(
        data=turtle,
        format="turtle"
    )

    subject = URIRef(kg)

    print("Removing existing moss:updatesLast180Days")

    g.remove(
        (
            subject,
            MOSS.updatesLast180Days,
            None
        )
    )

    print(
        "Adding moss:updatesLast180Days =",
        updates
    )

    g.add(
        (
            subject,
            MOSS.updatesLast180Days,
            Literal(
                updates,
                datatype=XSD.integer
            )
        )
    )

    updated = g.serialize(
        format="turtle"
    )

    print(updated)

    return updated


def publish_to_moss(kg, turtle):

    url = (
        f"{MOSS_ENDPOINT}"
        f"/api/v1/save-entry"
        f"?module=kg-metadata"
        f"&resource={kg}/"
    )

    headers = {
        "accept": "application/json",
        "X-API-KEY": MOSS_KEY,
        "Content-Type": "text/turtle"
    }

    r = requests.post(
        url,
        headers=headers,
        data=turtle,
        timeout=60
    )

    print("STATUS:", r.status_code)
    print(r.text)

    r.raise_for_status()


def main():

    print("Retrieving KG catalog...")

    kgs = get_kgs()

    print(f"Found {len(kgs)} KGs")

    for kg in kgs:

        try:

            print("\n================================")
            print("Processing:", kg)
            print("================================")

            updates = get_updates_last_180_days(kg)

            print(
                "Updates in last 180 days:",
                updates
            )

            turtle = get_moss_metadata(kg)

            updated = update_frequency(
                turtle,
                kg,
                updates
            )

            publish_to_moss(
                kg,
                updated
            )

            print(
                "Published successfully:",
                kg
            )

        except Exception as e:

            print(
                "FAILED:",
                kg,
                e
            )


if __name__ == "__main__":
    main()