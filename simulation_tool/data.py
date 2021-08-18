import pandas as pd
import numpy as np

'''
#############################################################################

DESCRIPTION DATA.PY
Author: Jonas Grundler (University of Edinburgh)

This module can be used to generate random order data.

    Functions:
      - generate_orders():      Generate some input data (order information)
                                for our simulation experiments.

#############################################################################
'''


def generate_orders(seed_no, simulation_period = 120, backlog = 100, interval = 15, arrival_mean = 5, arrival_stddev = 0, arrival_list = None,
                    min_lead = 30, avg_items_per_order = 1.5, first_due = 30, inter_due = 30,
                    aisle_no = 10, aisle_length = 45, log_file = 'logging.txt', metrics_file = 'metrics.txt'):
    '''
    Generate some input data (order information) for our simulation experiments.
    Users can specify their desired time horizon, backlog of orders,
    arrival process as well as many other parameters and receive a data frame
    containing the arrival and departure times, size and location of the
    various generated orders.

    Inputs:
        seed_no (int):              random seed for replication purposes

        simulation_period (int):    time horizon of simulation (in minutes)

        backlog (int):              number of orders in backlog at t=0

        interval (int):             interval in which lambda changes (exponential arrival process)

        arrival_mean (float):       mean of lambda (exponential arrival process)

        arrival_stddev (float):     standard dev. of lambda (exponential arrival process)

        arrival_list (list):        list with prespecified lambdas (exponential arrival process);
                                    alternatively to arrival_mean and arrival_stddev

        min_lead (int):             minimum time between order arrival and departure

        avg_items_per_order (int):  avg. no. of items (SKUs) included in a single order

        first_due (int):            departure time of first vehicle (in minutes after t=0)

        inter_due (int):            time between two vehicle departures

        aisle_no (int):             number of aisles in considered one-block warehouse

        aisle_length (int):         length of aisles (in meters) in considered one-block warehouse

        log_file (.txt):            file for simulation run protocol

        metrics_file (.txt):        file for simulation run results

    Outputs:
        df (DataFrame):             DataFrame containing information on
                                        - order ID
                                        - order arrivaltime
                                        - order departuretime
                                        - number of items
                                        - size of each item
                                        - location of each item (x,y)
    '''


    #WRITE HEADER FOR RESULT FILES
    for files in [log_file, metrics_file]:
        file = open(files, 'a')
        file.write(f"" + '\n')
        file.write(f"###### DATA INFORMATION ########"+ '\n')
        file.write(f"simulation_period: {simulation_period}" + '\n')
        file.write(f"backlog: {backlog}" + '\n')
        file.write(f"min_lead: {min_lead}" + '\n')
        if(arrival_list != None):
            file.write(f"arrivals: list = {arrival_list} (interval = {interval})" + '\n')
        else:
            file.write(f"arrivals: mean = {arrival_mean}, stddev = {arrival_stddev} (interval = {interval})" + '\n')
        file.write(f"seed_no: {seed_no}" + '\n')
        file.write(f"" + '\n')
        file.close()



    #Initialize df
    cols = ["order_ID", "arrivaltime", "departuretime", "size", "x_coord", "y_coord"]
    df = pd.DataFrame(columns = cols)

    #Initialize random number generator and other parameters
    rng = np.random.default_rng(seed = seed_no)
    t = 0
    d = 1
    order_ID = 0

    # GENERATE BACKLOG
    for i in range(backlog):
        arrivaltime = t
        order_ID = order_ID + 1

        #Assign order to one of the vehicles and get departuretime
        lead = rng.binomial(n = 5, p = 0.1)
        departuretime = first_due + lead * inter_due

        #Generate no_items included in order
        #for each order: generate row entry
        no_items = rng.geometric(1/avg_items_per_order)
        for k in range(no_items):
            size = rng.integers(1,10)
            x_coord = rng.integers(0, aisle_no)
            y_coord = rng.integers(1, aisle_length+1)

            df = df.append({"order_ID": order_ID, "arrivaltime": arrivaltime,
             "departuretime": departuretime, "size": size,
             "x_coord": x_coord, "y_coord": y_coord}, ignore_index=True)


    # GENERATE NEW ARRIVING ORDERS
    #Determine arrivalrate
    # Option 1: specfic arrival list as input
    if(arrival_list != None):
        arrivalrate = arrival_list[0]
    # Option 2: generate normally distributed arrival rate
    else:
        arrivalrate = rng.normal(arrival_mean, arrival_stddev)
        #Note: arrival rates <= 0 are not valid
        if arrivalrate < 0:
            arrivalrate = 0.05

    # Generate first arrivaltime
    t = rng.exponential(1/arrivalrate)

    while t < simulation_period:
        arrivaltime = t
        order_ID = order_ID + 1

        #Assign order to one of the vehicles and get departuretime
        earliest_departure = t + min_lead
        index_earliest_vehicle = max(0,np.ceil((earliest_departure-first_due)/inter_due))
        lead = rng.binomial(n = 5, p = 0.1)
        departuretime = first_due + (index_earliest_vehicle + lead)*inter_due

        #Generate no_items included in order
        #for each order: generate row entry
        no_items = rng.geometric(1/avg_items_per_order)
        for k in range(no_items):
            size = rng.integers(1,10)
            x_coord = rng.integers(0, aisle_no)
            y_coord = rng.integers(1, aisle_length+1)

            df = df.append({"order_ID": order_ID, "arrivaltime": arrivaltime,
             "departuretime": departuretime, "size": size,
             "x_coord": x_coord, "y_coord": y_coord}, ignore_index=True)

        #Check if arrivalrate has to be updated
        if(arrivaltime > d*interval):
            #Update interval_counter
            d += 1
            #Determine arrivalrate
            # Option 1: specfic arrival list as input
            if(arrival_list != None):
                arrivalrate = arrival_list[d-1]
            # Option 2: generate normally distributed arrival rate
            else:
                arrivalrate = rng.normal(arrival_mean, arrival_stddev)
                #Note: arrival rates <= 0 are not valid
                if arrivalrate < 0:
                    arrivalrate = 0.05

        #Generate next arrivaltime
        t = arrivaltime + rng.exponential(1/arrivalrate)

    #Change data types of columns
    df = df.astype({"order_ID": int, "arrivaltime": float, "departuretime": float, "size": int, "x_coord": int, "y_coord":int})
    return df
