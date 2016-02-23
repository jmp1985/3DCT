#!/usr/bin/env python
"""
Extracts sub-images containing individual particles, based on the corresponding
segment positions.

 # Author: Vladan Lucic (Max Planck Institute for Biochemistry)
# $Id: extract_particles.py 524 2009-09-03 14:26:39Z vladan $
"""
__version__ = "$Revision: 524 $"

import sys
import os
import os.path
import time
import platform
import pickle
from copy import copy, deepcopy
import logging

import numpy
import pyto


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%d %b %Y %H:%M:%S')

##############################################################
#
# Parameters
#
##############################################################

###########################################################
#
# Segments
#

# name of the pickle file containing segmentation data (data atribute has to 
#contain segmented image)  
segments_file_name = '../other_directory/segments.pkl'

############################################################
#
# Image (grayscale) file. It should be in em or mrc format.
#

# name of the image file
image_file_name = "../3d/tomo.em"

# binning factor of segments in respect to image
relative_bin = 0

############################################################
#
# Extracted images
#

# size of extracted images in the image file pixels
size = 31

# file name of extracted images (may include directories)
extracted_prefix = 'directory/begin'

extracted_insert_root = True

extracted_suffix = '.em'

pad_ids = True

################################################################
#
# Work
#
################################################################

###########################################
#
# Analysis
#




###########################################
#
# Input / output
#

def machine_info():
    """
    Returns machine name and machine architecture strings
    """
    mach = platform.uname() 
    mach_name = mach[1]
    mach_arch = str([mach[0], mach[4], mach[5]])

    return mach_name, mach_arch

def read_segments(segments_file):
    """
    """
    seg = pickle.load(open(segments_file))
    return seg


def read_image(image_file):
    """
    """
    image = pyto.grey.Image.read(file=image_file)
    return image

def get_file_root(name):
    """
    """
    dir, base = os.path.split(name)
    root, ext = os.path.splitext(base)
    return root

def get_n_digits(pad, max_id=None):
    """
    """
    if isinstance(pad, bool):
        if pad_ids:

            # n_digits according to the max id
            if max_id > 0:
                n_digits = numpy.floor(numpy.log10(max_id)).astype(int) + 1
            else:
                n_digits = 1

        else:
            
            # do not pad
            n_digits = None

    else:

        # n digits specified
        n_digits = pad

    return n_digits

def write_extracted(data, prefix, root, id_, n_digits, suffix):
    """
    """

    # make id string
    if n_digits is not None:
        id_string = ('%0' + str(n_digits) + 'd') % id_
    else:
        id_string = '%d' % id_

    # make file name
    dir, base_suffix = os.path.split(prefix)
    base = base_suffix + root + '_' + id_string + suffix
    file_name = os.path.join(dir, base)
    
    # write file
    file_ = pyto.io.ImageIO()
    file_.write(file=file_name, data=data)


################################################################
#
# Main function
#
###############################################################

def main():
    """
    Main function
    """

    # log machine name and architecture
    mach_name, mach_arch = machine_info()
    logging.info('Machine: ' + mach_name + ' ' + mach_arch)
    logging.info('Begin (script ' + __version__ + ')')

    # read segments and image
    segments = read_segments(segments_file=segments_file_name)
    if isinstance(segments, pyto.segmentation.Hierarchy):
        segments = segments.toSegment()
    image = read_image(image_file=image_file_name)

    # get centers
    mor = pyto.segmentation.Morphology(segments=segments)
    centers = mor.getCenter(real=True)

    # prepare the loop
    bin_fact = 2**relative_bin
    logging.info("Id           Segment center              Particle")
    if extracted_insert_root:
        image_root = get_file_root(name=image_file_name)
    n_digits = get_n_digits(pad=pad_ids, max_id=segments.maxId)

    # iterate over segments
    for id_ in segments.ids:

        # convert center to full size segment coordinates
        full_seg_cent = \
            numpy.array(centers[id_]) + [sl.start for sl in segments.inset]

        # convert center to (full size) image coordinates
        full_image_cent = bin_fact * full_seg_cent + (bin_fact - 1) * 0.5

        # calculate extracted image begin and end positions
        begin = full_image_cent - (size - 1) / 2.
        begin = numpy.rint(begin).astype(int)
        end = begin + size

        # move the extracted image if it falls outside the image
        correct_begin = numpy.zeros_like(begin) - begin
        correct_begin[correct_begin < 0] = 0
        begin = begin + correct_begin
        end = end + correct_begin

        correct_end = end - list(image.data.shape)
        correct_end[correct_end < 0] = 0
        begin = begin - correct_end
        end = end - correct_end

        if (begin < 0).any():
            raise ValueError("Segment " + str(id_) + " can't be repositioned "
                             + "so that it fits inside the image.")  

        # convert to slices
        nd_slice = \
            [slice(begin_1, end_1) for begin_1, end_1 in zip(begin, end)]

        # check if whole segment extracted 

        # extract image
        extract = image.data[nd_slice]

        # write extracted image
        write_extracted(data=extract, prefix=extracted_prefix, root=image_root, 
                        id_=id_, n_digits=n_digits, suffix=extracted_suffix)

        # write to results file

        # print info
        logging.info("%d: %s -> %s", id_, 
                     numpy.array2string(centers[id_]), nd_slice)

# run if standalone
if __name__ == '__main__':
    main()