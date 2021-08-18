import numpy as np
import pandas as pd

'''
#############################################################################

DESCRIPTION INITIALIZATION.PY
Author: Jonas Grundler (University of Edinburgh)

initialization.py is a purely functional package and only used for initializing different data frames
that are required for conducting our simulation experiments:

Functions:
     - initialize_event_calendar():     Initialize event_calendar (next order arrival, picker returns, etc.)
     - initialize_criteria():           Initialize DataFrame with batch triggering criteria (size-based, urgency-based)
     - initialize_picker():             Initialize DataFrame with status of picker availability
     - initialize_evaluation():         Initialize DataFrame for order statistics
     - initialize_summary():            Initialize DataFrame for summary of multiple simulation runs


#############################################################################
'''

def initialize_event_calendar(simulation_period):
    '''
    Initialize event calendar for given order data.

    Inputs:
        simulation_period (int):    Time horizon of simulation (in min)

    Outputs:
        df (DataFrame):             Initialized event calendar
    '''

    data = [[0,simulation_period+1]]
    cols = ["new_order", "free_picker"]
    df = pd.DataFrame(data, columns = cols)
    return df


def initialize_criteria():
    '''
    Initialize batch triggering criteria (size-based, urgency-based),
    i.e. no criterion is met at t=0.

    Inputs: None.

    Outputs:
        df (DataFrame):     Initialized DataFrame with batch triggering criteria
    '''
    data = [[0,0]]
    cols = ["urgency_criterion", "size_criterion"]
    df = pd.DataFrame(data, columns = cols)
    return df


def initialize_picker(no_pickers, simulation_period):
    '''
    Initialize picker availability, i.e. all pickers available at t=0.

    Inputs:
        simulation_period (int):    Time horizon of simulation (in min)
        no_pickers (int):           Number of pickers in system

    Outputs:
        df (DataFrame):              Initialized DataFrame with status of picker availability.
    '''
    cols = ["name", "available", "next_comeback", "no_tours", "no_orders", "no_items", "total_travel_time"]
    df = pd.DataFrame(columns = cols)
    for i in range(no_pickers):
        df = df.append({"name": i+1, "available": 1, "next_comeback": simulation_period+1, "no_tours": 0, "no_orders": 0, "no_items": 0,"total_travel_time": 0.0}, ignore_index=True)
    return df


def initialize_evaluation(order_df):
    '''
    Initialize and prepare order_df for evaluation.

    Inputs:
        order_df (int):     DataFrame containing generated order data

    Outputs:
        df (DataFrame):     Initialized DataFrame for order statistics
    '''
    df = pd.pivot_table(order_df, index = 'order_ID', aggfunc = {'order_ID':pd.Series.count, 'size': sum, 'arrivaltime': pd.unique, 'departuretime': pd.unique})
    df = df.rename(columns = {"order_ID": "no_items"})
    df = df.reset_index()
    df["batch_ID"] = 0
    df["batch_start"] = np.nan
    df["batch_end"] = np.nan

    return df


def initialize_summary():
    '''
    Initialize DataFrame for summary of multiple simulation runs.

    Inputs: None.

    Outputs:
        df (DataFrame):     Initialized DataFrame for summary
    '''
    cols = ["method", "c", "p", "no_finished", "no_delayed", "avg_delay_time",
    "avg_waiting_time", "avg_service_time", "delivery_rate", "delay_finished_ratio",
     "total_travel_time", "time_per_item", "items_per_tour"]
    df = pd.DataFrame(columns = cols)

    return df
