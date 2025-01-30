'''
Setup:

Compartment 5: 200ul wellplate
Compartment 6: Tuberack 4x50ml + 6x15ml
    A3 = D18_Cl
    A4 = Y6
    B3 = Y7
    B4 = L8_BO
Compartment 8: Tiprack 300ul
'''
from opentrons import protocol_api
import numpy as np

metadata = {
    "apiLevel": "2.13",
}


def run(protocol: protocol_api.ProtocolContext):
    resource = protocol.load_labware("opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical", 6)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    tipracksmall = protocol.load_labware("opentrons_96_tiprack_300ul", 8)
    pipettesmall = protocol.load_instrument("p300_single_gen2", "left")

    # Constant
    tip_max_volume = 300
    aspirate_dispense_rate = 1.5
    well_volume = 160

    # Initialiation of well-plate content and allocation
    partition = 7
    combination = [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]]
    initial_points = []
    for a in range(10):
        initial_points.append([0.25, 0.25, 0.25, 0.25])  # For consistency test
    for a in range(6):
        for b in range(partition):
            point = [0., 0., 0., 0.]
            point[combination[a][0]] = round(b / (partition - 1), 10)
            point[combination[a][1]] = round(1 - b / (partition - 1), 10)
            if point not in initial_points:
                initial_points.append(point)
    run_point = initial_points

    # Initialization of Sample Locations
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    columns = list(range(1, 13))
    nrows = len(rows)
    ncols = len(columns)

    well_names = np.zeros([nrows, ncols]).astype("object")
    for i, row in enumerate(rows):
        for j, col in enumerate(columns):
            well_names[i, j] = row + str(col)

    vial_locations = ["A3", "A4", "B3", "B4"]
    # A3 = D18_Cl, A4 = Y6, B3 = Y7, B4 = L8_BO
    protocol.home()

    # Mixing of Polymer
    summary = ''
    current_tip_volume = 0
    overflow = False
    for source_index, source in enumerate(vial_locations):
        # Initialization of new source
        pipettesmall.pick_up_tip(location=tipracksmall)
        pipettesmall.aspirate(volume=tip_max_volume, location=resource[source], rate=aspirate_dispense_rate)
        current_tip_volume = tip_max_volume

        for point_index, point in enumerate(run_point):
            # Checks if number of sample exceeds 96
            if point_index > 95:
                print("Sample point exceed 96, stopping process for source", source, "at point ", point)
                summary += "Sample point exceed 96, stopping process for source " + source + " at point index " + str(
                    point) + "\n"
                overflow = True
                break

            # Checks if dropper content is sufficient, if not, retrieve until max capacity
            if point[source_index] * well_volume > current_tip_volume:
                pipettesmall.aspirate(volume=tip_max_volume - current_tip_volume, location=resource[source],
                                      rate=aspirate_dispense_rate)
                current_tip_volume = tip_max_volume

            # Dispense sample, indicate in output and update corresponding parameters
            name = well_names[point_index // 12, point_index % 12]
            pipettesmall.dispense(volume=point[source_index] * well_volume, location=plate.wells_by_name()[name].top(z=0.5),
                                  rate=aspirate_dispense_rate)

            print("Dispensed", source, "source at", name, ". Volume: ", point[source_index], "of max volume (",
                  point[source_index] * well_volume, "uL)")
            summary += "Dispensed " + source + " source at " + name + ". Volume: " + str(
                point[source_index]) + " of max volume (" + str(point[source_index] * well_volume) + "uL)\n"

            current_tip_volume -= point[source_index] * well_volume

        # Change Source Procedure
        pipettesmall.blow_out(location=resource[source])
        pipettesmall.drop_tip()
    # Finish experimentation Procedure
    protocol.home()

