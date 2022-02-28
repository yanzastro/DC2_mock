import yaml
import numpy as np
from yaml import Loader
from subprocess import run
import subprocess
import os
import sys

config_file = sys.argv[1]
with open(config_file) as file:
    documents = yaml.load(file, Loader=Loader)

config = {}
for i, item in enumerate(documents):
    config[item] = documents[item]
    
def list2string(alist, prefix='', suffix=''):
    st = ''
    for l in alist:
        st += ' ' + prefix + str(l) + suffix
    return st

SURVEY = config['survey']
THREADS = str(config['threads'])
DATADIR = config['paths']['DATADIR']
MOCKraw = config['paths']['MOCKraw']
MOCKmasked = DATADIR + config['paths']['MOCKmasked']
MOCKoutfull = DATADIR + config['paths']['MOCKoutfull']
MOCKout = DATADIR + config['paths']['MOCKout']
BOUNDS = list2string(config['fields']['bounds'])
grid = list2string(config['fields']['grid'])

RA_name = config['columns']['coordinates']['RA']
DEC_name = config['columns']['coordinates']['DEC']

size_minor = config['columns']['shapes']['size_minor']
size_major = config['columns']['shapes']['size_major']

magnitudes = list2string(config['columns']['magnitudes'])
sn_factors = list2string(config['columns']['magnitudes'],prefix='sn_factor_')

PSFs = list2string(config['photometric_setup']['PSFs'])
MAGlims = list2string(config['photometric_setup']['MAGlims'])
scale = str(config['photometric_setup']['scale'])
MAGsig = str(config['photometric_setup']['MAGsig'])
sn_detect = str(config['photometric_setup']['sn_detect'])
select_rules = list2string(config['photometric_setup']['select_rules'], 
                              prefix = "--rule ")

real_weight_col = config['weight_assignment']['real_weight_col']
real_weight_file = config['weight_assignment']['real_weight_file']
real_mag_col = list2string(config['weight_assignment']['real_mag_col'])
tree = config['weight_assignment']['tree']

magnitudes_obs = list2string(config['columns']['magnitudes'], suffix='_obs')
magnitudes_obserr = list2string(config['columns']['magnitudes'], suffix='_obserr')

z_min = str(config['photoz_setup']['z_min'])
z_max = str(config['photoz_setup']['z_max'])
templates  = config['photoz_setup']['templates']
prior = config['photoz_setup']['prior']
prior_filter =  config['photoz_setup']['prior_filter']

if ~os.path.isdir(DATADIR):
    os.system('mkdir '+DATADIR)

print("==> generate base footprint for "+SURVEY)

try:
    run("test -e "+DATADIR+"/footprint.txt && rm "+DATADIR+"/footprint.txt", shell=True,  check=True)
except(subprocess.CalledProcessError): pass


run("mocks_generate_footprint.py \
    -b "+BOUNDS+" \
    --survey "+SURVEY+" \
    -f "+DATADIR+"/footprint.txt \
    -p "+DATADIR+"/pointings_KV450.txt \
    --grid "+grid, shell=True, check=True)
print("\n")

print("==> mask DC2 to given footprint")
# apply the bounds to the DC2 catalogue
run("data_table_mask_ra_dec.py \
    -i "+MOCKraw+" \
    -b "+BOUNDS+" \
    --ra "+RA_name+" --dec "+DEC_name+" \
    -o "+MOCKmasked, shell=True,  check=True)
run("data_table_hstack.py \
    -i "+MOCKmasked+" \
    -o "+MOCKoutfull, shell=True,  check=True)
print("\n")


print("==> compute point source S/N correction")
# Compute the effective radius (that contains 50% of the luminosity), compute
# the observational size using the PSFs, scale this with a factor of 2.5
# (similar to what sextractor would do) to get a mock aperture. Finally
# calculate a correction factor for the S/N based on the aperture area compared
# to a point source (= PSF area).
run("mocks_extended_object_sn.py \
    -i "+MOCKoutfull+" \
    --total-size-minor "+str(size_minor)+" --total-size "+str(size_major)+" \
    --psf "+PSFs+" \
    --filters "+magnitudes+"\
    --scale "+scale+"  --flux-frac 0.5\
    --threads "+THREADS+" \
    -o "+DATADIR+"/apertures.fits", shell=True,  check=True)
# update the combined data table
run("data_table_hstack.py \
    -i "+MOCKmasked+" \
       "+DATADIR+"/apertures.fits \
    -o "+MOCKoutfull, shell=True,  check=True)
print("\n")


print("==> generate photometry realisation")
# Based on the KiDS limiting magnitudes, calcalute the mock galaxy S/N and
# apply the aperture size S/N correction to obtain a KiDS-like magnitude
# realisation.
run("mocks_photometry_realisation.py \
    -i "+MOCKoutfull+" \
    --filters "+magnitudes+"\
    --limits "+MAGlims+" \
    --significance "+MAGsig+" \
    --sn-factors "+sn_factors+"\
    --sn-detect "+sn_detect+"\
    -o "+DATADIR+"/magnitudes_observed.fits", shell=True,  check=True)
    
# update the combined data table
run("data_table_hstack.py \
    -i "+MOCKmasked+" \
       "+DATADIR+"/magnitudes_observed.fits \
    -o "+MOCKoutfull, shell=True,  check=True)
print("\n")


print("==> assign galaxy weights")
# Assign lensfit weights by matching mock galaxies in 9-band magnitude space to
# their nearest neighbour KV450 galaxies using the super-user catalogues which
# contain objects with recal_weight<=0. Mock galaxies that do not have a
# nearest neighbour within --r-max (Minkowski distance) are assigned the
# --fallback values.
run("mocks_draw_property.py \
    -s "+MOCKoutfull+" \
    --s-attr "+magnitudes_obs+" \
    --s-prop recal_weight \
    -d "+real_weight_file+" \
    --d-attr "+real_mag_col+" \
    --d-prop "+real_weight_col+" \
    --r-max 1.0 \
    --fallback 0.0 \
    --threads "+THREADS+" \
    -t "+tree+" \
    -o "+DATADIR+"/recal_weights.fits", shell=True, check=True)


print("==> compute photo-zs")
# Run BPZ on the mock galaxy photometry using the KV450 setup (prior: NGVS,
# templates: Capak CWWSB), the prior limited to 0.7 < z < 1.43.
run("mocks_bpz_wrapper.py \
    -i "+MOCKoutfull+" \
    --filters "+magnitudes_obs+" \
    --errors "+magnitudes_obserr+" \
    --z-min "+z_min+" \
    --z-max "+z_max+" \
    --templates "+templates+" \
    --prior "+prior+" \
    --prior-filter "+prior_filter+"_obs \
    --threads "+THREADS+" \
    -o "+DATADIR+"/photoz.fits", shell=True, check=True)
print("\n")


print("==> create combined output table")
# update the combined data table
run("data_table_hstack.py \
    -i "+MOCKoutfull+" \
       "+DATADIR+"/recal_weights.fits \
       "+DATADIR+"/photoz.fits \
    -o "+MOCKoutfull, shell=True, check=True)
print("\n")


print("==> apply final selection")
# select objects with recal_weight>0 and M_0<90
run("data_table_filter.py \
    -i "+MOCKoutfull+" \
    "+select_rules+" \
    -o "+MOCKout, shell=True, check=True)
print("\n")


print("done!")