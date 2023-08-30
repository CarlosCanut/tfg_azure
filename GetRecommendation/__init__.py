import logging
import pandas as pd
import azure.functions as func
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
    
    
def get_general_cluster(cluster, role):
    if role == "unselected":
        return -99
    if role == "top":
        return int(cluster)
    if role == "jungle":
        return int(cluster) + 4
    elif role == "mid":
        return int(cluster) + 8
    elif role == "bottom":
        return int(cluster) + 12
    elif role == "utility":
        return int(cluster) + 15
    

def get_cluster_role(cluster):
    if cluster in [0, 1, 2, 3]:
        return ["top", cluster]
    if cluster in [4, 5, 6, 7]:
        return ["jungle", (cluster - 4)]
    if cluster in [8, 9, 10, 11]:
        return ["mid", (cluster - 8)]
    if cluster in [12, 13, 14]:
        return ["bottom", (cluster - 12)]
    if cluster in [15, 16, 17]:
        return ["utility", (cluster - 15)]
    

def recommend_pick(games_df, draftRotation, draftSelection):
    for i in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
        games_df['pick'+i] = games_df.apply(lambda row: get_general_cluster(row['cluster'+i], row['role'+i]), axis=1)
        games_df = games_df.drop(columns=["role"+i, "cluster"+i])
        
    # Extract pick columns
    pick_columns = ["pick1", "pick2", "pick3", "pick4", "pick5", "pick6", "pick7", "pick8", "pick9", "pick10"]
    
    # Preprocessing
    pick_features = games_df[pick_columns]
    
    def should_exclude_pick(existing_picks, pick):
        # Define the ranges and their corresponding conditions
        ranges = [(0, 3), (4, 7), (8, 10), (11, 13)]
        conditions = [
            (len(existing_picks) % 2 == 1 and pick % 2 == 1),
            (len(existing_picks) % 2 == 1 and pick % 2 == 0),
            (len(existing_picks) % 2 == 0 and pick % 2 == 1),
            (len(existing_picks) % 2 == 0 and pick % 2 == 0)
        ]
        
        for i, (start, end) in enumerate(ranges):
            if start <= pick <= end and conditions[i]:
                return True
        return False
    
    # Define a function to recommend the next champion pick
    def recommend_next_pick(draftSelection, draftRotation, pick_features):

        # prepara los drafts almacenamos
        drafts = []
        for index, picks in pick_features.iterrows():
            draft_instance = [picks['pick1'], picks['pick2'], picks['pick3'], picks['pick4'], picks['pick5'], picks['pick6'], picks['pick7'], picks['pick8'], picks['pick9'], picks['pick10']]        
            drafts.append(draft_instance)


        target_draft = []
        for pick in draftSelection:
            target_draft.append(get_general_cluster(pick['cluster'], pick['role']))
            
        # agrupa todos los drafts junto con el que se busca recomendación
        drafts.append(target_draft)
        drafts_array = np.array(drafts)

        # se genera la matriz de similaridad del coseno, esta es cuadrada y muestra la similitud de todos con todos los drafts
        cosine_sim = cosine_similarity(drafts_array)

        # se genera un df con los valores de similitud, indice del draft con similitud hacia el draft a recomendar y la recomendación de siguiente pick
        cosine_sim = cosine_sim[:-1, -1]
        similarity_json = {
            "cosine_similarity": cosine_sim
        }
        similarity_df = pd.DataFrame(similarity_json)
        similarity_df = similarity_df.sort_values(by=['cosine_similarity'], ascending=False)
        similarity_df['recommendation'] = similarity_df.apply(lambda row: drafts[row.name][draftRotation], axis=1)

        # se obtienen todos los posibles clusters a elegir
        available_picks = [pick for pick in range(1, 18) if pick not in target_draft and not should_exclude_pick([item for item in target_draft if item != -99], pick)]

        # se busca, de mayor a menor similitud el cluster que pueda seleccionarse y se devuelve
        for index, recommendation in similarity_df.iterrows():
            if recommendation['recommendation'] in available_picks:
                return int(recommendation['recommendation'])
            
    recommended_pick = recommend_next_pick(draftSelection, draftRotation, pick_features)
    return get_cluster_role(recommended_pick)


    

def find_most_repeated_role(df, draftRotation, draftSelection):
    games_df = pd.DataFrame()
    filtered_df = pd.DataFrame()
    
    roles_values = {}
    clusters_values = {}
    for pickIndex in range(0, draftRotation):
        role_column_name = 'role' + str(pickIndex + 1)
        cluster_column_name = 'cluster' + str(pickIndex + 1)
        roles_values[role_column_name] = draftSelection[pickIndex]['role']
        clusters_values[cluster_column_name] = int(draftSelection[pickIndex]['cluster'])
    
    
    role_condition = True
    for column, role in roles_values.items():
        role_condition &= (df[column] == role)
    games_df = df[role_condition]
    
    
    
    cluster_condition = True
    for column, cluster in clusters_values.items():
        cluster_condition &= (df[column] == cluster)
    filtered_df = df[cluster_condition]
    
    
    if not filtered_df.empty:
        most_repeated_cluster = filtered_df['cluster' + str(draftRotation)].mode().iloc[0]
        most_repeated_role = filtered_df['role' + str(draftRotation)].mode().iloc[0]
        return [most_repeated_role, str(most_repeated_cluster)]
    else:
        calculation = None
        for column, cluster in clusters_values.items():
            step = (games_df[column] - cluster) ** 2
            if calculation is None:
                calculation = step
            else:
                calculation += step
        
        idx_min = calculation.idxmin()
        closest_combination = games_df.iloc[idx_min]
        return [closest_combination['role' + str(draftRotation)], str(closest_combination['cluster' + str(draftRotation)])]


# {
#     "draftRotation": 2,
#     "draftSelection": [{"cluster": "4", "role": "top"}, {"cluster": "3", "role": "jungle"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}, {"cluster": "", "role": "unselected"}]
# } ->
def main(req: func.HttpRequest, doc:func.DocumentList) -> func.HttpResponse:
    
    req_body = req.get_json()
    
    items = []
    for document in doc:
        items.append(document.to_dict())

    df = pd.DataFrame(items)
    
    result = recommend_pick(df, req_body['draftRotation'], req_body['draftSelection'])
    
    # result = find_most_repeated_role(df, req_body['draftRotation'], req_body['draftSelection'])

    response_raw = {"recommendation": result}
    response = json.dumps(response_raw)

    return func.HttpResponse(response, mimetype="application/json")
