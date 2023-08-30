import logging
import azure.functions as func
import pandas as pd
from azure.cosmos import CosmosClient
import uuid
import os

def insert_dataframe(df):
    # Retrieve the Cosmos DB connection string from environment variables
    connection_string = os.environ['AzureCosmosDBConnectionString']

    # Create a Cosmos DB client and retrieve the container
    client = CosmosClient.from_connection_string(connection_string)
    database_name = 'Drafts'
    container_name = 'clusters'
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient='records')

    # Insert each dictionary into Cosmos DB
    for item in data:
        logging.info(item)
        item['id'] = str(uuid.uuid4())  # Generate 'id' field
        container.create_item(body=item)


def main(req: func.HttpRequest, doc: func.Out[func.Document]) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    # Get the current file's directory
    current_dir = os.path.dirname(os.path.realpath(__file__))

    # Construct the path to the excel file
    excel_file_path = os.path.join(current_dir, 'clusters.xlsx')
    # Retrieve the DataFrame from the local file
    df = pd.read_excel(excel_file_path)

    # Insert the DataFrame into Cosmos DB
    insert_dataframe(df)

    # Return a response
    return func.HttpResponse("Data inserted successfully into Cosmos DB.")
