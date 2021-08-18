import pandas as pd
import numpy as np
import simulation_tool.data as dax
import simulation_tool.distance as ds


'''
#############################################################################

DESCRIPTION MEASURES.PY
Author: Jonas Grundler (University of Edinburgh)

This package contains a composition of different functions
regarding the similarity, urgency/priority and size measures used in our simulation.

Functions:
     - update_similarities():       Update similarity values of currently waiting orders
     - priority_function():         Piecewise linear function to describe priority of orders
     - update_priorities():         Update priority scores of currently waiting orders
     - check_urgency_criterion():   Check if urgency-based triggering criterion is fulfilled
     - check_size_criterion():      Check if size-based triggering criterion is fulfilled

#############################################################################
'''



######################## SIMILARITY

def update_similarities(current_batch, df, similar_type, routing = "S-Shape"):
    '''
    Update similarity values of currently waiting orders acc. to current batch.

    Inputs:
        current_batch (list):    List of orders included in current batch
        df (DataFrame):          DataFrame incl. information on all waiting orders

    Outputs:
        df (DataFrame):          DataFrame with updated similiarities
    '''
    #Reset old similarity values
    df["similarity"] = np.nan

    #METHOD I: ADDITIONAL DISTANCE/WALKING TIME
    if(similar_type == "add_walkingdistance"):

        #Get distance of current picking list
        d_i = ds.get_distance(current_batch, df, routing)

        #Determine candidate order_IDs
        unique = list(df["order_ID"].unique())
        candidates = list(set(unique) - set(current_batch))

        #Get distance of each candidate and calculate time savings if candidate is
        #added to current picking list
        for j in candidates:
            # picking_df = df[df["order_ID"].isin(current_batch+[j])]
            d_ij = ds.get_distance(current_batch+[j], df, routing)
            df.loc[df["order_ID"] == j, "similarity"] = d_ij-d_i


    # METHOD II: TIME SAVINGS
    elif(similar_type == "total_time_savings"):

        #Get distance of current picking list
        t_i = ds.get_tourtime(current_batch, df, routing = routing)

        #Determine candidate order_IDs
        unique = list(df["order_ID"].unique())
        candidates = list(set(unique) - set(current_batch))

        #Get distance of each candidate and calculate time savings if candidate is
        #added to current picking list
        for j in candidates:
            t_j = ds.get_tourtime([j], df, routing = routing)
            t_ij = ds.get_tourtime(current_batch+[j], df, routing = routing)
            df.loc[df["order_ID"] == j, "similarity"] = 2*10*((t_i+t_j-t_ij)/(t_i+t_j))

    return df



######################## URGENCY AND PRIORITY

def priority_function(x):
    '''
    Piecewise linear function to describe priority of orders.
    '''

    res = np.piecewise(x, [x < 0, 0 <= x < 30, 30 <= x < 60, 60 <= x < 120, x >= 120],
    [lambda x: 20, lambda x: -2*x+100, lambda x: (-2/3)*x+60, lambda x: (-1/3)*x+40, lambda x: 0])

    return float(res/10)


def update_priorities(df, t_now, lead_time = 10):
    '''
    Update priorities and binary urgency indicator of each order.

    Inputs:
        df (DataFrame):          DataFrame incl. information on all waiting orders
        t_now (float):           Current simulation time (in min)
        lead_time (float):       Estimated lower bound to get a picker tour done (in min)

    Outputs:
        df (DataFrame):          DataFrame with updated urgencies
    '''
    #Allow for chained pd.assignment
    pd.options.mode.chained_assignment = None

    #Update priority columns
    df["t_left"] = df["departuretime"]-t_now
    df["t_lead"] = df["departuretime"]-lead_time-t_now
    df["urgent"] = np.where((df["t_lead"] < 30) & (df["t_lead"] >= 0), 1, 0)
    df["priority"] = df["t_lead"].apply(priority_function)
    return df


def check_urgency_criterion(df, criteria_df, urgency_ths, log_file):
    '''
    Check if urgency-based triggering criterion is fulfilled.

    Inputs:
        df (DataFrame):             DataFrame incl. information on all waiting orders
        criteria_df (DataFrame):    DataFrame with batch triggering criteria (size-based, urgency-based)
        urgency_ths (int):          Number of urgent orders that trigger batching process

    Outputs:
        criteria_df (DataFrame):    DataFrame with updated urgency criterion
    '''
    #Allow for chained pd.assignment
    pd.options.mode.chained_assignment = None

    #Determine no. of urgent orders
    groups = df.groupby(["order_ID"]).mean()
    urgent_orders = groups["urgent"].sum()

    #Check if threshold is exceeded
    if (urgent_orders >= urgency_ths) and (criteria_df.loc[0,"urgency_criterion"] == 0):
        criteria_df["urgency_criterion"] = 1
        file = open(log_file, 'a')
        file.write(f"urgency_criterion fulfilled ({urgent_orders})"+ '\n')
        file.close


    #Check if threshold is deceeded
    elif (urgent_orders < urgency_ths) and (criteria_df.loc[0,"urgency_criterion"] == 1):
        criteria_df["urgency_criterion"] = 0


    return criteria_df




######################## SIZE

def check_size_criterion(df, criteria_df, size_ths, log_file):
    '''
    Check if size criterion is fulfilled.
    Inputs:
        df (DataFrame):             DataFrame incl. information on all waiting orders
        criteria_df (DataFrame):    DataFrame with batch triggering criteria (size-based, urgency-based)
        size_ths (int):             Size of all waiting orders that trigger batching process

    Outputs:
        criteria_df (DataFrame):    DataFrame with updated urgency criterion
    '''
    size = df["size"].sum()
    #Check if threshold is exceeded
    if (size >= size_ths) and (criteria_df.loc[0,"size_criterion"] == 0):
        criteria_df["size_criterion"] = 1
        file = open(log_file, 'a')
        file.write(f"size_criterion fulfilled ({size})"+ '\n')
        file.close
    #Check if threshold is deceeded
    elif (size < size_ths) and (criteria_df.loc[0,"size_criterion"] == 1):
        criteria_df["size_criterion"] = 0


    return criteria_df
