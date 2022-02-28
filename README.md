# DC2_mocks

This Repository provides code to create galaxy mock catalogues based on
[cosmoDC2](https://github.com/LSSTDESC/cosmodc2) galaxy catalogues.


## Requirements

The pipeline is written in Python3 and requires the following non-standard
packages:
- `numpy` and `scipy`
- `astropy>=3.0` (recommended for the improved astropy.table performance)
- `matplotlib>=2.0` for the plotting scripts
- `pyYAML` for reading config files

Additionally, the wrapper scripts in `./scripts` make use of
an external packages that provide convenience functions to handle data tables:
- [jlvdb/table_tools](https://github.com/jlvdb/table_tools) (script calls
starting with `data_table_`)
The path to `table_tools` must be included in `$PATH` and `$PYTHONPATH`.

To be able to compute photometric redshifts
[BPZ](http://www.stsci.edu/~dcoe/BPZ/) is requried.


## Instructions

Starting from the cosmoDC2 base catalogues, the pipeline allows to model various
observational selection functions:

- Spectroscopic surveys: GAMA, SDSS (main sample, BOSS and QSOs), 
WiggleZ, DEEP2, zCOSMOS and VVDS (2h field)
- Photometric surveys: Examples to create KiDS-VIKING (KV450,
`./KV450`) and Legacy Survey of Space and Time are included.

The pipeline allows to attach realistic photometry realisations to the cosmoDC2
catalogues, photometric redshifts, galaxy weights (real galaxy weights needed), and spectroscopic success
rates for some of the included spectroscopic selection functions.


### Data Access

The MICE2 base catalogues can be downloaded from
[LSST DESC](https://portal.nersc.gov/project/lsst/cosmoDC2/_README.html). The data can be accessed via [
gcr-catalogs](https://github.com/LSSTDESC/gcr-catalogs).Recommended column selections are

```
[['ra',
 'dec',
 'redshift',
 'shear1',
 'shear2',
 'size_minor_true',
 'size_true',
 'convergence',
 'is_central',
 'mag_u_lsst',
 'mag_g_lsst',
 'mag_r_lsst',
 'mag_i_lsst',
 'mag_z_lsst',
 'mag_y_lsst',
 'mag_u_sdss',
 'mag_g_sdss',
 'mag_r_sdss',
 'mag_i_sdss',
 'mag_z_sdss']]
```

The meaning of each column of cosmoDC2 catalog can be found from [Schema of GCR Catalogs as used in LSST DESC](https://github.com/LSSTDESC/gcr-catalogs/blob/master/GCRCatalogs/SCHEMA.md)


### Set up environments

The script environment.sh sets up paths to DC2 mock pipelines and [jlvdb/table_tools](https://github.com/jlvdb/table_tools). The user needs to change the paths in this file and run it with `sh environment.sh`, then `source ~/.bashrc`.

### Set up configurations for a survey

The information needed for generating mock catalogues are stored in a `yaml` config file. Users can refer to the sample config files in `./scripts/config_yamls/`.

### Creating Photometric Catalogues

To creat a photometric catalogue for KV450, for example, one runs

`python ./scripts/dc2mocks_photo_realisation.py ./scripts/config_yamls/KV450_config.yaml`

The steps in the script include:

1. generate the footprint for a survey.
2. computing S/N for each bands according to limiting magnitudes, PSF sizes and galaxy shapes.
3. Adding a photometry realization 
4. Assigning galaxy weights by nearest neighbour matching between mock and data
in magnitude space
5. Computing photometric redshifts with BPZ


### Creating Spectroscopic Catalogues

The pipeline bundles a variety of spectroscopic (target) selection functions:
- DEEP2 (Newman et al. 2013)
- GAMA (Driver et al. 2011)
- SDSS
  - main sample (Strauss et al. 2002)
  - BOSS (Dawson et al. 2013)
  - QSO sample (Schneider et al. 2010a, only attempting to match the redshift 
    distribution)
- WiggleZ (Drinkwater et al. 2010, missing UV information replaced by redshift 
  distribution matching)
- VVDS (LeFèvre et al. 2005, only 2h field)
- zCOSMOS (Lilly et al. 2009, only bright sample)

These selection functions are defined in `./pipeline/specz_selection.py` and
have some adjustments applied in order to give a better match to the data
colour and/or redshift distributions.

To run spectroscopic selections for DEEP2, VVDSf02, zCOSMOS, for example, one create a photometric catalogue first, then run 

`python dc2mocks_spec_selection.py ./config_yamls/KV450_config.yaml DEEP2 VVDSf02 zCOSMOS`


### Plotting photo-z statistics

The functions needed to plot photo-z statistics (like Fig.1 and Fig.2 in  [van den Busch et al](https://arxiv.org/abs/2007.01846)) is given in `./plotting/`. Some examples are presented as `jupyter notebook` in `./notebooks`.
