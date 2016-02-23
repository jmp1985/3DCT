#
#
#

#!/usr/bin/env python
"""
Statstical analysis of presynaptic structures: synaptic vesicles, connectors 
and tethers obtained for different treatments.

Important note: This script is depreciated, use presynaptic_stats.py.

Reason: This script was used with the old (result files based) info about
the location of various pickle files and related metadata. This was supreceeded
by the catalog-based info.

ToDo: Make appropriate classes and convert majority of functions defined here
to methods.

# Author: Vladan Lucic (Max Planck Institute for Biochemistry)
# $Id: presynaptic_stats_old.py 1003 2013-12-09 10:00:26Z vladan $
"""
__version__ = "$Revision: 1003 $"

import sys
import os
import logging
import itertools
from copy import copy, deepcopy
import pickle

import numpy 
import scipy 
import scipy.stats
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass

import pyto
import result_files
import imaging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%d %b %Y %H:%M:%S')


##############################################################
#
# Parameters
#
##############################################################

# experiment categories
categories = ['plain', 'HTS', 'cemovis', 'KCl', 'okadaic', 'TeTx']
categories_no_sect = ['plain', 'HTS', 'KCl', 'okadaic', 'TeTx']

# reference category
reference='plain'

# 
distance_bins = [0, 45, 75, 150, 250]
layers_distance_bins = [10, 45, 75, 150, 250]
distance_bins_label = 'Distance to the AZ [nm]'
reference_distance_bin = 0

#


# used for binning of connection lengths
rough_length_bins = [0, 10, 20, 30, 40]
fine_length_bins = [0, 5, 10, 15, 20, 25, 30, 35, 40]

#connected_bins = [0,1,100]
teth_bins_label = ['non-tether', 'tethered']
conn_bins_label = ['non-connect', 'connected']

# bins for number of connections
n_conn_bins = [0,1,2,5,100]
n_conn_bins_label = 'N connections'

# layer bins
layer_bins = range(0, 250, 5)

# print format
density_format = {
    'mean' : '   %6.3f ',
    'std' : '   %6.3f ',
    'sem' : '   %6.3f ',
    'diff_bin_mean' : '   %6.3f '
    }

# plot 
plot_ = True
length_histo_range = [0, 40]
length_histo_bins = 8

category_color = {
    'plain' : 'k',
    'KCl' : 'r',
    'HTS' : 'b',
    'cemovis' : 'g',
    'okadaic' : 'y',
    'TeTx' : 'm',
    'non_rrp' : 'turquoise',
    'rrp' : 'grey',
    'tether' : 'orange',
    'conn' : 'b'
    }
category_color_default = 'grey'

category_label = {
    'plain' : 'Plain',
    'KCl' : 'KCl',
    'HTS' : 'HTS',
    'cemovis' : 'Slices',
    'okadaic' : 'OA',
    'TeTx' : 'TeTx',
    'non_rrp' : 'Plain non-RRP',
    'rrp' : 'Plain RRP'
    }

type_marker = {
    'all' : 'o',
    'tethered' : '+',
    'non-tethered' : 'o'
    }

bar_width = 0.15

# fontsize for confidence levels
font_size = 7

# alpha (global variable)
category_alpha = {
    'plain' : 1,
    'KCl' : 1,
    'HTS' : 1,
    'cemovis' : 1,
    'okadaic' : 1,
    'TeTx' : 1,
    'non_rrp' : 1,
    'rrp' : 1,
    'tether' : 1,
    'conn' : 1
    }
category_alpha_default = 1

################################################################
#
# Work
#
###############################################################

            
###############################################################
#
# Number and fraction of connected / tethered vesicles
#

def get_fraction_tethered_sv(sv, reference, categories=None, out=None, 
        n_tether_name='n_tether', bins=None, bin_names=None, bin_label='', 
        reference_bin=None, plot_=False, category_color=None, bar_width=None, 
        plot_confidence='stars', font_size=None, title=None):
    """
    Calculates numbers of tethered and non-tethered vesicles and the fraction 
    of tethered svs. Plots these values together with the chi-square confidence
    levels.

    Argument sv can be one or a list of Groups objects.

    """
    return get_fraction_connected_sv(sv=sv, reference=reference, 
         categories=categories, out=out, n_conn_name=n_tether_name, 
         bins=bins, bin_names=bin_names, reference_bin=reference_bin, 
         bin_label=bin_label, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, title=title,
         plot_confidence=plot_confidence)

def get_fraction_connected_sv(sv, reference, categories=None, out=None, 
        n_conn_name='n_connection', bins=None, bin_names=None, bin_label='', 
        reference_bin=None, plot_=False, category_color=None, bar_width=None, 
        plot_confidence='stars', font_size=None, title=None):
    """
    Calculates numbers of connected and non-connected vesicles and the fraction 
    of connected svs. Plots these values together with the chi-square confidence
    levels.

    Argument sv can be one or a list of Groups objects.

    """

    # check if one or more bins
    if isinstance(sv, pyto.analysis.Groups):
        sv = [sv]
        one_bin = True
    else:
        one_bin = False

    # find max n_conn_name and set bins for n connected
    all_n_conn = [nt for curr_sv in sv for obs in curr_sv.values() \
                      for nt in getattr(obs, n_conn_name)]
    conn_bins = [0, 1, max(pyto.util.nested.flatten(all_n_conn))]
    conn_index = 1

    # set title
    if title is None:
        if n_conn_name == 'n_tether':
            if one_bin:
                title = 'Tethered svs'
            else:
                title = 'Sv tethering'
        else:
            if one_bin:
                title = 'Connected svs'
            else:
                title = 'Sv connectivity'

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # calculate fractions and stats 
    stats = property_histogram(groups=sv, name=n_conn_name, reference=reference, 
               bins=conn_bins, categories=categories, reference_bin=reference_bin)

    # set attributes for printing and plotting
    for curr_stats in stats:
        for categ_name, categ in zip(curr_stats, curr_stats.values()):

            # all observations of this category together
            categ.value = categ.histo[conn_index]
            categ.fraction = categ.histo_fractions[conn_index]

            # individual observations
            if categ_name is not 'together':
                categ.value_obs = [x[conn_index] for x in categ.histo_obs]
                categ.fraction_obs = \
                    [x[conn_index] for x in categ.histo_fractions_obs]

    # print stats
    if reference_bin is None:
        var_names=['n', 'value', 'fraction', 'chi_square', 'confid'] 
    else:
        var_names=['n', 'value', 'fraction', 'chi_square', 'confid', 
                   'chi_sq_bin', 'confid_bin']
    print_stats(stats=stats, categories=categories, out=out, bins=bins, 
                bin_names=bin_names, var_names=var_names)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Fraction of total sv number')
        plt.xlabel(bin_label)

        # plot fraction connected
        plot_stats(stats=stats, name='fraction', categories=categories, 
                   bar_width=bar_width, category_color=category_color, bins=bins,
                   bin_names=bin_names, font_size=font_size, 
                   confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    if one_bin:
        return stats[0]
    else:
        return stats

def analyze_n_tether(sv, reference, categories=None, n_teth_name='n_tether', 
        out=None, test='t', bins=None, bin_names=None, reference_bin=None, 
        bin_label='', plot_=False, category_color=None, bar_width=None, 
        font_size=None, plot_confidence='stars', title=None):
    """
    """
    if title is None:
        title = 'Number of tethers per sv'

    return analyze_n_connection(sv=sv, reference=reference, categories=categories, 
        n_conn_name=n_teth_name, out=out, test=test, bins=bins, bin_names=bin_names,
        reference_bin=reference_bin, bin_label=bin_label, plot_=plot_, 
        category_color=category_color, bar_width=bar_width, font_size=font_size,
        plot_confidence=plot_confidence, title=title)

def analyze_n_connection(sv, reference, categories=None, 
        n_conn_name='n_connection', out=None, test='t', bins=None, 
        bin_names=None, reference_bin=None, bin_label='', plot_=False, 
        category_color=None, bar_width=None, font_size=None, y_error='sem', 
        plot_confidence='stars', title=None):
    """
    ToDo: replace main part with a call to analyze_item() like in analyze_density.
    """
    
    # set title and x label
    if title is None:
        title = 'Number of connections per sv'
    x_label = bin_label

    # categories
    if categories is None:
        if isinstance(sv, pyto.analysis.Groups):
            categories = conn.keys()
        else: 
            categories = conn[0].keys()

    # calculate stats
    stats = property_stats(groups=sv, name=n_conn_name, reference=reference, 
                           categories=categories, test=test, 
                           reference_bin=reference_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # print stats
    test_method, test_name = define_test(test=test)
    test_name_bin = test_name + '_bin'
    if reference_bin is None:
        var_names=['n', 'mean', 'std', 'sem', test_name, 'confid']
    else:
        var_names=['n', 'mean', 'std', 'sem', test_name, 'confid', test_name_bin, 
                   'confid_bin']
    print_stats(stats=stats, categories=categories, out=out, bins=bins,
                bin_names=bin_names, var_names=var_names)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Mean #/sv')
        if bin_label is None:
            plt.xlabel('')
        else:
            plt.xlabel(bin_label)

        # plot data
        plot_stats(stats=stats, name='mean', categories=categories, 
                   y_error=y_error, bins=bins, bin_names=bin_names, 
                   bar_width=bar_width, category_color=category_color, 
                   font_size=font_size, confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats   

def analyze_n_linked(sv, reference, categories=None, n_conn_name='n_linked', 
        test='t', out=None, bins=None, bin_names=None, reference_bin=None, bin_label='', 
        plot_=False, category_color=None, bar_width=None, font_size=None, 
        plot_confidence='stars', title=None):
    """
    """
    if title is None:
        title = 'Number of linked svs per sv'

    return analyze_n_connection(sv=sv, reference=reference, categories=categories, 
        n_conn_name=n_conn_name, test=test, out=out, bins=bins, bin_names=bin_names,
        reference_bin=reference_bin, bin_label=bin_label, plot_=plot_, 
        category_color=category_color, bar_width=bar_width, font_size=font_size,
        plot_confidence=plot_confidence, title=title)

###############################################################
#
# Vesicle raduis
#

def analyze_radius(sv, reference, categories=None, name='radius_nm', out=None,
                   bins=None, bin_names=None, bin_label='', reference_bin=None,
                   plot_=False, category_color=None, bar_width=None,
                   font_size=None, y_error='sem', plot_confidence='stars',
                   title=None):
    """
    ToDo: replace main part with a call to analyze_item() like in analyze_density.
    """

    # set title
    if title is None:
        title = 'Sv radius analysis'

    # categories
    if categories is None:
        if isinstance(sv, pyto.analysis.Groups):
            categories = conn.keys()
        else: 
            categories = conn[0].keys()

    # calculate stats
    stats = property_stats(groups=sv, name=name, reference=reference, 
                           categories=categories, reference_bin=reference_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # print stats
    if reference_bin is None:
        var_names=['n', 'mean', 'std', 'sem', 't', 'confid']
    else:
        var_names=['n', 'mean', 'std', 'sem', 't', 'confid', 
                   't_bin', 'confid_bin']
    print_stats(stats=stats, categories=categories, out=out, bins=bins, 
                bin_names=bin_names, var_names=var_names)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Mean [nm]')
        if bin_label is None:
            plt.xlabel('')
        else:
            plt.xlabel(bin_label)

        # plot data
        plot_stats(stats=stats, name='mean', categories=categories, 
                   bar_width=bar_width, category_color=category_color, 
                   font_size=font_size, bins=bins, bin_names=bin_names,
                   y_error=y_error, confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats   

def analyze_radius_ntether(sv, reference, bins, name='radius_nm', 
                   categories=None, out=None, n_tether_name='n_tether', 
                   bin_names=None, bin_label='', reference_bin=None,
                   plot_=False, category_color=None, 
                   bar_width=None, font_size=None, title=None):
    """
    """

    # set title
    if title is None:
        title = 'Sv ' + name + ' dependence on the number of tethers'

    # split sv according to the number of tethers
    sv_split = sv.split(name=n_tether_name, value=bins, categories=categories) 

    # analyze
    return analyze_radius(sv=sv_split, reference=reference, name=name,
                   categories=categories, bins=bins, bin_names=bin_names, 
                   bin_label=bin_label, out=out, reference_bin=reference_bin,
                   plot_=plot_, category_color=category_color,
                   bar_width=bar_width, font_size=font_size, title=title)  

def analyze_radius_nconn(sv, reference, bins,  name='radius_nm', 
                   categories=None, out=None, n_conn_name='n_connection',
                   bin_names=None, bin_label='', reference_bin=None,
                   plot_=False, category_color=None, 
                   bar_width=None, font_size=None, title=None):
    """
    """

    # set title
    if title is None:
        title = 'Sv ' + name + ' dependence on the number of connections'

    # split sv according to the number of connections
    sv_split = sv.split(name=n_conn_name, value=bins, categories=categories) 

    # analyze
    return analyze_radius(sv=sv_split, reference=reference, name=name,
                   categories=categories, bins=bins, bin_names=bin_names,
                   bin_label=bin_label, out=out, reference_bin=reference_bin,
                   plot_=plot_, category_color=category_color,
                   bar_width=bar_width, font_size=font_size, title=title)  

###############################################################
#
# Connections / tethers length
#

def analyze_tether_length(tether, reference, categories=None, mode='length', 
            test='t', bins=None, bin_names=None, bin_label=None, 
            reference_bin=None, out=None, plot_=True, bar_width=None, 
            plot_confidence='stars', category_color=None, font_size=None, 
            title=None):
    """
    """

    # length calculation mode
    if mode == 'length':
        name = 'length_nm'
        title = 'Tether length'
    elif mode == 'boundary':
        name = 'boundaryDistance_nm'
        title = 'Distance between tethered svs and az [nm]' 

    # call analyze_connection_length
    return analyze_connection_length(\
        conn=tether, reference=reference, categories=categories, mode=mode, 
        test=test, bins=bins, bin_names=bin_names, bin_label=bin_label, 
        reference_bin=reference_bin, out=None, plot_=plot_, bar_width=bar_width, 
        plot_confidence=plot_confidence, category_color=category_color, 
        font_size=font_size, title=title)

def analyze_connection_length(conn, reference, categories=None, mode='length', 
              test='t', bins=None, bin_names=None, bin_label=None, 
              reference_bin=None, out=None, plot_=True, bar_width=None, 
              plot_confidence='stars', category_color=None, font_size=None, 
              y_error='sem', title=None):
    """
    """
    
    # length calculation mode
    if mode == 'length':
        name = 'length_nm'
        if title is None:
            title = 'Connection length'
    elif mode == 'boundary':
        name = 'boundaryDistance_nm'
        if title is None:
            title = 'Distance between connected svs [nm]' 
        
    # categories
    if categories is None:
        if isinstance(sv, pyto.analysis.Groups):
            categories = conn.keys()
        else: 
            categories = conn[0].keys()

    # calculate stats
    stats = property_stats(groups=conn, name=name, reference=reference, test=test,
                           categories=categories, reference_bin=reference_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # print stats
    test_method, test_name = define_test(test=test)
    test_name_bin = test_name + '_bin'
    if reference_bin is None:
        var_names=['n', 'mean', 'std', 'sem', test_name, 'confid']
    else:
        var_names=['n', 'mean', 'std', 'sem', test_name, 'confid', 
                   test_name_bin, 'confid_bin']
    print_stats(stats=stats, categories=categories, out=out, bins=bins, 
                bin_names=bin_names, var_names=var_names)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Mean [nm]')
        if bin_label is None:
            plt.xlabel('')
        else:
            plt.xlabel(bin_label)

        # plot data
        plot_stats(stats=stats, name='mean', categories=categories, 
                   bar_width=bar_width, category_color=category_color, 
                   font_size=font_size, bins=bins, bin_names=bin_names,
                   y_error=y_error, confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats

def tether_length_histogram(tether, reference, categories=None, mode='length', 
                          bins=None, out=None, plot_=True, bar_width=None, 
                          category_color=None, font_size=None, 
                          plot_confidence='stars', title=None):
    """
    """

    # set title
    if title is None:
        if mode == 'length':
            title = 'Tether length histogram'
        elif mode == 'boundary':
            title = 'Distance between tethered svs and az [nm]' 

    # calculate, print and plot
    return connection_length_histogram(conn=tether, reference=reference, 
               categories=categories, mode=mode, bins=bins, out=out, plot_=plot_, 
               bar_width=bar_width, category_color=category_color, 
               plot_confidence=plot_confidence, font_size=font_size, title=title)

def connection_length_histogram(conn, reference, categories=None, mode='length', 
                          bins=None, out=None, plot_=True, bar_width=None, 
                          category_color=None, font_size=None, 
                          plot_confidence='stars', title=None):
    """
    """

    # set attribute name and title
    if mode == 'length':
        name = 'length_nm'
        if title is None:
            title = 'Connection length histogram'
    elif mode == 'boundary':
        name = 'boundaryDistance_nm'
        if title is None:
            title = 'Distance between connected svs' 

    # calculate stats
    stats = property_histogram(groups=conn, name=name, reference=reference, 
                               bins=bins, categories=categories)

    # make stats for each length bin
    stats_bin = []
    for bin_ind in range(len(bins) - 1):
        curr = deepcopy(stats)
        for categ in curr:
            curr[categ].value = stats[categ].histo[bin_ind]
            curr[categ].fraction = stats[categ].histo_fractions[bin_ind]
        stats_bin.append(curr)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # print stats
    print_stats(stats=stats_bin, categories=categories, out=out, bins=bins, 
                var_names=['n', 'value', 'fraction', 'chi_square', 'confid'])

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Fraction of total number')
        plt.xlabel('Length [nm]')

        # plot data
        plot_stats(stats=stats_bin, name='fraction', categories=categories, 
                   bar_width=bar_width, bins=bins, font_size=font_size,
                   category_color=category_color, confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats

def compare_tether_connection_histogram(tether, conn, category, reference, 
                         bins, out=None, plot_=True, bar_width=None, 
                         category_color=None, font_size=None,
                         plot_confidence='stars'):
    """
    """

    # make instance to hold the data 
    groups = pyto.analysis.Groups()
    groups['tether'] = tether[category]
    groups['conn'] = conn[category]

    # title
    title = 'Comparison of tether and connection lengths'

    return connection_length_histogram(conn=groups, categories=['conn', 'tether'], 
        bins=bins, reference=reference, plot_=plot_, bar_width=bar_width, 
        category_color=category_color, font_size=font_size, 
        plot_confidence=plot_confidence, title=title)

###############################################################
#
# Vesicle density
#

def analyze_density(groups, reference, categories=None, reference_bin=None, 
        out=None, bins=None, bin_names=None, format=None,
        plot_=False, category_color=None, bar_width=None, font_size=None, 
        plot_confidence='stars', title=None, bin_label=None, y_label=None):
    """
    Analyzes difference between vesicle lumen and membrane densities between 
    categoreis and between bins. 
    """

    # name of the difference attribute
    name = 'lum_mem'

    # check if one or more groups
    if isinstance(groups, pyto.analysis.Groups):
        loc_groups = [groups]
    else:
        loc_groups = groups

    # calculate the difference
    for bin_ind in range(len(loc_groups)):

        # set categories
        if categories is None:
            categories = groups[bin_ind].keys()

        for categ in categories:
            value = [lum - mem for lum, mem \
                         in zip(groups[bin_ind][categ].lumen_density, 
                                groups[bin_ind][categ].membrane_density)]
            setattr(groups[bin_ind][categ], name, value)

    # set title and y axis label
    if title is None:
        title='Analysis of vesicle density'
    if y_label is None:
        y_label = 'Difference between lumen and membrane densities'

    # analyze
    stats = analyze_item(groups=groups, name=name, reference=reference,
                         categories=categories, reference_bin=reference_bin,
                         out=out, bins=bins, bin_names=bin_names, format=format,
                         plot_=plot_, category_color=category_color, 
                         bar_width=bar_width, font_size=font_size, title=title,
                         bin_label=bin_label, y_label=y_label,
                         plot_confidence=plot_confidence)

    return stats

###############################################################
#
# Vesicle clustering
#

def cluster_histogram(clust, bins, reference, categories=None, bin_names=None,
                      out=None, plot_=True, bar_width=None, category_color=None, 
                      font_size=None, plot_confidence='stars',
                      title=None, y_label=None):
    """
    """
    
    # get categories
    if categories is None:
        categories = clust.keys()

    # make sure number of boundaries are up-to date
    clust.findNItems(mode='in_clust')
    clust.findNItems(mode='in_obs')

    # split according to bins
    clust_split = clust.split(value=bins, name='n_bound_clust', 
                              categories=categories)

    # make object stats to hold the histogram
    stats = pyto.analysis.Groups()
    stats['together'] = pyto.analysis.Observations()
    for categ in categories:
        stats[categ] = pyto.analysis.Observations()

        # for each category separately
        histo = [sum(nb.sum() for nb in clust_bin[categ].n_bound_clust) \
                     for clust_bin in clust_split]
        stats[categ].histo = numpy.array(histo)

        # for all categories together
        try:
            stats['together'].histo += stats[categ].histo 
        except AttributeError:
            stats['together'].histo = numpy.array(histo)

    # do stats
    histogram_test(stats=stats, reference=reference, categories=categories)

    # make object stats_split to hold data for output
    stats_split = []
    for clust_bin, bin_ind in zip(clust_split, range(len(clust_split))):
        stats_bin = deepcopy(stats)

        # for each category separately
        for categ in categories:

            # assign attributes value, n and fraction
            stats_bin[categ].value = \
                sum(nb.sum() for nb in clust_bin[categ].n_bound_clust)
            stats_bin[categ].n = sum(nb for nb in clust_bin[categ].n_bound_obs)
            stats_bin[categ].fraction = \
                stats_bin[categ].value / float(stats_bin[categ].n)

        # for all cateories together
        stats_bin['together'].value = \
            sum(stats_bin[categ].value for categ in categories)
        stats_bin['together'].n = sum(stats_bin[categ].n for categ in categories)
        stats_bin['together'].fraction = \
                stats_bin['together'].value / float(stats_bin['together'].n)

        # add current stats_bin
        stats_split.append(stats_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    if title is None:
        title = 'SV clusters'
    out.write('\n' + title + '\n')
        
    # print 
    var_names = ['n', 'value', 'fraction', 'chi_square', 'confid']
    print_stats(stats=stats_split, categories=categories, out=out, bins=bins, 
                bin_names=bin_names, var_names=var_names)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        if y_label is None:
            y_label = 'Fraction of svs'
        plt.ylabel(y_label)
        plt.xlabel('Cluster size')

        # plot fraction connected
        plot_stats(stats=stats_split, name='fraction', categories=categories, 
                   bar_width=bar_width, category_color=category_color, bins=bins,
                   bin_names=bin_names, font_size=font_size, 
                   confidence=plot_confidence)

        # show plot
        plt.show()

    return stats_split

def analyze_cluster_size(groups, reference, categories=None, reference_bin=None, 
        test='t', out=None, bins=None, bin_names=None, format=None,
        plot_=False, category_color=None, bar_width=None, font_size=None, 
        plot_confidence='stars', title=None, bin_label=None, y_label=None):
    """
    Analyzes vesicle cluster size
    """

    # name of the attribute
    name = 'n_bound_clust'

    # check if one or more groups
    if isinstance(groups, pyto.analysis.Groups):
        loc_groups = [groups]
    else:
        loc_groups = groups

    # set title and y axis label
    if title is None:
        title='Analysis of vesicle cluster sizes'
    if y_label is None:
        y_label = 'Mean cluster size'

    # analyze
    stats = analyze_item(groups=groups, name=name, reference=reference,
                  categories=categories, reference_bin=reference_bin,
                  test=test, out=out, bins=bins, bin_names=bin_names, format=format,
                  plot_=plot_, category_color=category_color, 
                  bar_width=bar_width, font_size=font_size, title=title,
                  bin_label=bin_label, y_label=y_label, 
                  plot_confidence=plot_confidence)

    return stats

def analyze_cluster_size_per_sv(groups, reference, categories=None, test='t', 
        reference_bin=None, out=None, bins=None, bin_names=None, format=None,
        plot_=False, category_color=None, bar_width=None, font_size=None, 
        plot_confidence='stars', title=None, bin_label=None, y_label=None):
    """
    Analyzes vesicle cluster size
    """

    # name of the attribute
    name = 'cluster_size'

    # check if one or more groups
    if isinstance(groups, pyto.analysis.Groups):
        loc_groups = [groups]
    else:
        loc_groups = groups

    # set title and y axis label
    if title is None:
        title='Analysis of cluster size for each vesicle'
    if y_label is None:
        y_label = 'Mean of the cluster sizes for all vesicles'

    # analyze
    stats = analyze_item(groups=groups, name=name, reference=reference, test=test,
                         categories=categories, reference_bin=reference_bin,
                         out=out, bins=bins, bin_names=bin_names, format=format,
                         plot_=plot_, category_color=category_color, 
                         bar_width=bar_width, font_size=font_size, title=title,
                         bin_label=bin_label, y_label=y_label,
                         plot_confidence=plot_confidence)

    return stats

###############################################################
#
# Active zone
#

def hi_cluster_sv(sv, clust, reference, method='average', categories=None, 
        reference_bin=None, test='t', out=None, plot_=False, category_color=None, 
        bar_width=None, font_size=None, title='Herarchical sv clustering', 
        plot_confidence='stars', y_label='Cophenetic coefficient'):
    """
    Hierarchical clustering of sv's that are a subset of those used in cluster. 
    """

    # cluster and get cophenetic coefficient
    sv.cluster(clusters=clust, categories=categories, method=method)

    # do stats on cophenetic coef
    stats = analyze_item(groups=sv, name='hi_cophen', indexed=False, 
         reference=reference, categories=categories, reference_bin=reference_bin, 
         test=test, out=out, plot_=plot_, category_color=category_color, 
         bar_width=bar_width, font_size=font_size, title=title, y_label=y_label,
         plot_confidence=plot_confidence)
         
    return stats

###############################################################
#
# SV layers
#

def plot_sv_occupancy(layer, bins=None, pixel_size=None, categories=None, mean=True,
                      title='SV occupancy by layers: ', x_label=None, 
                      y_label='Fraction of volume occupied by svs'):
    """
    Plots sv occupancy per layer vs. distance to the AZ for each observation separately.
    Different categories are plotted on different figures, while all observations of 
    one categories are plotted on the same figure.

    If mean is True also the mean of all observations (of one category) is plotted.
    """

    # bin layer data in fine bins (just to be able to average, if needed)
    if bins is not None:
        layer = layer.rebin(bins=bins, pixel=pixel_size)

    # set categories
    if categories is None:
        categories = groups.keys()

    for categ in categories:

        # start plot
        plt.figure()

        # plot data form all specified observations
        lines = plot_data(groups=layer, x_name='distance_nm', y_name='occupancy', 
                          mean=mean, categories=categ)

        # finish plot
        plt.title(title + categ)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xlim(xmin=min(bins), xmax=max(bins)*1.25)
        plt.legend()
        plt.show()

def analyze_sv_occupancy(layer, bins, pixel_size, reference, reference_bin,  
        test='t', categories=None, out=None, plot_=False, category_color=None, 
        bar_width=None, font_size=None, bin_label='Distance to the AZ [nm]', 
        title='SV by layers', y_label='Fraction of volume occupied by svs',
        plot_confidence='stars'):
    """
    Statistical analysis of sv occupancy divided in bins according to the distance
    to the AZ.
    """

    # rebin data in standard bins
    layer = layer.rebin(bins=bins, pixel=pixel_size)
    
    # make bins separate instances
    layer_bins = layer.splitIndexed()

    # analyze
    stats = analyze_item(groups=layer_bins, name='occupancy', reference=reference,
        test=test, categories=categories, reference_bin=reference_bin, out=out, 
        bins=bins, plot_=plot_, category_color=category_color, bar_width=bar_width, 
        font_size=font_size, title=title, bin_label=bin_label, y_label=y_label,
        plot_confidence=plot_confidence)

    return stats

###############################################################
#
# Split vesicle observations
#

def split(sv, categories, name, bins, conn=None):
    """
    Splits observations of vesicles (arg sv) according to the property (arg 
    name) and arg bins. The new (split) pieces are assigned as separate 
    categories to sv.

    If connectors (arg conn) are specified, splits them also according to 
    new vesicle categories and updates conn.

    In all cases the categories before splitting are retained, and the new
    ones are added.

    Modifies args sv and conn.

    Arguments:
      - sv: (Vesicles) vesicles group to be split
      - categories: {categ_name, [new_name_1, new_name_2, ...]}
      - name: property name
      - bins: bin values, has to have the same length as values of categories 
      - conn: (Connectors) conectors to be split according to 
    """

    for categ in categories:

        # split svs
        sv_pieces = sv[categ].split(name=name, bins=bins)

        # make new categories
        for one_sv_piece, new_name in zip(sv_pieces, categories[categ]):

            # assign new sv categories
            sv[new_name] = one_sv_piece

            # assign connectors
            if conn is not None:
                conn[new_name] = deepcopy(conn[categ])
                conn.update(conn.extractByVesicles(
                        vesicles=sv, categories=[new_name], other=False))


###############################################################
#
# General analysis functions
#

def analyze_item(groups, name, reference, categories=None, reference_bin=None, 
        test='t', indexed=True, out=None, bins=None, bin_names=None, format=None,
        plot_=False, category_color=None, bar_width=None, font_size=None, 
        y_error='sem', plot_confidence='stars', title=None, 
        bin_label=None, y_label=None):
    """
    Analyzes property given by (arg) name between categories and between bins. 
    The property has to have an array of values (one for each item) for each 
    observation.

    The analysis includes calculation of mean, std, t-test between categories and
    between bins. Mean values are plotted.
    """

    # set title
    if title is None:
        title = 'Analysis of ' + name

    # set categories
    if categories is None:
        if isinstance(groups, pyto.analysis.Groups):
            categories = groups.keys()
        else: 
            categories = groups[0].keys()

    # calculate stats
    stats = property_stats(groups=groups, name=name, reference=reference, 
                  test=test, indexed=indexed, categories=categories, 
                  reference_bin=reference_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    out.write('\n' + title + '\n')
        
    # print stats
    foo, test_name = define_test(test=test)
    test_name_bin = test_name + '_bin'
    if reference_bin is None:
        var_names=['n', 'mean', 'std', 'sem', test_name, 'confid']
    else:
        var_names=['n', 'mean', 'std', 'sem', test_name, 
                   'confid', test_name_bin, 'confid_bin']
    print_stats(stats=stats, categories=categories, out=out, bins=bins,
                bin_names=bin_names, var_names=var_names, format=format)

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        if y_label is None:
            y_label = 'Mean'
        plt.ylabel(y_label)
        if bin_label is None:
            bin_label = ''
        plt.xlabel(bin_label)

        # plot data
        plot_stats(stats=stats, name='mean', categories=categories, 
                   bins=bins, bin_names=bin_names, bar_width=bar_width, 
                   category_color=category_color, font_size=font_size,
                   y_error=y_error, confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats   

def analyze_obs_rel(groups, name, test, reference_bin, categories=None, out=None,
                bins=None, bin_names=None,  plot_=True, bar_width=None,  
                format=None, category_color=None, font_size=None, title=None, 
                plot_confidence='stars', y_label=None):
    """
    Ananlyzes property given by (arg) name between bins. The property has to have 
    a single value for each observation.

    Each bin has to have the same observations (categories and identifiers). 
    Values of corresponding properties from defferent bins are compared.

    Arguments:
      - groups: list of Groups objects
    """

    # calculates and sets mean_obs attribute
    stats = property_stats(groups=groups, name=name, categories=categories, 
                        reference=None, reference_bin=reference_bin)

    # calculate relative differences 
    find_diff_bin(stats=stats, name='mean_obs', reference_bin=reference_bin, 
                      categories=categories)

    # statistics between bins
    do_stats_bin(stats=stats, name='mean_obs', mode=test,  categories=categories,
                 reference_bin=reference_bin)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    if title is None:
        title = 'Analysis of mean observation values of ' + name 
    out.write('\n' + title + '\n')
        
    # print stats
    var_names = ['n', 'mean', 'diff_bin_mean', 't_bin', 'confid_bin'] 
    print_stats(stats=stats, categories=categories, out=out, bins=bins, 
                bin_names=bin_names, var_names=var_names, format=format,
                confidence=plot_confidence)


    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        if y_label is None:
            y_label = ('Mean of differences between observations')
        plt.ylabel(y_label)

        # plot data
        plot_stats(stats=stats, name='diff_bin_mean', categories=categories, 
                   bins=bins, bar_width=bar_width, bin_names=bin_names,
                   category_color=category_color, font_size=font_size)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats

def analyze_histogram(groups, reference, name=None, bins=None, categories=None, 
                      bin_names=None, out=None, plot_=True, bar_width=None, 
                      category_color=None, font_size=None, x_label=None, 
                      plot_confidence='stars', title=None):
    """
    Makes a histogram of all values of property given by arg name according to 
    arg bins.

    Statistics is done on histogram values, but fractions of total are plotted.

    If name and bins are none groups have to be a list of Groups objects. In this
    case number of indexed elements in each Groups object is used to make a 
    histogram.

    Arguments:
      - groups: (pyto.analysis.Groups)
    """
    
    # calcuate histogram
    if (name is not None) and (bins is not None):
        stats = property_histogram(groups=groups, name=name, reference=reference, 
                                   bins=bins, categories=categories)
        n_bins = len(bins) - 1
    else:
        stats = n_histogram_bin(groups=groups, reference=reference, 
                                categories=categories, together=True)
        n_bins = len(groups)

    # convert to bins
    stats_bin = []
    for bin_ind in range(n_bins):
        curr = deepcopy(stats)
        for categ in curr:
            curr[categ].value = stats[categ].histo[bin_ind]
            curr[categ].fraction = stats[categ].histo_fractions[bin_ind]
        stats_bin.append(curr)

    # set text output 
    if out is None:
        out = sys.stdout
    elif isinstance(out, str):
        out = open(out)
    if name is None:
        name = 'Number of Elements'
    if title is None:
        title = 'Histogram of ' + name
    out.write('\n' + title + '\n')
        
    # print stats
    print_stats(stats=stats_bin, categories=categories, out=out, bins=bins, 
                bin_names=bin_names,
                var_names=['n', 'value', 'fraction', 'chi_square', 'confid'])

    # plot
    if plot_:

        # start plot
        plt.figure()
        plt.title(title)
        plt.ylabel('Fraction of total number')
        if x_label is not None:
            plt.xlabel(x_label)

        # plot data
        plot_stats(stats=stats_bin, name='fraction', categories=categories, 
                   bar_width=bar_width, bins=bins, bin_names=bin_names,
                   category_color=category_color, font_size=font_size,
                   confidence=plot_confidence)

        # show plot
        plt.show()

    # return in the same form as argument conn
    return stats     

def correlate(groups, name_x, name_y, categories=None, plot_=True, title=None, 
              x_label=None, y_label=None):
    """
    Arguments:
      - groups: (pyto.analysis.Gruops)
    """

    # set 
    if title is None:
        title = ''
    if x_label is None:
        x_label = name_x
    if y_label is None:
        y_label = name_y

    # calculate correlation
    stats = property_correlation(groups=groups, name_x=name_x, name_y=name_y,
                                 categories=categories)

    # plot
    if plot_:

        # set categories
        if categories is None:
            categories = stats.keys()

        for categ in categories:

            # start plot
            plt.figure()
            curr_title = title + categ
            plt.title(categ)
            plt.xlabel(x_label)
            plt.ylabel(y_label)

            # plot data
            for x, y, ident in zip(stats[categ].x, stats[categ].y, 
                                   stats[categ].identifiers):
                plt.plot(x, y, 'o', label=ident) 

            # show plot
            plt.legend()
            plt.show()
    
    return stats

###############################################################
#
# Common functions 
#
# ToDo: move to Groups
#

def property_stats(groups, name, reference, indexed=True, test='t', 
                   categories=None, reference_bin=None):
    """
    """

    # check if one or more bins
    if isinstance(groups, pyto.analysis.Groups):
        groups = [groups]
        one_bin = True
    else:
        one_bin = False

    # calculate stats for each bin and category 
    results = []
    for curr_groups in groups:
        
        # get categories
        if categories is None:
            categories = curr_groups.keys()

        # make object to hold results
        results_bin = pyto.analysis.Groups()

        # initialize
        variable = {}
        together = []

        # organize data and calculate mean and std for each category
        for categ in categories:
            results_bin[categ] = pyto.analysis.Observations()
            results_bin[categ].identifiers = copy(curr_groups[categ].identifiers)
            var_data = getattr(curr_groups[categ], name)

            # individual observations
            if indexed:
                results_bin[categ].n_obs = []
                results_bin[categ].mean_obs = []
                results_bin[categ].std_obs = []
                results_bin[categ].sem_obs = []
                for var in var_data:
                    results_bin[categ].n_obs.append(len(var))
                    results_bin[categ].mean_obs.append(var.mean())
                    results_bin[categ].std_obs.append(var.std(ddof=1))
                    results_bin[categ].sem_obs.append(var.std(ddof=1)\
                                                          / numpy.sqrt(len(var)))

            # all observations together
            variable[categ] = numpy.asarray(pyto.util.nested.flatten(var_data))
            results_bin[categ].data = variable[categ]
            results_bin[categ].n = len(variable[categ])
            results_bin[categ].mean = variable[categ].mean()
            results_bin[categ].std = variable[categ].std()
            results_bin[categ].sem = \
                results_bin[categ].std / numpy.sqrt(results_bin[categ].n)

        # mean, std and sem for all categories together
        for categ in categories:
            together.extend(variable[categ])
        together = numpy.asarray(together)
        results_bin['together'] = pyto.analysis.Observations()
        results_bin['together'].data = together
        results_bin['together'].n = len(together)
        results_bin['together'].mean = together.mean()
        results_bin['together'].std = together.std()
        results_bin['together'].sem = \
            results_bin['together'].std / numpy.sqrt(results_bin['together'].n) 

        # test between categores 
        if reference is not None:
            categs = itertools.chain(categories, ['together'])
            stats_test(groups=results_bin, test=test, categories=categs, 
                       reference=reference, name='data')

        # add to results
        results.append(results_bin)

    # put results in the same form as argument groups
    if one_bin:
        results = results[0]

    # test between bins
    if reference_bin is not None:
        stats_test_bin(groups=results, test=test, categories=categories, 
                       reference_bin=reference_bin, name='data')
        
    return results

def property_histogram(groups, name, reference, bins, categories=None, 
                       reference_bin=None):
    """
    """
    
    # check if one or more bins
    if isinstance(groups, pyto.analysis.Groups):
        groups = [groups]
        one_bin = True
    else:
        one_bin = False
                               
    # loop over bins
    results = []
    for curr_groups, bin_ind in zip(groups, range(len(groups))):
        
        # get categories
        if categories is None:
            categories = curr_groups.keys()

        # make histograms for each category 
        results_bin = property_histogram_core(groups=curr_groups, name=name,
                                              bins=bins, categories=categories)

        # add to results
        results.append(results_bin)

    # chi-square tests between categories and between bins
    histogram_test(stats=results, reference=reference, 
                   reference_bin=reference_bin, categories=categories)

    # return
    if one_bin:
        return results[0]
    else:
        return results

def property_histogram_core(groups, name, bins, categories, together=True):
    """
    Makes histogram of the values of variable given by (arg) name according to
    the bin limits specified in arg bins for each category (given in arg 
    categories) of the group.

    Calculates histograms for all categories togeteher if arg together is True.

    Arguments:
      - groups: pyto.analysis.Groups object

    Returns Groups object with the same structure as arg groups that have 
    properties histo, n, histo_obs and n_obs.
    """

    # make object to hold results
    results = pyto.analysis.Groups()

    # initialize
    variable = {}
    histo = {}

    # make histogram for each category
    for categ in categories:
        results[categ] = pyto.analysis.Observations()
        results[categ].identifiers = copy(groups[categ].identifiers)
        var_data = getattr(groups[categ], name)

        # individual observations
        results[categ].n_obs = []
        results[categ].histo_obs = []
        results[categ].histo_fractions_obs = []
        for var in var_data:
            his, foo = numpy.histogram(var, bins=bins)
            results[categ].n_obs.append(len(var))
            results[categ].histo_obs.append(his)
            results[categ].histo_fractions_obs.append(his/float(len(var)))

        # all observations together
        variable[categ] = numpy.asarray(pyto.util.nested.flatten(var_data))
        histo[categ], same_bins = numpy.histogram(variable[categ], bins=bins)
        results[categ].n = len(variable[categ])
        results[categ].histo = histo[categ]
        results[categ].histo_fractions = \
            histo[categ] / float(len(variable[categ]))

    # make histogram for all categories together
    if together:
        results['together'] = pyto.analysis.Observations()
        results['together'].histo = numpy.zeros(len(bins) - 1)
        results['together'].n = 0
        for categ in categories:
            results['together'].histo += results[categ].histo
            results['together'].n += results[categ].n
        results['together'].histo_fractions = \
                results['together'].histo / float(results['together'].n)

    return results

def n_histogram_bin(groups, reference, categories=None, together=True):
    """
    Calculates fraction of total among bins
    """

    # set histograms for each category
    results = pyto.analysis.Groups()
    for curr_groups, bin_ind in zip(groups, range(len(groups))):
        
        # get categories
        if categories is None:
            categories = curr_groups.keys()

        for categ in categories:
            if results.get(categ, None) is None:
                results[categ] = pyto.analysis.Observations()

            data = getattr(curr_groups[categ], curr_groups[categ].index)
            flat_data = pyto.util.nested.flatten(data)
            try:
                results[categ].histo.append(len(flat_data))
            except AttributeError:
                results[categ].histo = [len(flat_data)]

    # set histograms for all categories together
    results['together'] = pyto.analysis.Observations()
    if categories is None:
        categories = results.keys()
    for categ in categories:
        try:
            results['together'].histo += numpy.asarray(results[categ].histo)
        except AttributeError:
            results['together'].histo = numpy.asarray(results[categ].histo)
        results['together'].histo = results['together'].histo.tolist()

    # set histogram total and fractions
    for categ in results.keys():
        results[categ].n = sum(results[categ].histo)
        results[categ].histo_fractions = [hi / float(results[categ].n) \
                                              for hi in results[categ].histo]

    # stats
    histogram_test(stats=results, reference=reference, categories=categories)

    return results

def histogram_test(stats, reference=None, reference_bin=None, categories=None):
    """
    Does chi-square tests between categoreis and between bins.

    Calculated values are saved as properties of stats: chi_square,
    confid, chi_sq_bin and confid_bin.
    """

    if isinstance(stats, (list, tuple)):
        stats_loc = stats
    else:
        stats_loc = [stats]

    # chi-square test between categories within the current bin
    if reference is not None:
        for stats_bin in stats_loc:

            for categ in itertools.chain(categories, ['together']):
                stats_bin[categ].chi_square, stats_bin[categ].confid = \
                    pyto.util.scipy_plus.chisquare_2(stats_bin[categ].histo, 
                                                     stats_bin[reference].histo)

    # chi-square between bins
    if reference_bin is not None:
        for bin_index in range(len(stats_loc)):
        
            for categ, ref in zip(stats_loc[bin_index].values(), 
                                  stats_loc[reference_bin].values()):
                categ.chi_sq_bin, categ.confid_bin = \
                    pyto.util.scipy_plus.chisquare_2(categ.histo, ref.histo)

def property_correlation(groups, name_x, name_y, categories=None):
    """
    """

    # check if one or more bins
    if isinstance(groups, pyto.analysis.Groups):
        groups = [groups]
        one_bin = True
    else:
        one_bin = False

    # calculate correlation for each bin and category 
    results = []
    for curr_groups in groups:
        
        # get categories
        if categories is None:
            categories = curr_groups.keys()

        # make object to hold results
        results_bin = pyto.analysis.Groups()

        # calculate correlation
        for categ in categories:
            results_bin[categ] = pyto.analysis.Observations()

            # get variables
            var_x = getattr(curr_groups[categ], name_x)
            var_y = getattr(curr_groups[categ], name_y)

            # set attributes
            results_bin[categ].x = var_x
            results_bin[categ].y = var_y
            results_bin[categ].identifiers = copy(curr_groups[categ].identifiers)

            # calculate correlation for each observation
            pear_res = [scipy.stats.pearsonr(x, y) for x, y in zip(var_x, var_y)] 
            results_bin[categ].pearson_r_obs = \
                [pear_obs[0] for pear_obs in pear_res]
            results_bin[categ].confid_obs = [pear_obs[1] for pear_obs in pear_res]
            
            # calculate correlation for all observations together
            var_x_all = numpy.asarray(pyto.util.nested.flatten(var_x))
            var_y_all = numpy.asarray(pyto.util.nested.flatten(var_y))
            results_bin[categ].pearson_r, results_bin[categ].confid = \
                scipy.stats.pearsonr(var_x_all, var_y_all)
                                      
        # add to results
        results.append(results_bin)

        # return in the same form as arg groups
        if one_bin:
            return results[0]
        else:
            return results

def find_diff_bin(stats, name, reference_bin, categories=None):
    """
    Calculates difference between each observation and the corresponding 
    observationfrom the reference bin.

    Sets attributes to stats[bin][category]:
      - diff_bin: difference for each observation
      - diff_bin_mean: mean of diff_bin
    """

    #
    for bin_ind in range(len(stats)):

        # get categories
        if categories is None:
            categories = stats[bin_ind].keys()

        # each category separately
        var_together = numpy.array([])
        ref_var_together = numpy.array([])
        for categ in categories:

            if categ == 'together':
                continue

            # prepare variables
            var = getattr(stats[bin_ind][categ], name)
            var = numpy.asarray(var)
            var_together = numpy.append(var, var_together)
            ref_var = getattr(stats[reference_bin][categ], name)
            ref_var = numpy.asarray(ref_var, dtype='float')
            ref_var_together = numpy.append(ref_var, ref_var_together)

            # calculate relative difference between bins for each observation
            stats[bin_ind][categ].diff_bin = var - ref_var
            
            # mean relative difference between bins
            clean = numpy.extract(~numpy.isnan(stats[bin_ind][categ].diff_bin), 
                                   stats[bin_ind][categ].diff_bin)
            stats[bin_ind][categ].diff_bin_mean = clean.mean()

        # all categories together 
        stats[bin_ind]['together'].diff_bin = var_together - ref_var_together
        
        # mean relative difference between bins
        clean = numpy.extract(~numpy.isnan(stats[bin_ind]['together'].diff_bin), 
                               stats[bin_ind]['together'].diff_bin)
        stats[bin_ind]['together'].diff_bin_mean = clean.mean()

def do_stats_bin(stats, name, mode, reference_bin, categories=None):
    """
    Calculates statistics of variable given by arg name between bins according
    to the arg mode. This variable has to have a single value for each observation.

    Redefines attribute n to be the number of observations for which the value
    (definde above) exist for both bin in question and the reference bin.

    The following modes are defined:
      - 't-paired': t-test between matched pairs (uses scipy.stats.ttest_rel)

    Sets attributes to stats[bin][config]:
      - t_bin
      - confid_bin
      - n: number of observations where bins can be compared (redefined)
    """

    # set mode
    if mode == 't-paired':
        stat_fun = scipy.stats.ttest_rel
    else:
        raise ValueError("Mode " + mode + " is not understood. Currently " +
                         "implemented modes are 't-paired' and .")

    # calculate
    for bin_ind in range(len(stats)):

        # get categories
        if categories is None:
            categories = stats[bin_ind].keys()

        # for each category separately
        var_together = numpy.array([])
        ref_var_together = numpy.array([])
        for categ in categories:

            if categ == 'together':
                continue

            # prepare variables
            var = getattr(stats[bin_ind][categ], name)
            var = numpy.asarray(var)
            var_together = numpy.append(var, var_together)
            ref_var = getattr(stats[reference_bin][categ], name)
            ref_var = numpy.asarray(ref_var)
            ref_var_together = numpy.append(ref_var, ref_var_together)

            # remove observations that contain no data 
            var_clean = [x for x, ref_x in zip(var, ref_var) \
                             if (not numpy.isnan(x)) and (not  numpy.isnan(ref_x))] 
            ref_var_clean = \
                [ref_x for x, ref_x in zip(var, ref_var) \
                     if (not numpy.isnan(x)) and (not  numpy.isnan(ref_x))] 

            # set number of observations
            stats[bin_ind][categ].n = len(var_clean)

            # do stats
            stats[bin_ind][categ].t_bin, stats[bin_ind][categ].confid_bin = \
                stat_fun(var_clean, ref_var_clean)
            
        # remove observations that contain no data from category together
        var_together_clean = \
            [x for x, ref_x in zip(var_together, ref_var_together) \
                 if (not numpy.isnan(x)) and (not  numpy.isnan(ref_x))] 
        ref_var_together_clean = \
            [ref_x for x, ref_x in zip(var_together, ref_var_together) \
                 if (not numpy.isnan(x)) and (not  numpy.isnan(ref_x))] 

        # set number of observations
        stats[bin_ind]['together'].n = len(var_together_clean)

        # for all categories together
        stats[bin_ind]['together'].t_bin, \
             stats[bin_ind]['together'].confid_bin = \
             stat_fun(var_together_clean, ref_var_together_clean)

def stats_test(groups, categories, test, reference, name='data'):
    """
    Preforms a statistical test on samples defined for each category for one
    Groups instance.

    Arguments:
      - groups: (Groups)
    """

    # set test method
    test_method, test_value_name = define_test(test=test)

    # test 
    ref_data = getattr(groups[reference], name)
    for categ in categories:
        data = getattr(groups[categ], name)

        # test current observations
        if (len(data) > 0) and (len(ref_data) > 0):
            test_value, confid = test_method(data, ref_data)
        else:
            test_value = numpy.NaN
            confid = numpy.NaN 

        # assign variables
        setattr(groups[categ], test_value_name, test_value)
        groups[categ].confid = confid

def stats_test_bin(groups, categories, test, reference_bin, name='data'):
    """
    Preforms a statistical test on samples defined for each category for a list of
    Groups instances.

    Arguments:
      - groups: (list of Groups)
    """

    # set test method
    test_method, test_value_name = define_test(test=test)
    test_value_name += '_bin'
    print

    # test 
    for bin_index in range(len(groups)):
        for categ in itertools.chain(categories, ['together']):

            # get data
            data = getattr(groups[bin_index][categ], name)
            data = numpy.array(pyto.util.nested.flatten(data))
            ref_data = getattr(groups[reference_bin][categ], name)
            ref_data = numpy.array(pyto.util.nested.flatten(ref_data))

            # test current observations
            if (len(data) > 0) and (len(ref_data) > 0):
                try:
                    test_value, confid = test_method(data, ref_data)
                except ValueError:
                    # deals with Kruskal
                    if (data == ref_data).all():
                        test_value = 0.
                        confid = 1.
            else:
                test_value = numpy.NaN
                confid = numpy.NaN 

            # assign variables
            setattr(groups[bin_index][categ], test_value_name, test_value)
            groups[bin_index][categ].confid_bin = confid

def define_test(test):
    """
    Returns test method and test value name
    """

    if (test == 't') or (test == 't_ind'):
        method = scipy.stats.ttest_ind
        value_name = 't'
    elif (test == 'kruskal') or (test == 'kruskal-wallis') or (test == 'h'):
        method = scipy.stats.kruskal
        value_name = 'h'
    elif (test == 'mannwhitneyu') or (test == 'u'):
        method = scipy.stats.mannwhitneyu 
        value_name = 'u'
    else:
        raise ValueError('Test ' + str(test) + " not understood. Defined tests "\
                             + "are: 't_ind', 'kruskal' and 'mannwhitneyu'.")

    return method, value_name
        
def print_stats(stats, out, var_names, categories=None, bin_names=None, bins=None,
                format=None):
    """
    """

    # check if one or more Groups
    if isinstance(stats, pyto.analysis.Groups):
        stats = [stats]

    # set bin_names
    if bin_names is None:
        if bins == None:
            bin_names = ['        '] * len(stats)
        else:
            bin_names = ['%3d-%3d ' % (low, high) \
                             for low, high in zip(bins[:-1], bins[1:])]

    # print table head
    var_head = ('%9s ' * len(var_names)) % tuple(var_names)
    out.write(' bin      category' + var_head + '\n')

    # make format string
    loc_format = {
        'mean' : '    %5.2f ',
        'std' : '    %5.2f ',
        'sem' : '    %5.2f ',
        'n' : '    %5d ',
        'value' : '    %5d ',
        'fraction' : '    %5.2f ',
        't_value' : '    %5.2f ',
        't' : '    %5.2f ',
        'h' : '    %5.2f ',
        'u' : '    %5.2f ',
        't_bin_value' : '    %5.2f ',
        't_bin' : '    %5.2f ',
        'chi_square' : '    %5.2f ',
        'chi_sq_bin' : '    %5.2f ',
        'confid' : '   %7.4f',
        'confid_bin' : '   %7.4f'
        }
    if format is not None:
        loc_format.update(format)
    var_format = ''.join([loc_format.get(name, '   %5.2f  ') \
                              for name in var_names])
    format = ' %8s %8s' + var_format + '\n'
    together_format = \
        ''.join([loc_format.get(name, '   %5.2f  ') for name in var_names \
                     if name not in ['t_value', 'chi_square', 'confid', 't', 'h', 
                                     'u','t_bin', 'h_bin', 'u_bin', 'confid_bin']])
    together_format = ' %8s %8s' + together_format + '\n'

    # print data
    for bin_ind in range(len(bin_names)):

        # set categories
        if categories is None:
            categories_plus = list(stats[bin_ind])
        elif ('together' in stats[bin_ind]) and ('together' not in categories):
            categories_plus = itertools.chain(categories, ['together'])
        else:
            categories_plus = categories

        # separate categories
        for categ in categories_plus:
            variables = [getattr(stats[bin_ind][categ], name) \
                             for name in var_names]
            variables = [bin_names[bin_ind], categ] + variables
            out.write(format % tuple(variables))
                         
def plot_stats(stats, name, bar_width, category_color, categories=None, 
               bin_names=None, bins=None, y_error=None, confidence='stars', 
               font_size=None):
    """
    """

    # check if one or more Groups
    if isinstance(stats, pyto.analysis.Groups):
        stats = [stats]

    # set bin_names
    if bin_names is None:
        if bins == None:
            bin_names = ['        '] * len(stats)
        else:
            bin_names = ['%3d-%3d ' % (low, high) \
                             for low, high in zip(bins[:-1], bins[1:])]


    # find range of y-axis values
    min_y = numpy.nanmin([stats_bin.min(name=name) for stats_bin in stats])
    min_y = numpy.nan_to_num(min_y)
    max_y = numpy.nanmax([stats_bin.max(name=name) for stats_bin in stats])
    max_y = numpy.nan_to_num(max_y)
    range_y = max_y - min(min_y, 0)

    # plot data for all bins and categories
    for stats_bin, bin_ind in zip(stats, range(len(stats))):

        # set categories
        if categories is None:
            categories = list(stats_bin)

        # plot each category
        for categ, categ_ind in zip(categories, range(len(categories))):

            # adjust alpha and bars
            try:
                alpha = category_alpha.get(categ, category_alpha_default)
            except NameError:
                alpha = category_alpha_default
            if y_error is not None:
                if alpha == 1:
                    yerr = getattr(stats_bin[categ], y_error)
                else:
                    yerr = None
            else:
                yerr = None

            # plot bar
            color = category_color.get(categ, category_color_default)
            bar = plt.bar(left=bin_ind+categ_ind*bar_width, 
                          height=getattr(stats_bin[categ], name), yerr=yerr,
                          width=bar_width, label=category_label.get(categ), 
                          color=color, alpha=alpha, ecolor=color)[0]

            if not confidence:
                continue

            if yerr is None: 
                yerr = 0

            # confidence between categories
            if confidence is not None:
                try:
                    confid_num = stats_bin[categ].confid
                    if confidence == 'stars':
                        confid = '*' * get_stars(confid_num)
                        f_size = 1.5 * font_size
                    else:
                        confid = '%5.3f' % confid_num
                        f_size = font_size
                    if not numpy.isnan(confid_num):        
                        color = category_color.get(
                            categ, category_color_default)
                        plt.text(bar.get_x()+bar_width/2, 
                                 0.02*range_y + max(bar.get_height() + yerr, 0),
                                 confid, ha='center', va='bottom', size=f_size,
                                 color=color)
                except AttributeError:
                    pass

            # confidence between bins
            if confidence is not None:
                try:
                    confid_bin_num = stats_bin[categ].confid_bin
                    if confidence == 'stars':
                        confid_bin = '*' * get_stars(confid_bin_num)
                        f_size = 1.5 * font_size
                    else:
                        confid_bin = '%5.3f' % confid_bin_num
                        f_size = font_size
                    if not numpy.isnan(confid_bin_num):
                        plt.text(bar.get_x()+bar_width/2, 
                                 0.04*range_y + max(bar.get_height() + yerr, 0),
                                 confid_bin, ha='center', va='bottom', 
                                 size=f_size, weight='black')
                except AttributeError:
                    pass

        # max y-axis value for this bin
        max_y_bin = stats_bin.max(name=name, categories=categories)
        if y_error is not None:
            max_y_bin += stats_bin.max(name=y_error, categories=categories)

        # confidence of all treatments together between bins
        if confidence is not None:
            try:
                if confidence == 'stars':
                    tog_confid_bin = '*' * get_stars(stats_bin['together'].confid_bin)
                    if len(tog_confid_bin) > 0:
                        tog_confid_bin = '--' + tog_confid_bin + '--'
                    f_size = 1.5 * font_size
                else:
                    tog_confid_bin = '--%5.3f--' % stats_bin[categ].confid_bin
                    f_size = font_size
                plt.text(bin_ind + categ_ind*bar_width/2., 
                         0.06*range_y + max(max_y_bin, 0),  
                         tog_confid_bin, ha='center', va='bottom', size=f_size, 
                         weight='black')
            except AttributeError:
                pass

    # finish plot
    axis_limits = list(plt.axis())
    if name == 'fraction':
        plt.axis([axis_limits[0]-bar_width, max(axis_limits[1], 4), 0., 1.])
    else:
        plt.axis([axis_limits[0]-bar_width, max(axis_limits[1], 4), 
                  axis_limits[2], axis_limits[3]])
    n_bins = len(bin_names)
    n_categ = len(stats_bin)
    plt.xticks(numpy.arange(n_bins)+bar_width*n_categ/2, bin_names)

def get_stars(confid):
    """
    Returns number of stars associated with (each of) the specified confidence level(s).
    """

    # initialize
    if isinstance(confid, (numpy.ndarray, list)):
        confid = numpy.asarray(confid)
        res = numpy.zeros(len(confid), dtype='int')
        single = False
    else:
        confid = numpy.array([confid])
        res = numpy.array([0])
        single = True

    # add stars
    res[confid <= 0.05] += 1
    res[confid <= 0.01] += 1
    res[confid <= 0.001] += 1

    if single:
        return res[0]
    else:
        return res
    
def plot_data(groups, x_name, y_name, categories=None, identifiers=None, 
              mean=False, title=None, x_label=None, y_label=None):
    """
    Plots properties x_name and y_name of groups for specified categories
    and identifiers.

    Plots on an open figure (so needs plt.figure() before this function is 
    executed). If not in interactive mode requires plt.show() after this
    function to show the figure.

    If mean is True also the mean of all plots is plotted.

    Returns a list of plotted lines (line.Line2D objects).
    """
    
    # title and axis labels
    if title is None:
        title = ''
        if categories is not None:
            title = str(categories) + ' '
        elif identifiers is not None:
            title += str(identifiers)
    plt.title(title)
    if x_label is None:
        x_label = x_name
    plt.xlabel(x_label)
    if y_label is None:
        y_label = y_name
    plt.ylabel(y_label)

    # find categories
    if categories is None:
        categories = groups.keys()
    if isinstance(categories, list):
        single_categ = False
    else:
        categories = [categories]
        single_categ = True

    # loop over categories
    for categ in categories:

        # find observations
        if identifiers is None:
            identifs = groups[categ].identifiers
        else:
            identifs = identifiers
        if isinstance(identifs, list):
            single_ident = False
        else:
            identifs = [identifs]
            single_ident = True

        # loop over observations
        lines = []
        for obs_ind, ident in zip(range(len(identifs)), identifs):

            # check if to plot the current observation
            if not ident in identifs:
                continue

            # prepare data
            x_data = getattr(groups[categ], x_name)[obs_ind]
            y_data = getattr(groups[categ], y_name)[obs_ind]

            if mean:
                try:
                    if (x_data_prev == x_data).all():
                        y_sum += y_data
                        graph_count += 1
                    else:
                        logging.warning('In oder to calculate mean all ' \
                                        + 'x-axis values have to be the same.')
                        mean=False
                except NameError:
                    x_data_prev = x_data
                    y_sum = y_data
                    graph_count = 1

            # plot current
            curr_line, = plt.plot(x_data, y_data, label=ident)
            lines.append(curr_line)

    # plot mean
    if mean:
        y_mean = y_sum / float(graph_count)
        lw = lines[-1].get_linewidth() + 1
        line, = plt.plot(x_data, y_mean, label='mean', linewidth=lw)
        lines.append(line)

    return lines

def plot_histogram(groups, name, category, bins, color=None, category_color=None, 
                   edgecolor=None, title=None, x_label=None):
    """
    Plots histogram of the specified property for a given category.

    If category is a list of categories, they are all pooled together.
    """

    # pools categories if needed
    if isinstance(category, list):
        groups.pool(categories=category, name='_all')
        categ = '_all'
    else:
        categ = category

    # color
    if color is None:
        if category_color is not None:
            color = category_color[category]
        else:
            color = None
    print 'color: ', color

    # plot data
    data = getattr(groups[categ], name)
    data = numpy.asarray(pyto.util.nested.flatten(data))
    plt.figure()
    plt.hist(data, bins=bins, facecolor=color, edgecolor=edgecolor)
    
    # finish plot
    if title is None:
        title = str(category)
    plt.title(title)
    if x_label is None:
        x_label = name
    plt.xlabel(x_label)
    plt.show()

    # remove pooled category
    groups.pop('_all', None)


################################################################
#
# Main function
#
###############################################################

def main():
    """
    """

    ##########################################################
    #
    # Read data and calculate few things
    #

    # read tether, connections and sv properties 
    tether = pyto.analysis.Connections.read(files=result_files.tethers, 
                          pixel=imaging.pixel_size, categories=categories)
    conn = pyto.analysis.Connections.read(files=result_files.connections, 
               pixel=imaging.pixel_size, categories=categories, order=tether)
    sv = pyto.analysis.Vesicles.read(files=result_files.sv, 
               pixel=imaging.pixel_size, categories=categories, order=tether,
               membrane=result_files.sv_membrane, lumen=result_files.sv_lumen)
    sv.addLinked(files=result_files.connections)
    clust = pyto.analysis.Clusters.read(files=result_files.clusters, mode='conn',
               categories=categories, order=tether, distances='default')
    layer = pyto.analysis.Layers.read(files=result_files.sv_layers,
                              pixel=imaging.pixel_size, categories=categories)

    # raw data is pickled here (sv_raw.pkl, tether_raw.pkl, conn_raw.pkl)

    # separate svs by size
    [small_sv, sv, big_sv] = sv.splitByRadius(radius=[0, 10, 30, 3000])

    # remove bad svs from tethers and connections
    tether.removeBoundaries(boundary=small_sv)
    tether.removeBoundaries(boundary=big_sv)
    conn.removeBoundaries(boundary=small_sv)
    conn.removeBoundaries(boundary=big_sv)

    # idealy bad svs should be absent from clusters already (cluster script
    # should have the bed sv ids excluded)
    # if not, this removes bad sv's from clusters, but it does not redo
    # clustering and connections clusters are not adjusted
    #clust.removeBoundaries(small_sv)
    #clust.removeBoundaries(big_sv)

    # calculate number of tethers, connections and linked svs for each sv
    sv.getNTethers(tether=tether)
    sv.getNConnections(conn=conn)
    sv.getNLinked()
    sv.getClusterSize(clusters=clust)

    # calculate number of items and max cluster fraction
    clust.findNItems()
    clust.findBoundFract()
    clust.findRedundancy()

    # data is pickled here for later use (sv.pkl, conn.pkl, tether.pkl, clust.pkl, 
    # layer.pkl)

    ##########################################################
    #
    # Separate data in various categories
    #

    # split svs by distance
    bulk_sv = sv.splitByDistance(distance=distance_bins[-1])
    sv_bins = sv.splitByDistance(distance=distance_bins)
    near_sv = sv_bins[0]
    inter_sv = sv_bins[1]
    dist_sv = sv.splitByDistance(distance=[distance_bins[2], distance_bins[-1]])[0]

    # extract svs that are near az, tethered, near+tethered, near-tethered 
    teth_sv, non_teth_sv = bulk_sv.extractTethered(other=True)
    near_teth_sv, near_non_teth_sv = near_sv.extractTethered(other=True)

    # extract connected and non-connected svs 
    conn_sv, non_conn_sv = sv.extractConnected(other=True)
    bulk_conn_sv, bulk_non_conn_sv = bulk_sv.extractConnected(other=True)
    near_conn_sv, near_non_conn_sv = near_sv.extractConnected(other=True)
    inter_conn_sv, inter_non_conn_sv = sv_bins[1].extractConnected(other=True)

    # extract by tethering and connectivity
    near_teth_conn_sv, near_teth_non_conn_sv = \
        near_teth_sv.extractConnected(other=True)    
    near_non_teth_conn_sv, near_non_teth_non_conn_sv = \
        near_non_teth_sv.extractConnected(other=True)    

    ###########################################################
    #
    # SV distribution
    #

    # plot sv layers for all observations
    plot_sv_occupancy(layer=layer, categories=categories, bins=range(0,251,5), 
          pixel_size=imaging.pixel_size, mean=True, x_label=distance_bins_label)

    # sv occupancy 
    analyze_sv_occupancy(layer=layer, bins=[0, 250], 
          pixel_size=imaging.pixel_size, reference=reference, reference_bin=0, 
          test='t', categories=categories, plot_=plot_, 
          category_color=category_color, bar_width=bar_width, 
          font_size=font_size, 
          title='SV occupancy', y_label='Fraction of volume occupied by svs')

    # sv occupancy dependence on distance
    analyze_sv_occupancy(layer=layer, bins=layers_distance_bins, 
          pixel_size=imaging.pixel_size, reference=reference, reference_bin=0, 
          test='t', categories=categories, plot_=plot_, 
          category_color=category_color, bar_width=bar_width, 
          font_size=font_size, bin_label=distance_bins_label, 
          title='SV by layers', y_label='Fraction of volume occupied by svs')

    # min distance to the AZ, fine histogram
    plot_histogram(near_sv, name='minDistance_nm', category='plain', bins=range(0,20),
                   title='Distance: Near sv, plain', 
                   x_label='Min distance to the AZ [nm]')

    # mean of the min distance to the AZ for near svs
    analyze_item(groups=near_sv, name='minDistance_nm', categories=categories, 
                 reference=reference, plot_=plot_, category_color=category_color, 
                 bar_width=bar_width, font_size=font_size, y_label='Mean [nm]',
                 title='Near SV: Min Distance to the AZ')

    # ToDo: max/min for each tomo, average

    ###########################################################
    #
    # Tethering based analysis of svs
    #

    # extract tethers for near az svs
    #near_tether = tether.extractByVesicles(vesicles=near_sv)

    # calculate fraction of svs near the az that are tethered
    get_fraction_tethered_sv(sv=near_sv, categories=categories, 
         reference=reference, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, title='Near svs')

    # calculate fraction of connected svs near the az that are tethered
    get_fraction_tethered_sv(sv=near_conn_sv, categories=categories, 
         reference=reference, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, 
         title='Near connected svs')

    # ToDo: fraction of tethered with 3+ tethers dependence on connectivity

    # analyze n tethers per tethered sv
    analyze_n_tether(sv=near_teth_sv, reference=reference, categories=categories, 
                     test='kruskal', plot_=True, category_color=category_color, 
                     bar_width=bar_width, font_size=font_size,
                     title='N tethers per tethered sv') 

    # analyze n tethers per tethered sv for connected and non-connected
    analyze_n_tether(sv=[near_teth_non_conn_sv, near_teth_conn_sv], 
              reference=reference, categories=categories, test='kruskal', 
              plot_=True, bin_names=['non-conn', 'conn'], 
              category_color=category_color, bar_width=bar_width, 
              font_size=font_size, title='Number of tethers per tethered sv') 

    # histogram of n tethers for tethered svs
    analyze_histogram(groups=near_teth_sv, reference=reference, name='n_tether', 
              bins=[1,2,3,200], categories=categories, 
              plot_=plot_,  category_color=category_color, bar_width=bar_width, 
              font_size=font_size, title='Tethered svs', 
              x_label='N tether')   

    # histogram of n tethers for tethered connected svs
    analyze_histogram(groups=near_teth_conn_sv, reference='HTS', name='n_tether', 
              bins=[1,2,3,200], categories=['plain', 'HTS', 'cemovis', 'TeTx'], 
              plot_=plot_,  category_color=category_color, bar_width=bar_width, 
              font_size=font_size, title='Near tethered connected svs', 
              x_label='N tether')   

    # plot n tethers per sv vs. sv center distance

    # plot n tethers per sv vs. min sv distance
    correlate(near_sv, name_x='minDistance_nm', name_y='n_tether', 
              categories=categories, plot_=plot_, title='Near SV: ', 
              x_label='Min distance to the AZ', y_label='N tethers')

    ##########################################################
    #
    # Connections based analysis of svs
    #

    # calculate fraction of connected svs (connected to other svs)
    get_fraction_connected_sv(sv=bulk_sv, categories=categories, 
         reference=reference, plot_=plot_, bar_width=bar_width,  
         category_color=category_color, font_size=font_size)

    # fraction of connected svs for various distances
    get_fraction_connected_sv(sv=sv_bins, categories=categories, 
         reference=reference, bins=distance_bins, bin_label=distance_bins_label, 
         reference_bin=reference_distance_bin, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # fraction of connected dependence on tethering
    get_fraction_connected_sv(sv=[near_teth_sv, near_non_teth_sv], 
         categories=categories, reference=reference, 
         bin_names=['teth', 'non-teth'], reference_bin=0, plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size)

    # fraction of connections and tethers
    analyze_histogram(groups=[near_teth_conn_sv, near_teth_non_conn_sv, 
                              near_non_teth_conn_sv, near_non_teth_non_conn_sv], 
         reference=reference, categories=categories,
         bin_names=['t c', 't nc', 'nt c', 'nt nc'], plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size, 
         title='Number of Near SVs by Tethering and Connectivity') 

    # n connections per sv dependence on distance 
    analyze_n_connection(sv=sv_bins, reference=reference, test='kruskal',
         categories=categories, bins=distance_bins, bin_label=distance_bins_label, 
         reference_bin=reference_distance_bin, plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # n linked svs per sv dependence on distance 
    analyze_n_linked(sv=sv_bins, reference=reference, test='kruskal',
         categories=categories, bins=distance_bins, bin_label=distance_bins_label, 
         reference_bin=reference_distance_bin, plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # n connections per connected sv dependence on distance 
    analyze_n_connection(sv=bulk_conn_sv.splitByDistance(distance_bins), 
         reference=reference, test='kruskal',
         categories=categories, bins=distance_bins, bin_label=distance_bins_label, 
         reference_bin=reference_distance_bin, plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         title='Number of connections per connected sv')

    # n linked svs per connected sv dependence on distance 
    analyze_n_linked(sv=bulk_conn_sv.splitByDistance(distance_bins), 
         reference=reference, test='kruskal',
         categories=categories, bins=distance_bins, bin_label=distance_bins_label, 
         reference_bin=reference_distance_bin, plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         title='Number of links per connected sv')

    # n connections histogram, connected bulk svs
    analyze_histogram(groups=bulk_conn_sv, name='n_connection', bins=[1,2,3,300], 
         reference=reference, categories=categories, plot_=plot_, 
         category_color=category_color, bar_width=bar_width, font_size=font_size,
         x_label='N connections',
         title='Histogram of n connections per connected bulk sv') 

    # n links histogram, connected bulk svs
    analyze_histogram(groups=bulk_conn_sv, name='n_linked', bins=[1,2,3,300], 
         reference=reference, categories=categories, plot_=plot_, 
         category_color=category_color, bar_width=bar_width, font_size=font_size,
         x_label='N links',
         title='Histogram of n links per connected bulk sv')

    # n connections per conected sv dependence on tethering 
    analyze_n_connection(sv=[near_non_teth_conn_sv, near_teth_conn_sv], 
         reference=reference, test='kruskal', reference_bin=0,
         categories=categories, bin_names=['non teth', 'tethered'], bin_label='', 
         plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # n connections per near sv dependence on n tether
    analyze_n_connection(sv=near_conn_sv.split(name='n_tether', value=[0,1,2,3,200]), 
         reference=reference, test='kruskal', categories=categories, 
         bins=[0,1,2,3,200], reference_bin=0, plot_=True, bar_width=bar_width,
         category_color=category_color, font_size=font_size) 

    # n linked svs per connected sv dependence on tethering 
    analyze_n_linked(sv=[near_non_teth_conn_sv, near_teth_conn_sv], 
         reference=reference, test='kruskal', reference_bin=0,
         categories=categories, bin_names=['non teth', 'tethered'], bin_label='', 
         plot_=True, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # n connection - n tethers for tethered 
    near_teth_sv.apply(funct=numpy.subtract, args=['n_connection', 'n_tether'], 
                       name='conn_min_teth')
    analyze_n_connection(sv=near_teth_sv, n_conn_name='conn_min_teth', 
                     reference=reference, categories=categories, test='kruskal', 
                     plot_=True, category_color=category_color, bar_width=bar_width, 
                     font_size=font_size, title='Connections - Tethers') 


    ###########################################################
    # 
    # Analyze sv radii
    #

    # analyze radii of bulk svs
    analyze_radius(sv=bulk_sv, reference=reference, categories=categories_no_sect, 
                   plot_=True,category_color=category_color, bar_width=bar_width, 
                   font_size=font_size)

    # dependence on the distance to the AZ
    analyze_radius(sv=sv_bins, reference=reference, categories=categories_no_sect,
                   bins=distance_bins, bin_label=distance_bins_label, 
                   reference_bin=reference_distance_bin, plot_=True, 
                   category_color=category_color, bar_width=bar_width, 
                   font_size=font_size)

    # dependence on tethering (bulk sv)
    analyze_radius(sv=[non_teth_sv, teth_sv], reference=reference, 
                   categories=categories_no_sect, bin_names=teth_bins_label, bin_label='', 
                   reference_bin=0, plot_=True, category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (bulk sv)')

    # dependence on tethering (near sv)
    analyze_radius(sv=[near_non_teth_sv, near_teth_sv], reference=reference, 
                   categories=categories_no_sect, bin_names=teth_bins_label, bin_label='', 
                   reference_bin=0, plot_=True, category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (near sv)')

    # dependence on tethering (near sv, plain, HTS and KCl)
    analyze_radius(sv=[near_non_teth_sv, near_teth_sv], reference=reference, 
                   categories=['plain', 'HTS', 'KCl'], bin_names=teth_bins_label, 
                   bin_label='', reference_bin=0, plot_=True, 
                   category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (near sv)')

    # analyze dependence on number of tethers
    analyze_radius_ntether(sv=bulk_sv, reference=reference,  categories=categories_no_sect, 
                   bins=n_conn_bins, bin_label=n_conn_bins_label, 
                   reference_bin=0, plot_=True, category_color=category_color,
                   bar_width=bar_width, font_size=font_size)  

    # dependence on connectivity (all sv)
    analyze_radius(sv=[non_conn_sv, conn_sv], reference=reference, 
                   categories=categories_no_sect, bin_names=conn_bins_label, bin_label='', 
                   reference_bin=0, plot_=True, category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (all sv)')

    # dependence on connectivity (bulk sv)
    analyze_radius(sv=[bulk_non_conn_sv, bulk_conn_sv], reference=reference, 
                   categories=categories_no_sect, bin_names=conn_bins_label, bin_label='', 
                   reference_bin=0, plot_=True, category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (bulk sv)')

    # dependence on connectivity (near sv, plain, HTS and KCl)
    analyze_radius(sv=[near_non_conn_sv, near_conn_sv], reference=reference, 
                   categories=['plain', 'HTS', 'KCl'], bin_names=conn_bins_label, 
                   bin_label='', 
                   reference_bin=0, plot_=True, category_color=category_color, 
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (near sv)')

    # dependence on connectivity (inter sv)
    analyze_radius(sv=inter_sv.extractConnected(other=True), reference=reference,
                   categories=categories_no_sect, 
                   bin_names=['connected', 'non-connected'] , bin_label='',
                   reference_bin=0, plot_=True, category_color=category_color,
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (inter)') 

    # analyze dependence on number of connections (all sv)
    analyze_radius_nconn(sv=sv, reference=reference, categories=categories_no_sect, 
                   bins=n_conn_bins, bin_label=n_conn_bins_label, 
                   reference_bin=0, plot_=True, category_color=category_color,
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (all sv)')  

    # analyze dependence on number of connections (bulk sv)
    analyze_radius_nconn(sv=bulk_sv, reference=reference, categories=categories_no_sect, 
                   bins=n_conn_bins, bin_label=n_conn_bins_label, 
                   reference_bin=0, plot_=True, category_color=category_color,
                   bar_width=bar_width, font_size=font_size,
                   title='Sv radius (bulk sv)')  

    # ananlyze dependence on both tethering and connectivity
    analyze_item(groups=[near_teth_conn_sv, near_teth_non_conn_sv, 
                         near_non_teth_conn_sv, near_non_teth_non_conn_sv], 
                 name='radius_nm', reference=reference, 
                 categories=categories_no_sect, 
                 reference_bin=0, bin_names=['t c', 't nc', 'nt c', 'nt nc'], 
                 plot_=plot_, category_color=category_color, bar_width=bar_width, 
                 font_size=font_size, title='Sv radius (near sv)')

    # radius histogram
    plot_histogram(groups=bulk_sv, name='radius_nm', category='plain', 
                   bins=numpy.arange(10,30,0.5), category_color=category_color,
                   edgecolor='grey', title='Bulk sv, plain')
    plot_histogram(groups=bulk_sv, name='radius_nm', category=categories, 
                   bins=numpy.arange(10,30,0.5), category_color=category_color,
                   title='Bulk sv, all categories')

    # radii of connected vesicles

    ###########################################################
    #
    # Tether and Connection length
    #

    # analyze tether length
    analyze_tether_length(tether=tether, categories=categories_no_sect, 
              reference=reference, test='kruskal', plot_=plot_, 
              bar_width=bar_width, category_color=category_color, 
              font_size=font_size) 

    # analyze tether length dependence on connectivity
    analyze_tether_length(tether=\
                    [tether.extractByVesicles(vesicles=near_non_conn_sv)[0],
                    tether.extractByVesicles(vesicles=near_conn_sv)[0]],
              categories=categories_no_sect, test='kruskal',
              reference=reference, bin_names=['no', 'yes'], reference_bin=0, 
              plot_=plot_, bin_label='Connected', bar_width=bar_width, 
              category_color=category_color, font_size=font_size,
              title='Tether length of near svs') 

    # tether length histograms
    tether_length_histogram(tether=tether, categories=categories_no_sect, 
               bins=[0,5,10,20,40], reference=reference, plot_=plot_, 
               bar_width=bar_width, category_color=category_color, 
               font_size=font_size)
    tether_length_histogram(tether=tether, categories=['plain', 'HTS', 'TeTx'], 
               bins=fine_length_bins, reference='HTS', plot_=plot_, 
               bar_width=bar_width, category_color=category_color, 
               font_size=font_size)

    # analyze connection length
    analyze_connection_length(conn=conn, categories=categories_no_sect, 
              reference=reference, test='kruskal', plot_=plot_,
              bar_width=bar_width, category_color=category_color,
              font_size=font_size) 

    # connection length dependence on the distance to the AZ
    analyze_connection_length(conn=conn.splitByDistance(distance=distance_bins), 
              categories=categories_no_sect, test='kruskal',
              reference=reference, bins=distance_bins, 
              reference_bin=reference_distance_bin, plot_=plot_, 
              bin_label=distance_bins_label, bar_width=bar_width, 
              category_color=category_color, font_size=font_size) 

    # connection length dependence: proximal vs. all other
    analyze_connection_length(conn=conn.splitByDistance(distance=[0, 45, 250]), 
              categories=categories_no_sect, test='kruskal',
              reference=reference, bins=[0, 45, 250], 
              reference_bin=reference_distance_bin, plot_=plot_, 
              bin_label=distance_bins_label, bar_width=bar_width, 
              category_color=category_color, font_size=font_size) 

    # analyze connection length dependence on tethering for near svs
    analyze_connection_length(conn=\
                    [conn.extractByVesicles(vesicles=near_non_teth_sv)[0],
                    conn.extractByVesicles(vesicles=near_teth_sv)[0]],
              categories=categories_no_sect, test='kruskal',
              reference=reference, bin_names=['no', 'yes'], reference_bin=0, 
              plot_=plot_, bin_label='Tethered', bar_width=bar_width, 
              category_color=category_color, font_size=font_size,
              title='Connection length of near svs') 

    # connection length histogram
    connection_length_histogram(conn=conn, categories=categories_no_sect, 
               bins=rough_length_bins, reference=reference, plot_=plot_, 
               bar_width=bar_width, category_color=category_color, 
               font_size=font_size)

    # compare connection and tether lengths
    compare_tether_connection_histogram(tether=tether, conn=conn, 
         category='plain', bins=rough_length_bins, reference='conn', plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size)

    # Tethered sv distance to the AZ (membrane to membrane)
    analyze_item(groups=[near_teth_conn_sv, near_teth_non_conn_sv], 
         name='minDistance_nm', reference=reference, categories=categories, 
         reference_bin=0, test='kruskal', bin_names=['connected', 'non connected'], 
         plot_=plot_, category_color=category_color, bar_width=bar_width, 
         font_size=font_size, y_label='Mean [nm]', 
         title='Min distance to AZ of near svs')


    ###########################################################
    #
    # Vesicle density analysis
    #

    # vesicle lumen density for tethered vs non-tethered
    analyze_obs_rel(groups=[non_teth_sv, teth_sv], reference_bin=0,  
         name='lumen_density', test='t-paired', categories=categories, 
         bin_names=['non-teth', 'tethered'],  plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, format=density_format,
         title='Vesicle (bulk_sv) lumen density')

    # near vesicle lumen density for tethered vs non-tethered
    analyze_obs_rel(groups=[near_non_teth_sv, near_teth_sv], reference_bin=0,  
         name='lumen_density', test='t-paired', categories=categories, 
         bin_names=['non-teth', 'tethered'],  plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, format=density_format,
         title='Vesicle (near sv) lumen density')

    # vesicle lumen density for tethered vs non-tethered
    analyze_obs_rel(groups=[non_teth_sv, teth_sv], reference_bin=0,  
         name='lumen_density', test='t-paired', categories=categories, 
         bin_names=['non-teth', 'tethered'],  plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, format=density_format,
         title='Vesicle lumen density')

    # vesicle membrane density for tethered vs non-tethered
    analyze_obs_rel(groups=[non_teth_sv, teth_sv], reference_bin=0,  
         name='membrane_density', test='t-paired', categories=categories, 
         bin_names=['non-teth', 'tethered'],  plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size, format=density_format,
         title='Vesicle membrane density')

    # difference between lumen and membrane density for tethered vs non-tethered
    analyze_density(groups=[near_non_teth_sv, near_teth_sv], reference=reference, 
         categories=categories, reference_bin=0, bin_names=['non-teth', 'tethered'], 
         format=density_format, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         title='Vesicle (near sv) density dependence on tetehering')

    # difference between lumen and membrane density for connected vs non-connected
    analyze_density(groups=[bulk_non_conn_sv, bulk_conn_sv], reference=reference, 
         categories=categories, reference_bin=0, bin_names=['non-conn', 'connected'], 
         format=density_format, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         title='Vesicle (bulk sv) density dependence on connectivity')

    # difference between lumen and membrane density vs distance
    analyze_density(groups=sv_bins, reference=reference, categories=categories, 
         reference_bin=0, bins=distance_bins, format=density_format, plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size,
         title='Vesicle density dependence on distance to the AZ', 
         bin_label='Distance to the AZ')

    # correlation of lumen density and radius
    correlate(groups=near_sv, name_x='radius', name_y='lumen_density', 
         categories=categories, plot_=plot_)

    ###########################################################
    #
    # Vesicle clustering analysis
    #

    # fraction of total vesicles in a largest cluster
    analyze_item(groups=clust, name='fract_bound_max', test='h', indexed=False, 
         reference=reference, categories=categories, plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size,
         title='Fraction of total vesicles in a largest cluster')

    # histogram of sv cluster sizes 
    cluster_histogram(clust=clust, bins=[1,2,5,50,3000], reference=reference, 
         categories=categories, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # ToDo: histogram showing fraction of svs for different cluster sizes 

    # make clusters without 1-sv clusters
    [one_clust, real_clust] = clust.split(value=[1,2,3000], name='n_bound_clust',
                                          categories=categories)
    real_clust.findNItems()
    real_clust.findBoundFract()
    real_clust.findRedundancy()

    # fraction of total vesicles in a largest cluster excluding 1-sv clusters
    analyze_item(groups=real_clust, name='fract_bound_max', test='h', indexed=False, 
         reference=reference, categories=categories, plot_=plot_, 
         bar_width=bar_width, category_color=category_color, font_size=font_size,
         title='Fraction of total vesicles in a largest cluster')

    # histogram of sv cluster sizes excluding 1-sv clusters
    cluster_histogram(clust=real_clust, bins=[2,5,50,3000], reference=reference, 
         categories=categories, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         y_label='Fraction of connected svs')

    # analyze mean of cluster sizes
    analyze_cluster_size(groups=clust, reference=reference, test='kruskal',
         categories=categories, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size)

    # analyse cluster size for each vesicle 
    analyze_cluster_size_per_sv(groups=bulk_sv, reference=reference, test='kruskal',
         categories=categories, plot_=plot_, bar_width=bar_width, 
         category_color=category_color, font_size=font_size,
         title='Vesicle (bulk sv) cluster sizes')

    # analyze cluster size for each connected vesicle vs distance to the AZ
    analyze_cluster_size_per_sv(groups=conn_sv.splitByDistance(distance_bins), 
         reference=reference, test='kruskal', categories=categories, reference_bin=0, 
         bins=distance_bins, plot_=plot_, bar_width=bar_width, font_size=font_size, 
         category_color=category_color, bin_label='Distance to the AZ', 
         title='Vesicle cluster size for each connected vesicle')

    # loops / connections per tomo
    analyze_item(groups=clust, name='redundancy_obs', reference=reference, 
          categories=categories, test='kruskal', indexed=False, plot_=plot_, 
          category_color=category_color, bar_width=bar_width, font_size=font_size,
          title='Redundancy (loops / connections)')
 
    # loops_links / links per tomo
    analyze_item(groups=clust, name='redundancy_links_obs', reference=reference, 
          categories=categories, test='kruskal', indexed=False, plot_=plot_, 
          category_color=category_color, bar_width=bar_width, font_size=font_size,
          title='Redundancy (loops_links / links)')
 
    # clusters containing near tethered svs that reach to the distal zone
    clust.findDistance(items=sv, distance='meanDistance_nm')
    for categ in categories:
        c_ids = [[ids for x, y, ids in zip(clust[categ].min_distance[obs_ind], clust[categ].max_distance[obs_ind], clust[categ].bound_clusters[obs_ind]) if (x <= 45) and (y > 75)] for obs_ind in range(len(clust[categ].ids))]  
        inter = [numpy.intersect1d(pyto.util.nested.flatten(c_ids[obs_ind]), near_teth_sv[categ].ids[obs_ind]) for obs_ind in range(len(clust[categ].ids))]
        print categ, ': ', sum(len(x) > 0 for x in inter), ' of ', len(inter), ' tomos, ', len(pyto.util.nested.flatten(inter)) , ' of ', len(pyto.util.nested.flatten(near_teth_sv[categ].ids)), ' svs.'

    ###########################################################
    #
    # AZ analysis
    #

    # cluster near svs
    hi_cluster_sv(sv=near_sv, clust=clust, reference=reference, method='average', 
         categories=['plain', 'HTS'], reference_bin=0, test='t', plot_=plot_, 
         category_color=category_color, bar_width=bar_width, font_size=font_size, 
         title='Hierarchical near sv clustering') 

    ###########################################################
    #
    # RRP 
    #

    # split svs and thethers to rrp and non-rrp
    split_categs = {'rat_plain' : ['non_rrp', 'rrp']}
    split(sv=sv, categories=split_categs, name='n_tether', bins=[1,3,300])

    # tether length
    analyze_tether_length(tether=tether, 
              categories=categories_no_sect+['non_rrp', 'rrp'],
              reference=reference, test='kruskal', plot_=plot_,
              bar_width=bar_width, category_color=category_color,
              font_size=font_size)   

    # n tether per tethered sv
    analyze_n_tether(sv=near_teth_sv, reference=reference, 
                     categories=categories+['non_rrp', 'rrp'],
                     test='kruskal', plot_=True, category_color=category_color,
                     bar_width=bar_width, font_size=font_size,
                     title='N tethers per tethered sv')

    # fraction connected
    get_fraction_connected_sv(sv=near_teth_sv, 
         categories=categories+['non_rrp', 'rrp'],
         reference=reference, plot_=plot_, bar_width=bar_width,
         category_color=category_color, font_size=font_size, title='Near svs')   

    # n connections per tethered sv
    analyze_n_connection(sv=near_teth_sv, reference=reference, 
                     categories=categories+['non_rrp', 'rrp'],
                     test='kruskal', plot_=True, category_color=category_color,
                     bar_width=bar_width, font_size=font_size,
                     title='N connection per tethered sv')  

    # separate tethers and near tethered svs into/according to long and short tethers
    short_tether, long_tether = tether.split(name='length_nm', value=[0,5,500])
    near_short_teth_sv = deepcopy(near_teth_sv)
    near_short_teth_sv.getNTethers(short_tether)

    # analyze n short tethers per tethered sv
    analyze_n_tether(sv=near_short_teth_sv, reference=reference, categories=categories, 
                     test='kruskal', plot_=True, category_color=category_color, 
                     bar_width=bar_width, font_size=font_size,
                     title='N tethers per tethered sv') 


    ###########################################################
    #
    # Numbers of analyzed
    #

    # number of synapses
    [(categ, len(bulk_sv[categ].identifiers)) for categ in categories]

    # number of bulk svs
    [(categ, len(pyto.util.nested.flatten(bulk_sv[categ].ids))) \
         for categ in categories]

    # number of tethers
    [(categ, len(pyto.util.nested.flatten(tether[categ].ids))) \
         for categ in categories]

    # number of connections in bulk
    [(categ, len(pyto.util.nested.flatten(conn[categ].ids))) \
         for categ in categories]

# run if standalone
if __name__ == '__main__':
    main()