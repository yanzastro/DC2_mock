#!/usr/bin/env python3
import os
import argparse
import numpy as np

from table_tools import load_table


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Mask the data objects to a right ascension / declination '
                    'bound.')
    parser.add_argument(
        '-i', '--input', required=True, help='file path of input data table')
    parser.add_argument(
        '--i-format', default='fits',
        help='astropy.table format specifier of the input tables ')
    parser.add_argument(
        '-b', '--bounds', nargs=4, type=float, required=True,
        help='bounds of polygon in degrees: RA_min RA_max DEC_min DEC_max')
    parser.add_argument(
        '--ra', required=True, help='fits column name of RA')
    parser.add_argument(
        '--dec', required=True, help='fits column name of DEC')
    parser.add_argument(
        '-o', '--output', required=True, help='file path of output table')
    parser.add_argument(
        '--o-format', default='fits',
        help='astropy.table format specifier of the output table '
             '(default: %(default)s)')
    args = parser.parse_args()

    RAmin, RAmax, DECmin, DECmax = args.bounds
    # check input bounds
    if not all(-90.0 <= dec <= 90.0 for dec in (DECmin, DECmax)):
        parser.error("DEC_min and DEC_max must be between -90 and 90 degrees")
    if not all(0.0 <= ra <= 360.0 for ra in (RAmin, RAmax)):
        parser.error("RA_min and RA_max must be between 0 and 360 degrees")
    if DECmax <= DECmin:
        parser.error("DEC_min must be lower than DEC_max")
    table = load_table(args.input, args.i_format, [args.ra, args.dec])

    # apply filter rule
    print(
        ("mask data to bounds with RA: %011.7f-%011.7f " % (RAmin, RAmax)) +
        ("and DEC: %0+11.7f-%0+11.7f " % (DECmin, DECmax)))
    # collect RA/DEC from the table
    ra_data = table[args.ra].data
    dec_data = table[args.dec].data
    if RAmax >= RAmin:
        mask = (  # mask data to bounds
            (ra_data >= RAmin) & (ra_data < RAmax) &
            (dec_data >= DECmin) & (dec_data < DECmax))
    else:
        mask = (  # mask data to bounds
            (ra_data >= RAmin) | (ra_data < RAmax) &
            (dec_data >= DECmin) & (dec_data < DECmax))
    if np.count_nonzero(mask) == 0:
        sys.exit("ERROR: no data found within RA/DEC limits")
    masked_table = table[mask]
    # write to specified output path
    print(
        "removed %d / %d rows" % (len(table) - len(masked_table), len(table)))
    print("write table to: %s" % args.output)
    masked_table.write(args.output, format=args.o_format, overwrite=True)
