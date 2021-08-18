import numpy as np
import pandas as pd
import time
import simulation_tool.data as dax
import simulation_tool.initialization as init
import simulation_tool.measures as ms
import simulation_tool.distance as ds
import simulation_tool.batching as bt
import simulation_tool.evaluation as ev
import simulation_tool.simulation as sim

'''
#############################################################################

DESCRIPTION MAIN.PY
Author: Jonas Grundler (University of Edinburgh)

This file can be seen as our testing environment. It builds on all other modules and is only
used for carrying out various experiments with different random seeds. Users can easily generate
random order data, run their simulation experiments and evaluate the performance of these.

Functions: None.

#############################################################################
'''


# --- Please insert your simulation experiments here ---
#
# Below, we have included an example of our 'when to batch?' simulation study.
# By doing so, we hope that the setup of different simulation experiments as well as
# the interpretation of the corresponding results become clearer.
#
# In concrete terms, we tested five different Q/U combinations
# for our batch triggering criteria under a demand setting with arrival mean = 5
# and stddev = 2. More details on this specific test run can be found in
# Appendix D - Table 5 of our dissertation.


################ SIMULATION EXPERIMENTS

# Perform 50 simulations runs (5 Q/U parameters, 10 diff. random seeds)
for run in range(50):

    ##### STEP 1: SPECIFY SIMULATION EXPERIMENT

    # Specify five different Q/U combinations
    Q_list = [1,75,150,225,375]
    U_list = [1,5,10,15,25]
    Q = Q_list[run//10]
    U = U_list[run//10]

    # Use 10 different seeds in total
    seed_list = list(range(3544,3554))
    seed = seed_list[run%len(seed_list)]

    # Initialize summary statistics
    stats_summary = init.initialize_summary()


    # Test Q/U combinations using different methods
    for i in range(1,4):

        if(i == 1):
            m = "FCFS"
            c_val = None
            p_val = None
        elif(i == 2):
            m = "static_weighting"
            c_val = 0.25
            p_val = None
        else:
            m = "percentage_flexible_weighting"
            c_val = 0.25
            p_val = 0.33

        # Specify location of log_files and metric_files
        log = f"example/log_files/logfile{100+100*run+i}.txt"
        mex = f"example/metric_files/metrics{100+100*run+i}.txt"


        ##### STEP 2: GENERATE ORDER DATA
        order_df = dax.generate_orders(seed_no = seed, arrival_mean = 5, arrival_stddev = 2, log_file = log, metrics_file = mex)

        ##### STEP 3: SIMULATE SYSTEM
        eval_df, picker_df = sim.simulate_system(order_df, simulation_period = 120, size_ths = Q, urgency_ths = U,
                                                 method = m, c = c_val, p = p_val, seed_type = 'longest_travel_time',
                                                 no_pickers = 5, picker_capacity = 150, routing = 'S-Shape',
                                                 log_file = log, metrics_file = mex)

        ##### STEP 4: EVALUATE SYSTEM
        stats = ev.evaluate_system(eval_df, picker_df, simulation_period = 120, metrics_file = mex)



        ##### STEP 5: ADD SIMULATION RESULTS TO SUMMARY
        new_row = {"method": m, "c": c_val, "p": p_val, **stats}
        stats_summary = stats_summary.append(new_row, ignore_index = True)

    # Save summary as .csv file
    stats_summary.to_csv(f"example/csv_results/metrics{100+100*run}.csv")



################ INTERPRETATION OF RESULTS

d = {}
df = {}

# Read .csv files for each run
for run in range(50):
    d[f"stats_{100+100*run}"] = pd.read_csv(f"experimental_results/when_to_batch/scenario_5/csv_results/metrics{100+100*run}.csv")

# Read method names from first .csv file
names = pd.read_csv("experimental_results/when_to_batch/scenario_8/csv_results/metrics100.csv")

#Loop over five different Q/U combinations
for q in range(5):
    no = 100 + 1000*q

    #Concatenate different random seeds of one simulation experiment
    for run in range(10):
        if run == 0:
            df_concat = d[f"stats_{no}"]
        else:
            df_concat = pd.concat((df_concat, d[f"stats_{no+100*run}"]))

    # Average different random seeds of one simulation experiment
    by_row_index = df_concat.groupby(df_concat.index)
    df_scenario = by_row_index.mean()
    df_scenario["full_names"] = names["method"]
    df[f"study_{q+1}"] = df_scenario

#Concatenate averaged results of all five different Q/U combinations
df_results = pd.concat((df[f"study_1"], df[f"study_2"], df[f"study_3"], df[f"study_4"], df[f"study_5"]))

#Print results
df_results.iloc[:,[13,1,2,3,4,5,6,7,11,12,10]].sort_values("full_names").round(2)
