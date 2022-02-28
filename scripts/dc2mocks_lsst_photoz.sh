#!/usr/bin/env bash

###############################################################################
#                                                                             #
#   Create a mock catalogue for LSST derived from the DC2 galaxy mock        #
#   catalogue. The catalogue contains a KiDS like photometry, lensfit         #
#   weights and BPZ photo-z.                                                  #
#                                                                             #
###############################################################################

THREADS=$(echo ${1:-$(nproc)})

# data paths
SURVEY="lsst"
DATADIR=${HOME}/DATA/cosmoDC2/LSST_magnification_off_${SURVEY}
mkdir -p ${DATADIR}

# static file names
MOCKraw=${HOME}/DATA/cosmoDC2/cosmodc2_smallsample_magcut_sparse.fits
MOCKmasked=${DATADIR}/DC2_shapes_halos_WL_masked.fits
MOCKoutfull=${DATADIR}/DC2_all.fits
MOCKout=${DATADIR}/DC2_LSST.fits
MOCKpipe=${HOME}/research/projects/dc2_mock/codes/pipeline
MOCKplot=${HOME}/research/projects/dc2_mock/codes/plotting
tabletool=${HOME}/research/src/table_tools
# LSST data table for check plots
dataLSST=${HOME}/DATA/LSST/KiDS_VIKING/LSST_north.cat
dataLSST_6bands=${HOME}/DATA/cosmoDC2/LSST_photoz.fits

sh ../environment.sh

export PYTHONPATH=${HOME}/research/projects/mice2/code/table_tools:$PYTHONPATH
export PYTHONPATH=${HOME}/research/projects/mice2/code/stomp_tools:$PYTHONPATH
export PYTHONPATH=${HOME}/research/projects/mice2/code/astropandas:$PYTHONPATH
#export PYTHONPATH=${HOME}/research/projects/mice2/code/MICE2_mocks:$PYTHONPATH


# constant parameters
# BOUNDS="35 55 6 24"  # footprint that is used for mocks: RAmin/max DECmin/max
BOUNDS="40 60 -60 -20"  # footprint that is used for mocks: RAmin/max DECmin/max

RAname=ra
DECname=dec

### Filters: 

# Filters=u     g     r     i     z     y    
PSFs="    0.77  0.73  0.70  0.67  0.65  0.63  "
MAGlims=" 27.85 29.15 29.25 28.55 27.85 26.65 "
MAGsig=1  # the original value is 1.0, however a slightly larger values
            # yields smaller photometric uncertainties and a better match in
            # the spec-z vs phot-z distribution between data and mocks

#export BPZPATH=${HOME}/src/bpz-1.99.3
#export BPZPYTHON=${HOME}/BPZenv/bin/python2
export BPZPATH=${HOME}/research/src/bpz-1.99.3
export BPZPYTHON=${HOME}/anaconda3/envs/python2/bin/python2
chmod -R 777 ${MOCKpipe}

#: <<'END'

echo "==> generate base footprint for LSST"
test -e ${DATADIR}/footprint.txt && rm ${DATADIR}/footprint.txt
# Create bounds of ~343 sqdeg (effective LSST area). Create a pointing list of
# 440 pointings (20x22) with ~0.7 sqdeg each (mean pointing area in LSST CC
# data).
python ${MOCKpipe}/mocks_generate_footprint.py \
    -b $BOUNDS \
    --survey LSST \
    -f ${DATADIR}/footprint.txt \
    -p ${DATADIR}/pointings_LSST.txt \
    --grid 20 22
echo ""

echo "==> mask DC2 to LSST footprint"
# apply the bounds to the DC2 catalogue
python ${tabletool}/data_table_mask_ra_dec.py \
    -i ${MOCKraw} \
    -b $BOUNDS \
    --ra $RAname --dec $DECname \
    -o ${MOCKmasked}
echo ""


echo "==> apply evolution correction"
# automatically applied to any existing MICE2 filter column
python ${MOCKpipe}/mocks_dc2_mag_evolved.py \
    -i ${MOCKmasked} \
    -o ${DATADIR}/magnitudes_evolved.fits \
    --evo False
# update the combined data table
python ${tabletool}/data_table_hstack.py \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_evolved.fits \
    -o ${MOCKoutfull} 
echo ""


echo "==> compute point source S/N correction"
# Compute the effective radius (that contains 50% of the luminosity), compute
# the observational size using the PSFs, scale this with a factor of 2.5
# (similar to what sextractor would do) to get a mock aperture. Finally
# calculate a correction factor for the S/N based on the aperture area compared
# to a point source (= PSF area).
python ${MOCKpipe}/mocks_extended_object_sn.py \
    -i ${MOCKoutfull} \
    --total-size-minor size_minor_true --total-size size_true \
    --psf $PSFs \
    --filters \
        mag_u_lsst\
        mag_g_lsst\
        mag_r_lsst\
        mag_i_lsst\
        mag_z_lsst\
        mag_y_lsst\
    --scale 2.5  --flux-frac 0.5\
    --threads $THREADS \
    -o ${DATADIR}/apertures.fits

# update the combined data table
python ${tabletool}/data_table_hstack.py \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_evolved.fits \
       ${DATADIR}/apertures.fits \
    -o ${MOCKoutfull}
echo 



echo "==> generate photometry realisation"
# Based on the KiDS limiting magnitudes, calcalute the mock galaxy S/N and
# apply the aperture size S/N correction to obtain a KiDS-like magnitude
# realisation.
python ${MOCKpipe}/mocks_photometry_realisation.py \
    -i ${MOCKoutfull} \
    --filters \
        mag_u_lsst_evo\
        mag_g_lsst_evo\
        mag_r_lsst_evo\
        mag_i_lsst_evo\
        mag_z_lsst_evo\
        mag_y_lsst_evo\
    --limits $MAGlims \
    --significance $MAGsig \
    --sn-factors \
        sn_factor_mag_u_lsst\
        sn_factor_mag_g_lsst\
        sn_factor_mag_r_lsst\
        sn_factor_mag_i_lsst\
        sn_factor_mag_z_lsst\
        sn_factor_mag_y_lsst\
    -o ${DATADIR}/magnitudes_observed.fits
    
# update the combined data table
python ${tabletool}/data_table_hstack.py \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_observed.fits \
    -o ${MOCKoutfull}
echo ""

#: << 'END'

echo "==> assign galaxy weights"
# Assign lensfit weights by matching mock galaxies in 9-band magnitude space to
# their nearest neighbour LSST galaxies using the super-user catalogues which
# contain objects with recal_weight<=0. Mock galaxies that do not have a
# nearest neighbour within --r-max (Minkowski distance) are assigned the
# --fallback values.
python ${MOCKpipe}/mocks_draw_property.py \
    -s ${MOCKoutfull} \
    --s-attr \
        mag_u_lsst_obs \
        mag_g_lsst_obs \
        mag_r_lsst_obs \
        mag_i_lsst_obs \
        mag_z_lsst_obs \
        mag_y_lsst_obs \
    --s-prop recal_weight \
    -d ${HOME}/DATA/LSST/recal_weights.fits \
    --d-attr \
        MAG_GAAP_u \
        MAG_GAAP_g \
        MAG_GAAP_r \
        MAG_GAAP_i \
        MAG_GAAP_Z \
        MAG_GAAP_Y \
    --d-prop weight \
    --r-max 1.0 \
    --fallback 0.0 \
    --threads $THREADS \
    -t ${HOME}/DATA/LSST/dc2_recal_weights.tree.pickle \
    -o ${DATADIR}/recal_weights.fits
echo ""

#END

echo "==> compute photo-zs"
# Run BPZ on the mock galaxy photometry using the LSST setup (prior: NGVS,
# templates: Capak CWWSB), the prior limited to 0.7 < z < 1.43.
python ${MOCKpipe}/mocks_bpz_wrapper.py \
    -i ${MOCKoutfull} \
    --filters \
        mag_u_${SURVEY}_obs \
        mag_g_${SURVEY}_obs \
        mag_r_${SURVEY}_obs \
        mag_i_${SURVEY}_obs \
        mag_z_${SURVEY}_obs \
        mag_y_lsst_obs \
    --errors \
        mag_u_${SURVEY}_obserr \
        mag_g_${SURVEY}_obserr \
        mag_r_${SURVEY}_obserr \
        mag_i_${SURVEY}_obserr \
        mag_z_${SURVEY}_obserr \
        mag_y_lsst_obserr \
    --z-min 0.06674 \
    --z-max 1.42667 \
    --templates CWWSB_capak \
    --prior NGVS \
    --prior-filter mag_i_lsst_obs \
    --threads $THREADS \
    -o ${DATADIR}/photoz.fits
echo ""


echo "==> create full output table"
python ${tabletool}/data_table_hstack.py \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_evolved.fits \
       ${DATADIR}/apertures.fits \
       ${DATADIR}/magnitudes_observed.fits \
       ${DATADIR}/recal_weights.fits \
       ${DATADIR}/photoz.fits \
    -o ${MOCKoutfull}
echo ""

echo "==> apply final LSST selection"
# select objects with recal_weight>0 and M_0<90
python ${tabletool}/data_table_filter.py \
    -i ${MOCKoutfull} \
    --rule recal_weight gg 0.0 \
    --rule M_0 ll 90.0 \
    -o ${MOCKout}
echo ""

: << 'END'

echo "==> plot aperture statistics"
${MOCKplot}/plot_extended_object_sn \
    -i ${MOCKout} \
    --filters \
        mag_u_lsst\
        mag_g_lsst\
        mag_r_lsst\
        mag_i_lsst\
        mag_z_lsst\
        mag_y_lsst\
        mag_u_sdss\
        mag_g_sdss\
        mag_r_sdss\
        mag_i_sdss\
        mag_z_sdss
echo ""



echo "==> plot magnitude statistics"
${MOCKplot}/plot_photometry_realisation \
    -s ${MOCKout} \
    --s-filters \
        mag_u_${SURVEY}_obs \
        mag_g_${SURVEY}_obs \
        mag_r_${SURVEY}_obs \
        mag_i_${SURVEY}_obs \
        mag_z_${SURVEY}_obs \
        mag_y_lsst_obs \
    --s-errors \
        mag_u_${SURVEY}_obserr \
        mag_g_${SURVEY}_obserr \
        mag_r_${SURVEY}_obserr \
        mag_i_${SURVEY}_obserr \
        mag_z_${SURVEY}_obserr \
        mag_y_lsst_obserr \
    -d ${dataLSST} \
    --d-filters \
        MAG_GAAP_u \
        MAG_GAAP_g \
        MAG_GAAP_r \
        MAG_GAAP_i \
        MAG_GAAP_Z \
        MAG_GAAP_Y \
    --d-errors \
        MAGERR_GAAP_u \
        MAGERR_GAAP_g \
        MAGERR_GAAP_r \
        MAGERR_GAAP_i \
        MAGERR_GAAP_Z \
        MAGERR_GAAP_Y \
    --d-extinct \
        EXTINCTION_u \
        EXTINCTION_g \
        EXTINCTION_r \
        EXTINCTION_i \
        EXTINCTION_Z \
        EXTINCTION_Y 
echo ""



echo "==> plot weight statistics"
${MOCKplot}/plot_draw_property \
    -s ${MOCKout} \
    --s-prop recal_weight \
    --s-filters \
        mag_u_${SURVEY}_obs \
        mag_g_${SURVEY}_obs \
        mag_r_${SURVEY}_obs \
        mag_i_${SURVEY}_obs \
        mag_z_${SURVEY}_obs \
        mag_y_lsst_obs \
    -d ${dataLSST} \
    --d-prop recal_weight \
    --d-filters \
        MAG_GAAP_u \
        MAG_GAAP_g \
        MAG_GAAP_r \
        MAG_GAAP_i \
        MAG_GAAP_Z \
        MAG_GAAP_Y 
echo ""

#END

echo "==> plot photo-z statistics"
${MOCKplot}/plot_bpz_wrapper \
    -s ${MOCKout} \
    --s-z-true redshift \
    -d ${dataLSST_6bands} \
    --d-zb Z_B
echo ""

END