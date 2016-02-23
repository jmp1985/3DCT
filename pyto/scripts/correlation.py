#!/usr/bin/env python
"""
Establishes EM - LM correlation and correlates spots between EM and LM. The 
procedure is organized as follows:

  1) Find transformation between LM and EM overview systems using specified
  markers. LM markers are typically specified as (coordinates of) features on a 
  LM image, and overview markers (as coordinates) of the same features on a low 
  mag EM image (so that the whole gid square fits on this image, such as 220x).

  This transformation is an affine transformation in 2D, that is it is composed
  of a Gl (general linear) transformation and a translation. The Gl 
  transformation can be decomposed into rotation, scaling along two principal 
  axes, parity (flipping one axis) and shear. The LM - overview transformation
  can be calculated in two ways:

    (a) Direct: Markers lm_markers and overview_markers need to correspond to
    the same spots, the transformation is calculated directly

    (b) Separate gl and translation:  Markers lm_markers_gl and 
    overview_markers_gl have to outline the same shape in the same orientation
    but they need not don't need to be the same spots, that is they can have a 
    fixed displacement. For example, holes on a quantifoil can be used for this 
    purpose. These parameters are used to find the Gl transformation. In the 
    next step, parameters lm_markers_d and overview_markers_d are used to 
    calculate only the translation. 

  2)  Find transformation between EM overview and EM search systems using 
  (overview and search) markers (here caled details). The transformation is
  also affine, but it can be restricted so that instead of the full Gl 
  transformation only orthogonal transformation is used (rotation, one scaling 
  and parity). The EM overview system has to have the same mag as the one used 
  for the LM - overview transformation, while the search system can be chosen 
  in a different way:

    (a) Collage: A collage of medium mag EM images (image size around 10 um) is
    used as a search system and the same overview image as the one used for 
    the LM - overview transformation. The markers (details) are simply 
    identified (as coordinates) of features found in these images 
    (overview_detail and search_detail). Parameter overview2search_mode has to 
    be set to 'move search'. This is conceptually the simplest method, but 
    assembling the EM image collage might take some time or not be feasible.

    (b) Stage, move search: The same overview image as the one used for 
    the LM - overview transformation is used for the overview system, but the
    stage movement system is used for the search system. Specifically, for each
    detail (markers for this transformation) found on the overview image, the 
    EM stage needs to be moved so that the same feature is seen in the center 
    of the EM image made at a medium mag (image size typically up to 10 um). 
    The stage coordinates are used as search details. Parameter 
    overview2search_mode has to be set to 'move search'. The difficulty here is
    to find enough features that are seen in the overview image but can be 
    easily navigated to in search (cracks in ice are often used).

    (c) Stage, move overview: First one feature needs to be identified on the 
    overview image used for the LM - overview transformation. The coordinates 
    of that feature are used as one marker (search_detail) and the EM stage 
    cooordinates for that image is the corresponding search marker 
    (search_detail). This particular stage position has also to be specified
    as search_main parameter. The other markers are obtained by moving the
    stage around (typically 10 - 20 um) and making overview at these positions.
    Coordinates of the feature at overview images, and the corresponding 
    stage coordinates are used as overview and stage markers. Naturally, the 
    feature has to be present in all overview images. Parameter 
    overview2search_mode has to be set to 'move overview'. This is perhaps the
    easiest method to use, but conceptually the most difficult.

  3) Calculates transformation between LM and search systems as a composition of
  the LM - overview and overview - search transforms

  4) Correlates spots specified in one system to the other systems. Coordinates 
  of spots correlated to search system are interpreted according to the mathod
  used to establish the overview - search transformation (see point 2)

    (a) Collage: Spots in search system are simply the coordinates in the 
    collage used for the overview - search transformation.

    (b) Stage, move search: Correlated spots are stage coordinates where
    spots are located in the center of search images (medium mag).

    (c) Stage, move overview: Correlated spots are stage coordinates. An search
    image made at this stage position (low mag) contains the spot at the
    coordinate specified by parameter overview_center.

Note: For reading rows from a file (such as lm_markers_file) top rows
containing comments are ignored, and the data rows are numbered from 0 up. 
That is, the first data row is specified by row 0 in parameters such as 
lm_markers_rows. 

ToDo: expand 

# Author: Vladan Lucic (Max Planck Institute for Biochemistry)
# $Id: correlation.py 980 2013-07-05 08:37:31Z vladan $
"""

__version__ = "$Revision: 980 $"

import sys
import os
import os.path
import time
import platform
from copy import copy, deepcopy
import logging

import numpy
import scipy
import scipy.io

import pyto
from pyto.scene.em_lm_correlation import EmLmCorrelation

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%d %b %Y %H:%M:%S')

##################################################################
#
# Parameters
#
#################################################################

##################################################################
#
# General
#

# Note: To read all rows from a file set rows to None 
#
# Note: Rows are counted from 0 on, comment rows (such as table head) are
# not counted

# Positions file type
positions_file_type = 'imagej'

# X and y columns in positions file(s)
xy_columns = [2, 3]

##################################################################
#
# Establishing LM to overview correlation
#

# LM markers: file name and rows 
# Note: either lm_markers_rows or lm_markers_rows_gl and lm_markers_rows_d need
# to be specified.
lm_markers_file = 'correlation_data.dat'
lm_markers_rows = range(6, 10)
#lm_markers_rows_gl = range(6, 10)
#lm_markers_rows_d = range(6, 7)

# EM overview markers
# Note: either overview_markers_rows or overview_markers_rows_gl and 
# overview_markers_rows_d need to be specified.
overview_markers_file = lm_markers_file
overview_markers_rows = range(0, 4)
#overview_markers_rows_gl = range(0, 4)
#overview_markers_rows_d = range(0, 1)

# Type of transformation for LM to overview: 'gl' for general linear
# transformation or 'rs' for rotation and isotropic scaling (appropriate if 
# grid is flat and horizontal in LM and EM) 
lm2overview_type = 'gl'

##################################################################
#
# Establishing overview to search correlation
#

# Correlation between overview and search ('move search' or 'move overview')
overview2search_mode = 'move overview'

## EM overview detail
overview_detail_file = lm_markers_file
overview_detail_rows = range(13, 17)

# EM search detail (stage coordinates)
search_detail = [[2, -0.2],
                 [4, -1],
                 [6, 0],
                 [5.2, 1]]
#search_detail_file = 'detail_tomo1.dat'
#search_detail_rows = range(1, 10, 2)

# Stage position of the main EM overview image ('move overview' mode only)
search_main = search_detail[0]

# Position at the main overview image correlated to LM spots, typically the 
# center of the image ('move overview' mode only)
overview_center = [512, 512]

# X and y columns in overview_detail and search_detail files
detail_xy_columns = [-3, -2]

# Type of transformation for overview to search: 'gl' for general linear
# transformation or 'rs' for rotation and isotropic scaling (appropriate if 
# there are no distorsions in overview and search
overview2search_type = 'gl'

##################################################################
#
# Points to be correlated
#

# LM spots file
lm_spots_file = lm_markers_file
lm_spots_rows = range(6, 10)

# x and y columns in lm_spots_file
lm_spots_xy_columns = xy_columns

# EM overview spots
overview_spots = [[226, 558]]

# EM overview spot labels (has to have the same length as overview_spots)
overview_spot_labels = ['tomo 1, roughly']

# EM search spots
search_spots = [[2, -1],
                [2, 1],
                [6, 1],
                [6, -1]]
#search_spots_file = 'detail_tomo1.dat'
#search_spots_rows = [10]

# EM search spot labels (has to have the same length as search_spots)
search_spot_labels = ['tomo 1', 'tomo 2', '', '']

# x and y columns in lm_spots_file
search_spots_xy_columns = xy_columns

# Name of the results file
results_file = 'corr.dat'


#####################################################################
#
# Functions
#
#####################################################################

def machine_info():
    """
    Returns machine name and machine architecture strings
    """
    mach = platform.uname() 
    mach_name = mach[1]
    mach_arch = str([mach[0], mach[4], mach[5]])

    return mach_name, mach_arch

def write_results(corr, res_file_name):
    """
    Writes results to a file
    """

    # open results file
    res_file = open(res_file_name, 'w')
    
    # machine info
    mach_name, mach_arch = machine_info()
    header = ["#",
        "# Machine: " + mach_name + " " + mach_arch,
        "# Date: " + time.asctime(time.localtime())]
    
    # file names and times
    script_file_name = sys.modules[__name__].__file__
    script_time = \
        time.asctime(time.localtime(os.path.getmtime(script_file_name)))
    header.extend([\
            "#",
            "# Input script: " + script_file_name + " (" + script_time + ") " \
                + __version__,
            "# Working directory: " + os.getcwd()])
            
    # correlation parameters
    header.extend([
            "#",
            "# Correlation parameters",
            "#",
            "# LM to EM overview:",
            "#   - rotation = %6.1f" % corr.lm2overview.phiDeg \
                + ",  scale = [%6.3f, %6.3f]" \
                % (corr.lm2overview.scale[0], corr.lm2overview.scale[1]) \
                + ",  parity = %d" % corr.lm2overview.parity \
                + ",  shear = %7.3f" % corr.lm2overview.shear,
            "#   - translation = [%6.3f, %6.3f]" % (corr.lm2overview.d[0],
                                                    corr.lm2overview.d[1]),
            "#   - rms error: " \
                + "(in EM overview units) %6.2f" % corr.lm2overview.rmsError \
                + ",  (in LM units) %6.2f" % corr.overview2lm.rmsError
            ])
    try:
        header.extend([
            "#   - error (in EM overview units): " \
                + str(corr.lm2overview.error)
            ])
    except AttributeError:
        header.extend([
            "#   - Gl error (in EM overview units): " \
                + str(corr.lm2overview.errorGl),
            "#   - Translation error (in EM overview units): " \
                + str(corr.lm2overview.errorD)
            ])
    header.extend([
            "#",
            "# EM overview to search:",
            "#   - rotation = %6.1f" % corr.overview2search.phiDeg \
                + ",  scale = [%6.3f, %6.3f]" \
                % (corr.overview2search.scale[0], 
                   corr.overview2search.scale[1]) \
                + ",  parity = %d" % corr.overview2search.parity \
                + ",  shear = %7.3f" % corr.overview2search.shear,
            "#   - translation = [%6.3f, %6.3f]" % (corr.overview2search.d[0],
                                                    corr.overview2search.d[1]),
            "#   - rms error: " \
                + "(in EM search units) %6.2f" % corr.overview2search.rmsError \
                + ",  (in EM overview units) %6.2f" \
                % corr.search2overview.rmsError,
            "#   - error (in EM search units): " \
                + str(corr.overview2search.error),
            "#",
            "# LM to EM search:",
            "#   - rotation = %6.1f" % corr.lm2search.phiDeg \
                + ",  scale = [%6.3f, %6.3f]" \
                % (corr.lm2search.scale[0], corr.lm2search.scale[1]) \
                + ",  parity = %d" % corr.lm2search.parity \
                + ",  shear = %7.3f" % corr.lm2search.shear,
            "#   - translation = [%6.3f, %6.3f]" % (corr.lm2search.d[0],
                                                    corr.lm2search.d[1]),
            "#   - rms error: " \
                + "(in EM search units) %6.2f" % corr.lm2search.rmsErrorEst,
            ])
    if corr.overviewCenter is not None:
        header.extend([
                "",
                "#",
                "# Overview center: [%d, %d]" % (corr.overviewCenter[0], 
                                                 corr.overviewCenter[1]),
                "# Main search: [%d, %d]" % (corr.searchMain[0], 
                                             corr.searchMain[1]),
                "#"])

    # write header
    for line in header:
        res_file.write(line + os.linesep)

    # LM spots correlation results
    table = []
    if (corr.lmSpots is not None) and (len(corr.lmSpots) > 0):
        table.extend([\
                "#",
                "# Correlation of LM spots",
                "#",
                "#  id        LM         EM overview       EM search" ])
        out_vars = [corr.lmSpots[:,0], corr.lmSpots[:,1],
                    corr.overviewFromLmSpots[:,0], 
                    corr.overviewFromLmSpots[:,1],
                    corr.searchFromLmSpots[:,0], corr.searchFromLmSpots[:,1]]
        out_format = ' %3u   %6.2f %6.2f   %6.0f %6.0f   %6.1f %6.1f '
        n_res = corr.lmSpots.shape[0]
        ids = range(n_res)
        res_tab_1 = pyto.io.util.arrayFormat(arrays=out_vars, format=out_format,
                                             indices=ids, prependIndex=True)
        table.extend(res_tab_1)

    # EM overview spots correlation results
    if (corr.overviewSpots is not None) and (len(corr.overviewSpots) > 0):
        table.extend([
                '',
                "#",
                "# Correlation of EM overview spots",
                "#",
                "#  id        LM         EM overview       EM search" ])
        out_vars_overview = [
            corr.lmFromOverviewSpots[:,0], corr.lmFromOverviewSpots[:,1],
            corr.overviewSpots[:,0], corr.overviewSpots[:,1],
            corr.searchFromOverviewSpots[:,0], 
            corr.searchFromOverviewSpots[:,1]]
        out_format_overview = ' %3u   %6.2f %6.2f   %6.0f %6.0f   %6.1f %6.1f '
        if corr.overviewSpotLabels is not None:
            out_vars_overview += [corr.overviewSpotLabels]
            out_format_overview += '  %s '
        n_res = corr.overviewSpots.shape[0]
        ids = range(n_res)
        res_tab_2 = pyto.io.util.arrayFormat(
            arrays=out_vars_overview, format=out_format_overview,
            indices=ids, prependIndex=True)
        table.extend(res_tab_2)

    # EM search spots correlation results
    if (corr.searchSpots is not None) and (len(corr.searchSpots) > 0):
        table.extend([
                '',
                "#",
                "# Correlation of EM search spots",
                "#",
                "#  id        LM         EM overview       EM search" ])
        out_vars_search = [
            corr.lmFromSearchSpots[:,0], corr.lmFromSearchSpots[:,1],
            corr.overviewFromSearchSpots[:,0], 
            corr.overviewFromSearchSpots[:,1],
            corr.searchSpots[:,0], corr.searchSpots[:,1]]
        out_format_search = ' %3u   %6.2f %6.2f   %6.0f %6.0f   %6.1f %6.1f '
        if corr.searchSpotLabels is not None:
            out_vars_search += [corr.searchSpotLabels]
            out_format_search += '  %s '
        n_res = corr.searchSpots.shape[0]
        ids = range(n_res)
        res_tab_2 = pyto.io.util.arrayFormat(
            arrays=out_vars_search, format=out_format_search,
            indices=ids, prependIndex=True)
        table.extend(res_tab_2)

    # write data table
    for line in table:
        res_file.write(line + os.linesep)

            
#####################################################################
#
# Main
#
#####################################################################

def main():
    """
    Main function
    """

    #####################################################################
    #
    # Get positions
    #
  
    # initialize
    corr = EmLmCorrelation()

    # setup positions for lm2overview
    pos_read = {}
    try:
        pos_read['lmMarkers'] = (lm_markers_file, lm_markers_rows)
        pos_read['overviewMarkers'] = (overview_markers_file, 
                                       overview_markers_rows)
    except NameError:
        pos_read['lmMarkersGl'] = (lm_markers_file, lm_markers_rows_gl)
        pos_read['lmMarkersD'] = (lm_markers_file, lm_markers_rows_d)
        pos_read['overviewMarkersGl'] = (overview_markers_file, 
                                         overview_markers_rows_gl)
        pos_read['overviewMarkersD'] = (overview_markers_file, 
                                        overview_markers_rows_d)

    # read positions for lm2overview
    corr.readPositions(specs=pos_read, format=positions_file_type, 
                       xyColumns=xy_columns)

    # setup positions for overview2search
    pos_read = {}
    corr.mode = overview2search_mode
    pos_read['overviewDetail'] = (overview_detail_file, 
                                   overview_detail_rows)
    try:
        corr.searchDetail = numpy.asarray(search_detail)
    except NameError:
        pos_read['searchDetail'] = (search_detail_file, search_detail_rows)

    # read positions for overview2search
    corr.readPositions(specs=pos_read, format=positions_file_type, 
                       xyColumns=detail_xy_columns)

    # setup move overview mode for overview2search
    if corr.mode == 'move overview':
        corr.searchMain = search_main
        corr.overviewCenter = overview_center

    # setup spots
    spot_pos_read = {}
    try:
        spot_pos_read['lmSpots'] = (lm_spots_file, lm_spots_rows)
    except NameError: 
        corr.lmSpots = None
    corr.readPositions(specs=spot_pos_read, format=positions_file_type, 
                       xyColumns=lm_spots_xy_columns)
    try:
        corr.overviewSpots = numpy.asarray(overview_spots)
    except NameError: 
        corr.overviewSpots = None
    try:
        corr.overviewSpotLabels = overview_spot_labels
    except NameError: 
        corr.overviewSpotLabels = None
    try:
        corr.searchSpots = numpy.asarray(search_spots)
    except NameError: 
        corr.searchSpots = None
        try:
            spot_pos_read['searchSpots'] = (search_spots_file, 
                                            search_spots_rows)
        except NameError: pass
    try:
        corr.searchSpotLabels = search_spot_labels
    except NameError: 
        corr.searchSpotLabels = None
    corr.readPositions(specs=spot_pos_read, format=positions_file_type, 
                       xyColumns=search_spots_xy_columns)


    #####################################################################
    #
    # Correlate
    #
            
    # establish correlation
    corr.establish(lm2overviewType=lm2overview_type, 
                   overview2searchType=overview2search_type)

    # inverse correlations
    corr.search2lm = corr.lm2search.inverse()
    corr.overview2lm = corr.lm2overview.inverse() 
    if corr.overview2lm.rmsError is None:
        scale = numpy.sqrt(numpy.multiply.reduce(corr.overview2lm.scale))
        if corr.lm2overview.rmsError is not None:
            corr.overview2lm._rmsError = corr.lm2overview.rmsError * scale
        elif corr.lm2overview.rmsErrorEst is not None:
            corr.overview2lm._rmsError = corr.lm2overview.rmsErrorEst * scale
        else:
            corr.overview2lm._rmsError = None
    corr.search2overview = corr.overview2search.inverse() 

    # correlate LM spots
    if corr.lmSpots is not None:
        corr.searchFromLmSpots = corr.lm2search.transform(corr.lmSpots)
        corr.overviewFromLmSpots = corr.lm2overview.transform(corr.lmSpots)

    # correlate overview spots
    if corr.overviewSpots is not None:
        corr.lmFromOverviewSpots = \
            corr.overview2lm.transform(corr.overviewSpots)
        corr.searchFromOverviewSpots = \
            corr.overview2search.transform(corr.overviewSpots)

    # correlate EM search spots
    if corr.searchSpots is not None:
        corr.lmFromSearchSpots = corr.search2lm.transform(corr.searchSpots)
        corr.overviewFromSearchSpots = \
            corr.search2overview.transform(corr.searchSpots)

    #####################################################################
    #
    # Output
    #

    write_results(corr=corr, res_file_name=results_file)


# run if standalone
if __name__ == '__main__':
    main()