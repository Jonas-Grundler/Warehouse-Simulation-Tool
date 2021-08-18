import numpy as np
import pandas as pd
import simulation_tool.data as dax
import simulation_tool.initialization as init
import simulation_tool.measures as ms
import simulation_tool.distance as ds
import simulation_tool.batching as bt

'''
#############################################################################

DESCRIPTION EVALUATION.PY
Author: Jonas Grundler (University of Edinburgh)

This module mainly fulfills two tasks. Firstly, it helps to translate the ’raw’ output
data coming from the simulate system() function into reasonable performance metrics.
Secondly, the package ensures that a detailed protocol of each individual test run is created.

Functions:
     - log():                Write entry for different 'events' to log_file
     - evaluate_system():    Evaluate simulation experiments by calculating various KPI's.


#############################################################################
'''

def log(log_file, event, backlog = None, backlog_size = None, t = None, batch = None, batch_size = None, used_method = None, i = None, tour_time = None):
    '''
    Write entry for different 'events' to log_file.
    Inputs:
        log_file (.txt):       File for simulation run protocol

        event (string):        Event that should be written to log_file
                                    - backlog_before
                                    - backlog_after
                                    - batch_created
                                    - picker_tour

        backlog (int):         Number of orders currently in backlog

        backlog_size (int):    Current backlog size

        t (float):             Current point in time (in min)

        batch (list):          List of orders included in current batch

        batch_size (int):      Current batch size

        used_method (string):  String incl. used batching method (for protocol)

        i (int):               Picker ID

        tour_time (float):     Tour time of next batch

    Outputs:
        None. Write various events to log_file, e.g:
                    - Backlog before batching: 76 orders (size: 578)
                    - Backlog after batching: 38 orders (size: 299)
                    - TIME 19.9: Batch created with orders [179, 182, ..., 133]
                    - Picker 3 starts tour (tour_time: 16.88 min).
    '''

    file = open(log_file, 'a')

    if(event == "backlog_before"):
        file.write(f"Backlog before batching: {backlog} orders (size: {backlog_size})"+ '\n')
    elif(event == "backlog_after"):
        file.write(f"Backlog after batching: {backlog} orders (size: {backlog_size})"+ '\n')
    elif(event == "batch_created"):
        file.write(f"TIME {np.round(t,1)}: Batch created with orders {batch} (size: {batch_size}). {used_method}"+ '\n')
    elif(event == "picker_tour"):
        file.write(f"Picker {i+1} starts tour (tour_time: {np.round(tour_time,2)} min)."+ '\n')
    file.close()

    return None


def evaluate_system(eval_df, picker_df, simulation_period, metrics_file):
    '''
    Evaluate simulation experiments by calculating various KPI's.
    Inputs:
        eval_df (DataFrame):        DataFrame containing order statistics

        picker_df (DataFrame):      DataFrame containing picker statistics

        simulation_period (int):    Time horizon of simulation (in min)

        metrics_file (.txt):        File for simulation run results

    Outputs:
        stats (DataFrame):          DataFrame with various KPI's for simulation run
                                    Customer Service Metrics:
                                        - no_finished
                                        - no_delayed
                                        - avg_delay_time
                                        - avg_waiting_time
                                        - avg_service_time
                                        - delivery_rate
                                        - delay_finished_ratio
                                    Efficiency metrics:
                                        - total_travel_time
                                        - time_per_item
                                        - items_per_tour

        Additionally all KPI's are written to the metrics_file.

    '''
    #Allow for chained pd.assignment
    pd.options.mode.chained_assignment = None

    #Get total no. of orders
    total_no_orders = eval_df.loc[:,"order_ID"].nunique()


    ### CUSTOMER SERVICE METRICS

    #Calculate helper columns
    eval_df.loc[:,"started"] = np.where(eval_df.loc[:,"batch_start"] <= simulation_period, 1, 0)
    eval_df.loc[:,"finished"] = np.where(eval_df.loc[:,"batch_end"] <= simulation_period, 1, 0)
    eval_df.loc[:,"due"] = np.where(eval_df.loc[:,"departuretime"] <= simulation_period, 1, 0)
    eval_df.loc[:,"now_delayed"] = np.where((eval_df["batch_end"] > eval_df["departuretime"]), 1, 0)
    eval_df.loc[:,"later_delayed"] = np.where((eval_df.loc[:,"started"] == 0) & (eval_df.loc[:,"due"] == 1), 1, 0)
    eval_df.loc[:,"delayed"] = np.where((eval_df["now_delayed"] == 1) | (eval_df["later_delayed"] == 1), 1, 0)

    #Calculate number components
    no_finished = eval_df.loc[:,"finished"].sum()
    no_delayed = eval_df.loc[:,"delayed"].sum()
    now_delayed = eval_df.loc[:,"now_delayed"].sum()
    later_delayed = eval_df.loc[:,"later_delayed"].sum()
    delivery_rate = 100*(no_finished/total_no_orders)
    delay_finished_ratio = 100*(no_delayed/no_finished)

    #Calculate time components
    eval_df.loc[:,"delay_time"] = np.where(eval_df.loc[:,"batch_end"] <= eval_df.loc[:,"departuretime"], 0, eval_df.loc[:,"batch_end"] - eval_df.loc[:,"departuretime"])
    eval_df.loc[:,"waiting_time"] = eval_df.loc[:,"batch_start"] - eval_df.loc[:,"arrivaltime"]
    eval_df.loc[:,"serivce_time"] = eval_df.loc[:,"batch_end"] - eval_df.loc[:,"batch_start"]

    avg_delay_time = eval_df[eval_df["delay_time"] > 0]["delay_time"].mean()
    avg_waiting_time = eval_df.loc[:,"waiting_time"].mean()
    avg_service_time = eval_df.loc[:,"serivce_time"].mean()


    ### EFFICIENCY METRICS
    no_tours = picker_df.loc[:,"no_tours"].sum()
    no_orders = picker_df.loc[:,"no_orders"].sum()
    no_items = picker_df.loc[:,"no_items"].sum()
    total_travel_time = picker_df.loc[:,"total_travel_time"].sum()
    items_per_tour = no_items/no_tours
    time_per_item = total_travel_time/no_items

    #Write to metrics_file
    file = open(metrics_file, 'a')
    file.write(""+ '\n')
    file.write("CUSTOMER SERVICE METRICS"+ '\n')
    file.write(f"no_finished: {no_finished}"+ '\n')
    file.write(f"no_delayed: {no_delayed} (now: {now_delayed}, later: {later_delayed})"+ '\n')
    file.write(f"avg_delay_time: {avg_delay_time}"+ '\n')
    file.write(f"avg_waiting_time: {avg_waiting_time}"+ '\n')
    file.write(f"avg_service_time: {avg_service_time}"+ '\n')
    file.write(f"delivery_rate: {delivery_rate}"+ '\n')
    file.write(f"delay_finished_ratio: {delay_finished_ratio}"+ '\n')
    file.write(""+ '\n')
    file.write("EFFICIENCY METRICS"+ '\n')
    file.write(f"total_travel_time: {total_travel_time}"+ '\n')
    file.write(f"time_per_item: {time_per_item}"+ '\n')
    file.write(f"items_per_tour: {items_per_tour}"+ '\n')
    file.write(""+ '\n')
    file.close()

    #Append statistics to stats dictionary
    stats = {"no_finished": no_finished, "no_delayed": no_delayed, "avg_delay_time": avg_delay_time,
    "avg_waiting_time": avg_waiting_time, "avg_service_time": avg_service_time, "delivery_rate": delivery_rate,
    "delay_finished_ratio": delay_finished_ratio, "total_travel_time": total_travel_time, "time_per_item": time_per_item,
    "items_per_tour": items_per_tour}


    return stats
