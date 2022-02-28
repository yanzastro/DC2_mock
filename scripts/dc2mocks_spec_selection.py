import yaml
import numpy as np
from yaml import Loader
from subprocess import run
import subprocess
import os
from astropy.io import fits
import sys

survey_folder = os.path.expanduser('~')+"/DATA/mocks/KV450/SPECZ/"  # need to be specified!

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

THREADS = str(config['threads'])
DATADIR = config['paths']['DATADIR']
OUTROOT = DATADIR + '/REALISATION/'
MOCKout = DATADIR + config['paths']['MOCKout']

if ~os.path.isdir(DATADIR):
    os.system('mkdir '+DATADIR)

if ~os.path.isdir(OUTROOT):
    os.system('mkdir '+OUTROOT)
    
surveys = sys.argv[2:]#['DEEP2', 'VVDSf02', 'zCOSMOS']

for survey in surveys:
    print("==> generate photometry realizations and apply "+survey+" selection")
    if ~os.path.isdir(OUTROOT+"/"+survey+"_phot_samples/"):
        os.system("mkdir "+OUTROOT+"/"+survey+"_phot_samples/")
    survey_file = fits.open(survey_folder+survey+"_masked.fits")
    n_obj = len(survey_file[1].data)
    print(n_obj)
    run("mocks_DC2_specz_sample.py \
        -s "+MOCKout+" \
        --s-type LSST \
        --survey "+survey+" \
        --d-z-spec z_spec \
        --n-data "+str(n_obj)+" \
        -o "+OUTROOT+"/"+survey+"_phot_samples/"+survey+"_phot_samples.fits", shell=True, check=True)

print("done!")


