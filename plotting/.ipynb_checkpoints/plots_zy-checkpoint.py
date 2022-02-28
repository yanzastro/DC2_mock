import matplotlib.pyplot as plt
import numpy as np
from thcolor import *

def hist_plot(data, bins, color, ax, fmt='', **kargs):
    '''
    This function plots the normalized histogram of a dataset. \
    Parameters are the same as plt.hist()
    '''
    ax.hist(data, bins, color=color, alpha=0.5, density=True, **kargs)
    ax.hist(data, bins, color=color, histtype='step', density=True)
    return

def binned_mean_plot(bindata, stat, bins, color, ax, label='', fmt='-'):
    '''
    This function plots the mean value of 'stat' in each bin of the 'bindata'.
    Input:
    bindata (1-d array): data that defines the bin. Should have the same shape as \
    stat;
    stat: (1-d array): data to be binned;
    bins (integer or 1-d array): number of bins or the array that defines bin edges;
    color: color for the plot;
    ax: the axis to be plotted in;
    label: the label of the stat;
    fmt: format of the line
    '''
    stat_sum, edges = np.histogram(bindata, bins=bins, weights=stat)
    norm, edges = np.histogram(bindata, bins=bins)
    bincenter = (edges[1:]+edges[:-1])/2
    stat_mean = stat_sum/norm
    #print(stat_mean)
    ax.plot(bincenter, stat_mean, color=color, label=label, linestyle=fmt)
    return

def mad_plot(bindata, stat, bins, color, ax, label='', fmt='-'):
    '''
    This function calculates and plots the median-absolute-deviation of 'stat' in each \
    bin defined by 'bindata' and 'bins'.
    bindata (1-d array): data that defines the bin. Should have the same shape as \
    stat;
    stat: (1-d array): data whose MAD to be calculated and binned;
    bins (integer or 1-d array): number of bins or the array that defines bin edges;
    color: color for the plot;
    ax: the axis to be plotted in;
    label: the label of the stat;
    fmt: format of the line
    '''
    znorms, edges = np.histogram(bindata, bins=bins)
    dzs, edges = np.histogram(bindata, bins=bins, weights=stat) 
    bincenter = (edges[1:]+edges[:-1])/2
    mad = np.zeros(edges.size-1)
    for i in range(len(edges) - 1):
        bin_mask = (
            (bindata >= edges[i]) &
            (bindata < edges[i + 1]))
        mad[i] = 1.4826 * np.median(
            np.abs(stat[bin_mask] - (dzs/znorms)[i]))
    ax.plot(bincenter, mad, color=color, label=label, linestyle=fmt)
    return

def plot_BPZ_stats(z_spec, z_phot, mag, axes, color='C1', fmt='-', survey_label='', 
                   zb_label='Z_B', zspec_label='z_spec', 
                   zphot_label='z_phot', mag_label='mag_r', 
                   zbin = np.arange(0.05, 1.5+0.05, 0.05),
                   magbin = np.arange(20, 25, .1)):
    
    '''
    This function is a wrapper to generate BPZ statistics like Fig.2 in the paper \
    arxiv:2007.01846.
    z_spec: spectroscopic redshift;
    z_phot: photometric redshift;
    mag: magnitude to be binned;
    axes: axes to be plotted in;
    color: color of the lines and histograms;
    fmt: format of the lines;
    survey_label: label of the dataset;
    zb_label: the label for x-axis of z_phot;
    zspec_label: the label for x-axis of z_spec;
    mag_label: the label for x-axis of mag;
    survey_label:
    zbin: bin edge of z_phot and z_spec;
    magbin: bin edge of mag;
    '''
    
    dz = (z_phot-z_spec)/(1+z_spec)
    dz015 = (np.abs(dz) > 0.15)

    z_spec_ = z_spec#[z_spec<zbin[-1]]
    z_phot_ = z_phot#[z_spec<zbin[-1]]
    mag_ = mag#[z_spec<zbin[-1]]
    dz_ = dz#[z_spec<zbin[-1]]
    dz015_ = dz015#[z_spec<zbin[-1]]
    
    hist_plot(z_spec_, zbin, color=color, ax=axes[3][0], fmt=fmt)
    hist_plot(z_phot_, zbin, color=color, ax=axes[3][1], fmt=fmt)
    hist_plot(mag_, magbin, color=color, ax=axes[3][2], fmt=fmt)
    axes[3][0].set_ylabel('PDF', fontsize=14)
    axes[3][0].set_xlabel(zspec_label, fontsize=14)
    axes[3][1].set_xlabel(zphot_label, fontsize=14)
    axes[3][2].set_xlabel(mag_label)

    mad_plot(z_spec_, dz_, zbin, color, axes[0][0], label=survey_label, fmt=fmt)
    mad_plot(z_phot_, dz_, zbin, color, axes[0][1], fmt=fmt)
    mad_plot(mag_, dz_, magbin, color, axes[0][2], fmt=fmt)
    axes[0][0].set_ylabel(r'$\sigma_{\mathrm{m}}$', fontsize=14)

    binned_mean_plot(z_spec_, dz_, zbin, color, axes[1][0], fmt=fmt)
    binned_mean_plot(z_phot_, dz_, zbin, color, axes[1][1], fmt=fmt)
    binned_mean_plot(mag_, dz_, magbin, color, axes[1][2], fmt=fmt)
    axes[1][0].set_ylabel(r'$\mu_{\delta z}$', fontsize=14)

    binned_mean_plot(z_spec_, dz015_*1.0, zbin, color, axes[2][0], fmt=fmt)
    binned_mean_plot(z_phot_, dz015_*1.0, zbin, color, axes[2][1], fmt=fmt)
    binned_mean_plot(mag_, dz015_*1.0, magbin, color, axes[2][2], fmt=fmt)
    axes[2][0].set_ylabel(r'$\zeta_{0.15}$', fontsize=14)
    
    return