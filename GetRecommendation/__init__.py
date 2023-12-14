import logging
import pandas as pd
import azure.functions as func
import json
import numpy as np
from scipy.stats import mode
    
    
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
            
        
            
        def find_arrays_with_same_prefix(desired_array, array_list, n):
            desired_prefix = desired_array[:n]
            matching_arrays = [arr for arr in array_list if np.array_equal(arr[:n], desired_prefix)]
            return matching_arrays
        
        def get_mode_at_position(array_of_arrays, position):
            values_at_position = [arr[position] for arr in array_of_arrays]
            result = mode(values_at_position)
            return result.mode.item()
        
        drafts_with_same_picks = find_arrays_with_same_prefix(target_draft, drafts, draftRotation - 1)
        
        if len(drafts_with_same_picks) > 0:
            most_common_cluster = get_mode_at_position(drafts_with_same_picks, draftRotation - 1)
            return most_common_cluster
        else:
            # if there is no similar drafts, gets the most common pick for that pick turn
            most_common_cluster = get_mode_at_position(drafts, draftRotation - 1)
            return most_common_cluster
        
        
            
    recommended_pick = recommend_next_pick(draftSelection, draftRotation, pick_features)
    return get_cluster_role(recommended_pick)


    
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
    

    response_raw = {"recommendation": result}
    response = json.dumps(response_raw)

    return func.HttpResponse(response, mimetype="application/json")
