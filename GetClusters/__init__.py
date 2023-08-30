import logging
import pandas as pd
import azure.functions as func
import json

def main(req: func.HttpRequest, doc:func.DocumentList) -> func.HttpResponse:
    
    items = []
    for document in doc:
        items.append(document.to_dict())

    df = pd.DataFrame(items)

    return func.HttpResponse(df.to_json(orient="records"), mimetype="application/json")
