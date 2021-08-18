import pandas as pd
import numpy as np
import simulation_tool.data as dax

'''
#############################################################################

DESCRIPTION DISTANCE.PY
Author: Jonas Grundler (University of Edinburgh)

In this package, the routing strategies applied in our experiments are implemented.
Specifically, users can choose between ’S-Shape’ and ’Largest Gap’ routing.

    Functions:
      - get_distance():      Get distance of picker tour (using different routing strategies).
      - get_tourtime():      Get processing time of picker tour (using different routing strategies).


#############################################################################
'''

def get_distance(batch, df, routing = "S-Shape", aisle_no = 10, aisle_length = 45, aisle_between = 5):
    '''
    Get distance of picker tour (using different routing strategies).

    Inputs:
        picking_df (DataFrame):     DataFrame containing on information items to be picked

        routing (string):           Warehouse routing strategy
                                        - S-Shape
                                        - Largest-Gap

        aisle_no (int):             No. of aisles in warehouse

        aisle_length (int):         Length of aisles in warehouse

        aisle_between (int):        Distance between two aisles

    Outputs:
        distance (int):             Distance of picker tour
    '''
    #Initialization
    distance = 0
    picking_df = df[df["order_ID"].isin(batch)]
    visited_aisles = picking_df["x_coord"].nunique()
    first_aisle = picking_df["x_coord"].min()
    last_aisle = int(picking_df["x_coord"].max())

    #ROUTING STRATEGY I: S-SHAPED ROUTING
    if(routing == "S-Shape"):
        distance += visited_aisles * aisle_length
        distance += 2*last_aisle*aisle_between

        if(visited_aisles % 2 == 1):
            d = picking_df[picking_df["x_coord"] == last_aisle]
            last_item = d["y_coord"].max()
            distance += 2*last_item - aisle_length

    #ROUTING STRATEGY II: LARGEST GAP ROUTING
    elif(routing == "Largest-Gap"):
        if(visited_aisles == 1):
            d = picking_df[picking_df["x_coord"] == last_aisle]
            last_item = d["y_coord"].max()
            distance += 2*last_item
            distance += 2*last_aisle*aisle_between

        else:
            distance += 2*aisle_length
            distance += 2*last_aisle*aisle_between

            #Get all aisles (excl. first and last one)
            middle_aisles = picking_df["x_coord"].unique().tolist()
            middle_aisles.remove(min(middle_aisles))
            middle_aisles.remove(max(middle_aisles))

            #Identify largest_gap for each middle aisle
            for i in middle_aisles:
                d = picking_df[picking_df["x_coord"] == i]
                y_coords = d["y_coord"].tolist()
                y_coords = sorted(y_coords + [0,aisle_length])
                gaps = []
                for j in range(len(y_coords)-1):
                    gaps = gaps+[y_coords[j+1] - y_coords[j]]
                largest_gap = max(gaps)
                distance += 2*(aisle_length - largest_gap)

    return distance


def get_tourtime(batch, df, travel_speed = 48, pick_speed = 6, packup_time = 3, routing = "S-Shape"):
    '''
    Get total processing time of a particular batch (incl. travel time,
    picking time and unloading/preparation time).

    Inputs:
        batch (list):           List of orders included in current batch

        df (DataFrame):         DataFrame incl. information on waiting orders

        travel_speed (int):     Travel speed of picker (in m/min)

        pick_speed (int):       Pick speed of picker (in items/min)

        packup_time (int):      Constant time for packing (in min)

        routing (string):       Warehouse routing strategy
                                    - S-Shape
                                    - Largest-Gap
    Outputs:
        total_time (float):     Total time needed to process current batch
    '''

    df = df[df["order_ID"].isin(batch)]

    total_no_of_items = df["order_ID"].count()
    dist = get_distance(batch, df, routing)

    #Calculate time components
    travel_time = dist/travel_speed
    pick_time = total_no_of_items/pick_speed

    #Calculate total time
    total_time = travel_time + pick_time + packup_time

    return total_time
