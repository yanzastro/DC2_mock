#!/usr/bin/env python3
import argparse
import os
import sys
from hashlib import md5

import numpy as np
from astropy import units
from astropy.table import Column, Table

from table_tools import load_table


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Create a data table with a photometery realisation based '
                    'on a table with simulated model magnitudes and '
                    'observational detection limits.')

    data_group = parser.add_argument_group('data')
    data_group.add_argument(
        '-i', '--input', required=True, help='file path of input data table')
    data_group.add_argument(
        '--i-format', default='fits',
        help='astropy.table format specifier of the input table '
             '(default: %(default)s)')
    data_group.add_argument(
        '-o', '--output', required=True, help='file path of output table')
    data_group.add_argument(
        '--o-format', default='fits',
        help='astropy.table format specifier of the output table '
             '(default: %(default)s)')

    params_group = parser.add_argument_group('parameters')
    params_group.add_argument(
        '--filters', nargs='*', required=True,
        help='list of table column names providing model magnitudes')
    params_group.add_argument(
        '--limits', nargs='*', type=float, required=True,
        help='magnitude limits for each entry in --filters')
    params_group.add_argument(
        '--significance', type=float, default=1.0,
        help='significance of detection against magnitude limits '
             '(default: %(default)s)')
    params_group.add_argument(
        '--sn-limit', type=float, default=0.2,
        help='lower numerical limit for the signal-to-noise ratio '
             '(default: %(default)s)')
    params_group.add_argument(
        '--sn-detect', type=float, default=1.0,
        help='limiting signal-to-noise ratio for object detection '
             '(default: %(default)s)')
    params_group.add_argument(
        '--sn-factors', nargs='*',
        help='list of table column names of correction factors for the '
             'signal-to-noise ratio of extended sources, one '
             'for each --filter')
    params_group.add_argument(
        '--seed', default='KV450',
        help='string to seed the random generator (default: %(default)s)')

    args = parser.parse_args()

    # check if all argument lengths match
    filters = args.filters
    if len(args.limits) != len(filters):
        sys.exit("ERROR: number of input --limits do not match --filters")
    if args.sn_factors is None:
        sn_factors = [None] * len(filters)
    else:
        sn_factors = args.sn_factors
        if len(sn_factors) != len(filters):
            sys.exit(
                "ERROR: number of input --sn-factors do not match --filters")

    # load the data table and check that all required columsn exist
    columns = [f for f in filters]
    if args.sn_factors is not None:
        columns.extend(sn_factors)
    data = load_table(args.input, args.i_format, columns)
    print("use input filters: %s" % ", ".join(filters))

    # get all input magnitudes and their limits
    mag_model_data = {filt: data[filt] for filt in filters}
    mag_model_limits = {
        filt: lim for filt, lim in zip(filters, args.limits)}

    # create noise realisations
    SN_limit = args.sn_limit
    SN_detect = args.sn_detect
    non_detection_magnitude = 99.0  # inserted for non-detections
    detect_sigma_to_mag = 2.5 * np.log10(args.significance)  # ZP conversion
    # dictionaries that collect the magnitude realisations per filter
    mag_realisation_data = {}
    mag_realisation_error = {}
    # reseed the random state -> reproducible results
    hasher = md5(bytes(args.seed, "utf-8"))
    hashval = bytes(hasher.hexdigest(), "utf-8")
    np.random.seed(np.frombuffer(hashval, dtype=np.uint32))
    np.random.seed(np.frombuffer(hashval, dtype=np.uint32))
    
    for filt, sn_key in zip(filters, sn_factors):
        print("processing filter '%s'" % filt)
        model_mags = mag_model_data[filt]
        # compute the model flux
        model_flux = np.power(10.0, -0.4 * model_mags)
        # compute the flux error from the magnitude limit
        flux_err = np.power(
            10.0, -0.4 * mag_model_limits[filt]) / args.significance
        if sn_key is not None:
            # point source correction: 0 < data[sn_key] <= 1
            flux_err /= data[sn_key]
        # compute the flux realisation (the flux error does not change)
        real_flux = np.random.normal(model_flux, flux_err)
        # convert to magnitudes
        
        real_flux[real_flux<=0] = 1.e-99        
        real_mags = -2.5 * np.log10(real_flux)
        
        real_SN = np.maximum(real_flux / flux_err, args.sn_limit)
        real_mags_err = 2.5 / np.log(10.0) / real_SN
        # set magnitudes of undetected objects and mag < 5.0 to 99.0
        not_detected = (real_SN < args.sn_detect) | (real_mags < 5)
        real_mags[not_detected] = non_detection_magnitude
        real_mags_err[not_detected] = (  # one sigma magnitude limit
            mag_model_limits[filt] - 2.5 * np.log10(args.significance))
        # collect the results
        mag_realisation_data[filt] = real_mags.astype(np.float32)
        mag_realisation_error[filt] = real_mags_err.astype(np.float32)

    # collect output data
    table = Table()
    for filt in filters:
        # find the correct magnitude column suffix depending on whether
        # magnification was applied or not
        if "_evo" in filt:
            key = filt.replace("_evo", "_obs")
            keyerr = filt.replace("_evo", "_obserr")
        else:
            if filt.endswith("_mag"):
                key = filt[:-4] + "_obs_mag"
                keyerr = filt[:-4] + "_obserr_mag"
            else:
                key = filt + "_obs"
                keyerr = filt + "_obserr"
        table[key] = Column(
            mag_realisation_data[filt], unit=units.mag,
            description="realisation of model magnitude")
        table[keyerr] = Column(
            mag_realisation_error[filt], unit=units.mag,
            description="error of realisation of model magnitude")

    # write to specified output path
    print("write table to: %s" % args.output)
    table.write(args.output, format=args.o_format, overwrite=True)
