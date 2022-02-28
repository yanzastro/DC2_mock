#!/usr/bin/env python3
import argparse
import os
import sys

import numpy as np
from astropy import units
from astropy.table import Column, Table

from table_tools import load_table


def mag_correction(mag, redshift, evo=True):
    """
    Evolution correction as described in the official MICE2 manual
    https://www.dropbox.com/s/0ffa8e7463n8h1q/README_MICECAT_v2.0_for_new_CosmoHub.pdf?dl=0
    Parameters
    ----------
    mag : array_like
        Uncorrected model magnitudes.
    redshift : array_like
        True galaxy redshift (z_cgal).
    Returns
    -------
    mag_evo : array_like
        Evolution corrected model magnitudes.
    """
    if evo:
        return mag - 0.8 * (np.arctan(1.5 * redshift) - 0.1489)
    else:
        return mag


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Apply the missing magnitude evolution correction to '
                    'DC2.')
    parser.add_argument(
        '-i', '--input', required=True, help='file path of DC2 data table')
    parser.add_argument(
        '--i-format', default='fits',
        help='astropy.table format specifier of the input table')
    parser.add_argument(
        '-o', '--output', required=True,
        help='file path of output table containing only the corrected colours')
    parser.add_argument(
        '--o-format', default='fits',
        help='astropy.table format specifier of the output table '
             '(default: %(default)s)')
    parser.add_argument(
        '--evo', default='True',
        help='Add evolution correction or not?')
    args = parser.parse_args()

    # check if all required columns exist
    z_col = "redshift"
    evo = args.evo
    data = load_table(args.input, args.i_format, [z_col])
    # find all model magnitude columns, ending with _true
        
    mag_cols = [col for col in data.colnames if col.startswith("mag")]
    if len(mag_cols) == 0:
        sys.exit("ERROR: table does not contain any DC2 magnitude columns")
    print("Find following filters:" + str(mag_cols))

    # collect data and apply correction
    z_data = data[z_col]
    # create a new table that only contains the evolution corrected magnitudes
    table = Table()
    for filt in mag_cols:
        print(filt + "_evo")
        table[filt + "_evo"] = Column(
            mag_correction(data[filt], z_data, evo), unit=units.mag,
            description="evolution corrected model magnitude")

    # write to specified output path
    print("write table to: %s" % args.output)
    table.write(args.output, format=args.o_format, overwrite=True)