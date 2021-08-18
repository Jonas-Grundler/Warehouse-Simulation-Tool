import numpy as np
import pandas as pd
import time
import simulation_tool.data as dax
import simulation_tool.initialization as init
import simulation_tool.measures as ms
import simulation_tool.distance as ds
import simulation_tool.batching as bt
import simulation_tool.evaluation as ev

'''
#############################################################################

DESCRIPTION SIMULATION.PY
Author: Jonas Grundler (University of Edinburgh)

This module constitutes the core element of our simulation tool.
By means of the incorporated simulate_system() function, we can simulate
each single decision step of our warehousing system over the pre-specified time horizon.

Functions:
     - simulate_system():   Write entry for different 'events' to log_file


#############################################################################
'''



def simulate_system(order_df, simulation_period = 120, size_ths = 150, urgency_ths = 10,
                    method = 'FCFS', c = None, p = None, seed_type = 'FCFS',
                    no_pickers = 5, picker_capacity = 150, lead_time = 10,
                    routing = "S-Shape", log_file = 'logging.txt', metrics_file = 'metrics.txt'):

        '''
        Perform simulation experiments for given order data.

        Inputs:
            order_df (DataFrame):       DataFrame containing generated order data

            simulation_period (int):    Time horizon of simulation (in min)

            size_ths (int):             Size of all waiting orders that trigger batching process

            urgency_ths (int):          Number of urgent orders that trigger batching process

            method (string):            Used batching method:
                                            - FCFS (First-Come-First-Serve)
                                            - dist_prio_ratio
                                            - static_weighting
                                            - trigger_flexible_weighting
                                            - percentage_flexible_weighting

            c (float):                  Range = [0;1]
                                        Weighting Parameter of similarity and priority metrics

            p (float):                  Range = [0;1]
                                        Percentage threshold for percentage_flexible_weighting

            seed_type (string):         Strategy to determine seed order:
                                            - FCFS (First come, first serve)
                                            - longest_travel_time

            no_pickers (int):           Number of pickers in system

            picker_capacity (int):      Capacity of each picker

            lead_time (float):          Estimated lower bound to get a picker tour done (in min)

            routing (string):           Warehouse routing strategy
                                        - S-Shape
                                        - Largest-Gap

            log_file (.txt):            File for simulation run protocol

            metrics_file (.txt):        File for simulation run results

        Outputs:
            eval_df (DataFrame):        DataFrame containing order statistics

            picker_df (DataFrame):      DataFrame containing picker statistics
        '''

        #Start execution time
        start = time.time()

        #### PREPARE RESULT FILES #######
        for files in [log_file, metrics_file]:
            file = open(files, 'a')
            file.write(f"" + '\n')
            file.write(f"###### SIMULATION RUN ########"+ '\n')
            file.write(f"simulation_period: {simulation_period}" + '\n')
            file.write(f"thresholds: {size_ths} (size_ths), {urgency_ths} (urgency_ths)" + '\n')
            file.write(f"pickers: {no_pickers} with capacity {picker_capacity}" + '\n')
            file.write(f"lead time: {lead_time}" + '\n')
            file.write(f"batching strategy: {method}" + '\n')
            if(method == "static_weighting") or (method == "trigger_flexible_weighting") or (method == "percentage_flexible_weighting"):
                file.write(f"c: {c}" + '\n')
            if(method == "percentage_flexible_weighting"):
                file.write(f"threshold percentage: {p}" + '\n')
            if(method != "FCFS"):
                file.write(f"seed rule: {seed_type}" + '\n')
            file.write(f"" + '\n')
            file.close()

        #### INITIALIZATION #########
        #Initialize event_calendar
        event_calendar = init.initialize_event_calendar(simulation_period)
        #Initialize criteria_df
        criteria_df = init.initialize_criteria()
        #Initialize picker_df
        picker_df = init.initialize_picker(no_pickers, simulation_period)
        #Initialize eval_df
        eval_df = init.initialize_evaluation(order_df)
        #Initialize other parameters
        t = 0
        type = "new_order"
        batch_no = 0
        size = 0

        #### SIMULATION LOOP ##########
        while t < simulation_period:

            ### EVENT 1: NEW ORDER ARRIVAL
            if(type == "new_order"):
                #Update waiting orders and their size
                waiting_order_list = order_df[order_df["arrivaltime"] <= t]

                #Update event_calendar: arrival of next "new_order"
                next_arriving = order_df[order_df["arrivaltime"] > t]
                event_calendar["new_order"] = next_arriving["arrivaltime"].min()

            ### EVENT 2: AVAILABLE PICKER
            elif(type == "free_picker"):
                #Update picker_df row of corresponding picker
                i = picker_df["next_comeback"].idxmin()
                picker_df.loc[i,"available"] = 1
                picker_df.loc[i,"next_comeback"] = simulation_period+1

                #Update event_calendar: arrival of next "available picker"
                event_calendar["free_picker"] = picker_df["next_comeback"].min()


            ### BATCHING DECISION
            #Check if size_criterion is fulfilled
            criteria_df = ms.check_size_criterion(waiting_order_list, criteria_df, size_ths, log_file)

            #Check if urgency_criterion is fulfilled
            waiting_order_list = ms.update_priorities(waiting_order_list, t, lead_time)
            criteria_df = ms.check_urgency_criterion(waiting_order_list, criteria_df, urgency_ths, log_file)

            #Check if picker is available AND batching criterion is fulfilled
            if (picker_df["available"].any() == 1) and (criteria_df.iloc[0,].any() == 1):

                #Order backlog before batching
                backlog = waiting_order_list["order_ID"].nunique()
                backlog_size = waiting_order_list["size"].sum()
                ev.log(log_file, event = "backlog_before", backlog = backlog, backlog_size = backlog_size)

                #Generate new batch
                batch_no += 1
                batch, batch_size, tour_time, used_method = bt.generate_new_batch(waiting_order_list, criteria_df, method, c, p, picker_capacity, seed_type, routing)
                picking_df = order_df[order_df["order_ID"].isin(batch)]
                ev.log(log_file, event = "batch_created", t = t, batch = batch, batch_size = batch_size, used_method = used_method)

                #Update waiting orders and total orders
                waiting_order_list = waiting_order_list[~waiting_order_list["order_ID"].isin(batch)]
                order_df = order_df[~order_df["order_ID"].isin(batch)]

                #Assign batch to picker and update picker_df
                i = picker_df[picker_df["available"] == 1]["total_travel_time"].idxmin()
                picker_df.loc[i, "available"] = 0
                picker_df.loc[i, "next_comeback"] = t + tour_time
                picker_df.loc[i, "no_tours"] += 1
                picker_df.loc[i, "no_orders"] += picking_df["order_ID"].nunique()
                picker_df.loc[i, "no_items"] += picking_df["order_ID"].count()
                picker_df.loc[i, "total_travel_time"] += min(tour_time, simulation_period - t)
                ev.log(log_file, event = "picker_tour", i = i, tour_time = tour_time)

                #Update evaluation data
                to_be_updated = eval_df["order_ID"].isin(batch)
                eval_df.loc[to_be_updated, "batch_ID"] = batch_no
                eval_df.loc[to_be_updated, "batch_start"] = t
                eval_df.loc[to_be_updated, "batch_end"] = t + tour_time

                #Update event_calendar: arrival of next "available picker"
                event_calendar["free_picker"] = picker_df["next_comeback"].min()

                #Check if size_criterion is still fulfilled
                criteria_df = ms.check_size_criterion(waiting_order_list, criteria_df, size_ths, log_file)

                #Check if urgency_criterion is still fulfilled
                waiting_order_list = ms.update_priorities(waiting_order_list, t, lead_time)
                criteria_df = ms.check_urgency_criterion(waiting_order_list, criteria_df, urgency_ths, log_file)

                #Order backlog after batching
                backlog = waiting_order_list["order_ID"].nunique()
                backlog_size = waiting_order_list["size"].sum()
                ev.log(log_file, event = "backlog_after", backlog = backlog, backlog_size = backlog_size)

            t = event_calendar.iloc[0,].min()
            type = event_calendar.iloc[0,].idxmin()

        #Stop execution time
        end = time.time()

        #Write execution tim to metrics_file
        file = open(metrics_file, 'a')
        file.write(f"Execution time: {end-start}" + '\n')
        file.close()

        return eval_df, picker_df
