import numpy as np
import pandas as pd
import simulation_tool.data as dax
import simulation_tool.initialization as init
import simulation_tool.measures as ms
import simulation_tool.distance as ds
import simulation_tool.data as dax


'''
#############################################################################

DESCRIPTION BATCHING.PY
Author: Jonas Grundler (University of Edinburgh)

This module deals with the issue of how to batch and
summarizes our proposed batching.

Functions:
  - get_seed_order():        Determine seed order for batching strategies.
  - generate_new_batch():    Generate new batches using different strategies.

#############################################################################
'''


def get_seed_order(df, seed_type = "FCFS", routing = "S-Shape"):
    '''
    Determine seed order for advanced batching strategies.
    Inputs:
        df (DataFrame):          DataFrame incl. information on waiting orders
        seed_type (string):      Strategy to determine seed order:
                                    - FCFS (First come, first serve)
                                    - longest_travel_time
        routing (string):        Warehouse routing strategy
                                    - S-Shape
                                    - Largest-Gap
    Outputs:
        res:                     ID of seed order
    '''

    #SEED 1: FCFS
    if(seed_type == "FCFS"):
        res = df["order_ID"].min()

    #SEED 2: LONGEST TRAVEL TIME
    elif(seed_type == "longest_travel_time"):
        #Get candidate_IDs
        candidate_IDs = df["order_ID"].unique()
        urgent_IDs = df[df["urgent"] == 1]["order_ID"].unique()
        #If there are urgent orders, the seed is chosen among them
        if(urgent_IDs.size != 0):
            candidate_IDs = urgent_IDs

        #Initialization
        longest_travel_time = 0

        #Determine longest travel time among urgent orders
        for i in candidate_IDs:
            tour_time = ds.get_tourtime([i], df, routing = routing)
            if(tour_time > longest_travel_time):
                longest_travel_time = tour_time
                res = i

    return res




def generate_new_batch(df, criteria_df, method, c, percent, picker_capacity = 150, seed_type = 'FCFS', routing = "S-Shape"):
    '''
    Generate new batches using different batching methods.
    Valid inputs include First-Come-First-Serve (FCFS), priority/similartiy weighted combinations, flexible weighting methods, etc.

    Inputs:
        df (DataFrame):          DataFrame incl. information on waiting orders

        criteria_df (DataFrame): DataFrame incl. criteria fulfillment indicators

        method (string):         Used batching method:
                                    - FCFS (First-Come-First-Serve)
                                    - dist_prio_ratio
                                    - static_weighting
                                    - trigger_flexible_weighting
                                    - percentage_flexible_weighting

        c (float):               Range = [0;1]
                                 Weighting Parameter of similarity and priority metrics

        percent (float):         Range = [0;1]
                                 Percentage threshold for percentage_flexible_weighting

        picker_capacity (int):   Capacity of each picker

        seed_type (string):      Strategy to determine seed order:
                                    - First come, first serve (FCFS)
                                    - Longest Travel Time

        routing (string):        Warehouse routing strategy
                                    - S-Shape
                                    - Largest_Gap

    Outputs:
        batch (list):             List of orders that are included in created batch
        batch_size (int):         Size of created batch
        batch_time (float):       Time needed to collect created batch
        used_method (string):     String incl. used method (for protocol)
    '''

    #Initialize batch list and batch size
    batch = []
    batch_size = 0
    batch_time = 0
    added = 1
    used_method = ""



    ### METHOD 1: FIRST COME FIRST SERVE ########################
    if(method == "FCFS"):
        for i in df["order_ID"].unique():
            next_order = i
            next_size = df[df["order_ID"] == i]["size"].sum()

            #Check if next order still fits in current batch
            if(batch_size + next_size <= picker_capacity):
                batch.append(next_order)
                batch_size += next_size
            else:
                break
        #Calculate tourtime
        batch_time = ds.get_tourtime(batch, df, routing = routing)




    ### METHOD 2: DISTANCE PRIORITY RATIO ########################
    elif(method == "dist_prio_ratio"):
            #Determine seed order
            seed_order = get_seed_order(df, seed_type, routing = routing)
            batch.append(seed_order)
            batch_size += df[df["order_ID"] == seed_order]["size"].sum()
            batch_time = ds.get_tourtime(batch, df, routing = routing)

            while(added == 1):
                #Set added = 0 to check if batch is still created
                added = 0

                #Calculate distance-priority ratio for each order
                df = ms.update_similarities(batch, df, similar_type = "add_walkingdistance", routing = routing)
                df["score"] = df["similarity"]/df["priority"]

                #Sort dataframe: lower scores are preferred (in case of tie, urgent orders should be preferred)
                groups = df.groupby(["order_ID"]).mean()
                groups = groups.reset_index()
                groups = groups.dropna()
                groups = groups.sort_values(by = ["score", "urgent"], ascending = [True, False])

                for index, i in groups.iterrows():
                    #Determine next order and its size
                    next_order = i["order_ID"]
                    next_size = df[df["order_ID"] == next_order]["size"].sum()
                    next_time = ds.get_tourtime(batch+[next_order], df, routing = routing)

                    #Determine smallest t_left in current_batch
                    cdf = df[df["order_ID"].isin(batch+[next_order])]
                    min_t_left = cdf[cdf["t_left"] >= 0]["t_left"].min()

                    #Check if next order still fits in current batch
                    if(batch_size + next_size <= picker_capacity) and (next_time <= min_t_left):
                        batch.append(int(next_order))
                        batch_size += next_size
                        batch_time = next_time
                        added = 1
                        break




    ### METHOD 3: STATIC HYBRID SCORE ########################
    elif(method == "static_weighting"):
            #Determine seed order
            seed_order = get_seed_order(df, seed_type, routing = routing)
            batch.append(seed_order)
            batch_size += df[df["order_ID"] == seed_order]["size"].sum()
            batch_time = ds.get_tourtime(batch, df, routing = routing)

            while(added == 1):
                #Set added = 0 to check if batch is still created
                added = 0

                #Calculate hybrid score for each order
                df = ms.update_similarities(batch, df, similar_type = "total_time_savings", routing = routing)
                df["score"] = (1-c)*df["similarity"] + c*df["priority"]

                #Sort dataframe in descending order
                groups = df.groupby(["order_ID"]).mean()
                groups = groups.reset_index()
                groups = groups.dropna()
                groups = groups.sort_values(by = "score", ascending = False)

                for index, i in groups.iterrows():

                    #Determine next order and its size
                    next_order = i["order_ID"]
                    next_size = df[df["order_ID"] == next_order]["size"].sum()
                    next_time = ds.get_tourtime(batch+[next_order], df, routing = routing)

                    #Determine smallest t_left in current_batch
                    cdf = df[df["order_ID"].isin(batch+[next_order])]
                    min_t_left = cdf[cdf["t_left"] >= 0]["t_left"].min()


                    #Check if next order still fits in current batch
                    if(batch_size + next_size <= picker_capacity) and (next_time <= min_t_left):
                        batch.append(int(next_order))
                        batch_size += next_size
                        batch_time = next_time
                        added = 1
                        break




    ### METHOD 4: FLEXIBLE HYBRID SCORE (TRIGGER CRITERIA BASED) #############
    elif(method == "trigger_flexible_weighting"):
            #Determine seed order
            seed_order = get_seed_order(df, seed_type, routing = routing)
            batch.append(seed_order)
            batch_size += df[df["order_ID"] == seed_order]["size"].sum()
            batch_time = ds.get_tourtime(batch, df, routing = routing)

            #Determine c-value depending on whether urgency_criterion is fulfilled or not
            if(criteria_df["size_criterion"].all() == 1) and (criteria_df["urgency_criterion"].all() == 0):
                prio_weight = c
                sim_weight = (1-c)
                used_method = (f"Similarity-based batching (priority_weight = {prio_weight}) was applied.")
            elif(criteria_df["size_criterion"].all() == 0) and (criteria_df["urgency_criterion"].all() == 1):
                prio_weight = (1-c)
                sim_weight = c
                used_method = (f"Priority-based batching (priority_weight = {prio_weight}) was applied.")
            else:
                prio_weight = 0.5
                sim_weight = 0.5
                used_method = (f"Hybrid-based batching (priority_weight = {prio_weight}) was applied.")

            while(added == 1):
                #Set added = 0 to check if batch is still created
                added = 0

                #Calculate hybrid score for each order
                df = ms.update_similarities(batch, df, similar_type = "total_time_savings", routing = routing)
                df["score"] = sim_weight*df["similarity"] + prio_weight*df["priority"]

                #Sort dataframe in descending order
                groups = df.groupby(["order_ID"]).mean()
                groups = groups.reset_index()
                groups = groups.dropna()
                groups = groups.sort_values(by = "score", ascending = False)

                for index, i in groups.iterrows():

                    #Determine next order and its size
                    next_order = i["order_ID"]
                    next_size = df[df["order_ID"] == next_order]["size"].sum()
                    next_time = ds.get_tourtime(batch+[next_order], df, routing = routing)

                    #Determine smallest t_left in current_batch
                    cdf = df[df["order_ID"].isin(batch+[next_order])]
                    min_t_left = cdf[cdf["t_left"] >= 0]["t_left"].min()


                    #Check if next order still fits in current batch
                    if(batch_size + next_size <= picker_capacity) and (next_time <= min_t_left):
                        batch.append(int(next_order))
                        batch_size += next_size
                        batch_time = next_time
                        added = 1
                        break




    ### METHOD 5: FLEXIBLE HYBRID SCORE (PERCENTAGE BASED) #####################
    elif(method == "percentage_flexible_weighting"):
            #Determine seed order
            seed_order = get_seed_order(df, seed_type, routing = routing)
            batch.append(seed_order)
            batch_size += df[df["order_ID"] == seed_order]["size"].sum()
            batch_time = ds.get_tourtime(batch, df, routing = routing)

            #Determine c-value depending on percentage of urgent orders
            no_urgent = df[df["urgent"] == 1]["order_ID"].nunique()
            no_total = df["order_ID"].nunique()
            ratio = no_urgent/no_total

            #Determine c-value depending on whether urgency_criterion is fulfilled or not
            if(ratio >= percent):
                prio_weight = (1-c)
                sim_weight = c
                used_method = (f"Priority-based batching (priority_weight = {prio_weight}) was applied.")
            else:
                prio_weight = c
                sim_weight = (1-c)
                used_method = (f"Similarity-based batching (priority_weight = {prio_weight}) was applied.")

            while(added == 1):
                #Set added = 0 to check if batch is still created
                added = 0

                #Calculate hybrid score for each order
                df = ms.update_similarities(batch, df, similar_type = "total_time_savings", routing = routing)
                df["score"] = sim_weight*df["similarity"] + prio_weight*df["priority"]

                #Sort dataframe in descending order
                groups = df.groupby(["order_ID"]).mean()
                groups = groups.reset_index()
                groups = groups.dropna()
                groups = groups.sort_values(by = "score", ascending = False)

                for index, i in groups.iterrows():

                    #Determine next order and its size
                    next_order = i["order_ID"]
                    next_size = df[df["order_ID"] == next_order]["size"].sum()
                    next_time = ds.get_tourtime(batch+[next_order], df, routing = routing)

                    #Determine smallest t_left in current_batch
                    cdf = df[df["order_ID"].isin(batch+[next_order])]
                    min_t_left = cdf[cdf["t_left"] >= 0]["t_left"].min()


                    #Check if next order still fits in current batch
                    if(batch_size + next_size <= picker_capacity) and (next_time <= min_t_left):
                        batch.append(int(next_order))
                        batch_size += next_size
                        batch_time = next_time
                        added = 1
                        break

    return batch, batch_size, batch_time, used_method
