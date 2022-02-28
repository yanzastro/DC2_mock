#!/usr/bin/env bash

###############################################################################
#                                                                             #
#   Create a mock catalogue for KV450 derived from the DC2 galaxy mock        #
#   catalogue. The catalogue contains a KiDS like photometry, lensfit         #
#   weights and BPZ photo-z. Then apply selection function from three         #
#   deepfield surveys: DEEP2, VVDS, zCOSMOS                                   #
#                                                                             #
###############################################################################

THREADS=$(echo ${1:-$(nproc)})

# data paths
SURVEY="lsst"
DATADIR=${HOME}/DATA/cosmoDC2/KV450_${SURVEY}
mkdir -p ${DATADIR}

# static file names
MOCKraw=${HOME}/DATA/cosmoDC2/cosmodc2_smallsample_magcut.fits
MOCKmasked=${DATADIR}/DC2_shapes_halos_WL_masked.fits

OUTROOT=${HOME}/DATA/cosmoDC2/REALISATIONS
MOCKoutfull=${DATADIR}/DC2_all.fits
MOCKout=${DATADIR}/DC2_KV450.fits

MOCKpipe=${HOME}/research/projects/dc2_mock/codes/pipeline
MOCKplot=${HOME}/research/projects/dc2_mock/codes/plotting
tabletool=${HOME}/research/src/table_tools

# KV450 data table for check plots
dataKV450=${HOME}/DATA/KV450/KiDS_VIKING/KV450_north.cat
dataKV450_6bands=${HOME}/DATA/cosmoDC2/KV450_photoz.fits

#sh ../environment.sh

#export PYTHONPATH=${HOME}/research/projects/mice2/code/table_tools:$PYTHONPATH
#export PYTHONPATH=${HOME}/research/projects/mice2/code/stomp_tools:$PYTHONPATH
#export PYTHONPATH=${HOME}/research/projects/mice2/code/astropandas:$PYTHONPATH
#export PYTHONPATH=${HOME}/research/projects/mice2/code/MICE2_mocks:$PYTHONPATH


# constant parameters
# BOUNDS="35 55 6 24"  # footprint that is used for mocks: RAmin/max DECmin/max
BOUNDS="40 60 -60 -20"  # footprint that is used for mocks: RAmin/max DECmin/max

RAname=ra
DECname=dec

### Filters: 

# Filters=u    g    r    i    z    y    u    g    r    i    z    y
PSFs="    1.0  0.9  0.7  0.8  1.0  1.0  1.0  0.9  0.7  0.8  1.0  "
MAGlims=" 25.5 26.3 26.2 24.9 24.9 24.1 25.5 26.3 26.2 24.9 24.9 "
MAGsig=1.1  # the original value is 1.0, however a slightly larger values
            # yields smaller photometric uncertainties and a better match in
            # the spec-z vs phot-z distribution between data and mocks

#export BPZPATH=${HOME}/src/bpz-1.99.3
#export BPZPYTHON=${HOME}/BPZenv/bin/python2
#export BPZPATH=${HOME}/research/src/bpz-1.99.3
#export BPZPYTHON=${HOME}/anaconda3/envs/python2/bin/python2
#chmod -R 777 ${MOCKpipe}

echo "==> generate base footprint for KV450"
test -e ${DATADIR}/footprint.txt && rm ${DATADIR}/footprint.txt
# Create bounds of ~343 sqdeg (effective KV450 area). Create a pointing list of
# 440 pointings (20x22) with ~0.7 sqdeg each (mean pointing area in KV450 CC
# data).
python ${MOCKpipe}/mocks_generate_footprint.py \
    -b $BOUNDS \
    --survey KV450 \
    -f ${DATADIR}/footprint.txt \
    -p ${DATADIR}/pointings_KV450.txt \
    --grid 20 22
echo ""


echo "==> mask DC2 to KV450 footprint"
# apply the bounds to the DC2 catalogue
${tabletool}/data_table_mask_ra_dec \
    -i ${MOCKraw} \
    -b $BOUNDS \
    --ra $RAname --dec $DECname \
    -o ${MOCKmasked}
echo ""
: << 'END'


echo "==> apply evolution correction"
# automatically applied to any existing MICE2 filter column
${MOCKpipe}/mocks_dc2_mag_evolved \
    -i ${MOCKmasked} \
    -o ${DATADIR}/magnitudes_evolved.fits \
    --evo False
# update the combined data table
${tabletool}/data_table_hstack \
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
${MOCKpipe}/mocks_extended_object_sn \
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
        mag_u_sdss\
        mag_g_sdss\
        mag_r_sdss\
        mag_i_sdss\
        mag_z_sdss\
    --scale 2.5  --flux-frac 0.5\
    --threads $THREADS \
    -o ${DATADIR}/apertures.fits
# update the combined data table
${tabletool}/data_table_hstack \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_evolved.fits \
       ${DATADIR}/apertures.fits \
    -o ${MOCKoutfull}
echo 



echo "==> generate photometry realisation"
# Based on the KiDS limiting magnitudes, calcalute the mock galaxy S/N and
# apply the aperture size S/N correction to obtain a KiDS-like magnitude
# realisation.
${MOCKpipe}/mocks_photometry_realisation \
    -i ${MOCKoutfull} \
    --filters \
        mag_u_lsst_evo\
        mag_g_lsst_evo\
        mag_r_lsst_evo\
        mag_i_lsst_evo\
        mag_z_lsst_evo\
        mag_y_lsst_evo\
        mag_u_sdss_evo\
        mag_g_sdss_evo\
        mag_r_sdss_evo\
        mag_i_sdss_evo\
        mag_z_sdss_evo\
    --limits $MAGlims \
    --significance $MAGsig \
    --sn-factors \
        sn_factor_mag_u_lsst\
        sn_factor_mag_g_lsst\
        sn_factor_mag_r_lsst\
        sn_factor_mag_i_lsst\
        sn_factor_mag_z_lsst\
        sn_factor_mag_y_lsst\
        sn_factor_mag_u_sdss\
        sn_factor_mag_g_sdss\
        sn_factor_mag_r_sdss\
        sn_factor_mag_i_sdss\
        sn_factor_mag_z_sdss\
    -o ${DATADIR}/magnitudes_observed.fits
    
# update the combined data table
${tabletool}/data_table_hstack \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_observed.fits \
    -o ${MOCKoutfull}
echo ""


echo "==> assign galaxy weights"
# Assign lensfit weights by matching mock galaxies in 9-band magnitude space to
# their nearest neighbour KV450 galaxies using the super-user catalogues which
# contain objects with recal_weight<=0. Mock galaxies that do not have a
# nearest neighbour within --r-max (Minkowski distance) are assigned the
# --fallback values.
${MOCKpipe}/mocks_draw_property \
    -s ${MOCKoutfull} \
    --s-attr \
        mag_u_lsst_obs \
        mag_g_lsst_obs \
        mag_r_lsst_obs \
        mag_i_lsst_obs \
        mag_z_lsst_obs \
        mag_y_lsst_obs \
    --s-prop recal_weight \
    -d ${HOME}/DATA/KV450/recal_weights.fits \
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
    -t ${HOME}/DATA/KV450/dc2_recal_weights.tree.pickle \
    -o ${DATADIR}/recal_weights.fits
echo ""

#END

echo "==> compute photo-zs"
# Run BPZ on the mock galaxy photometry using the KV450 setup (prior: NGVS,
# templates: Capak CWWSB), the prior limited to 0.7 < z < 1.43.
${MOCKpipe}/mocks_bpz_wrapper \
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
${tabletool}/data_table_hstack \
    -i ${MOCKmasked} \
       ${DATADIR}/magnitudes_evolved.fits \
       ${DATADIR}/apertures.fits \
       ${DATADIR}/magnitudes_observed.fits \
       ${DATADIR}/recal_weights.fits \
       ${DATADIR}/photoz.fits \
    -o ${MOCKoutfull}
echo ""

echo "==> apply final KV450 selection"
# select objects with recal_weight>0 and M_0<90
${tabletool}/data_table_filter \
    -i ${MOCKoutfull} \
    --rule recal_weight gg 0.0 \
    --rule M_0 ll 90.0 \
    -o ${MOCKout}
echo ""
#END

for survey in DEEP2 VVDSf02 zCOSMOS; do
    echo "==> generate photometry realizations and apply ${survey} selection"
    mkdir ${OUTROOT}/${survey}_phot_samples/
    n_obj=$(data_table_shape ${HOME}/DATA/KV450/SPECZ/${survey}_masked.fits)
    ${MOCKpipe}/mocks_DC2_specz_sample \
        -s ${MOCKout} \
        --s-type KV450lsst \
        --survey ${survey} \
        --d-z-spec z_spec \
        --n-data ${n_obj} \
        -o ${OUTROOT}/${survey}_phot_samples/${survey}_phot_samples_0.fits
    done
done

END