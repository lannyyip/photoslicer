from photoslicer.autoslicer import AutoslicerParams, Autoslicer
import getopt

import os
import re
import sys
image_regex="[\w-]+\.(?i:gif|jpe?g|tiff|bmp|png)$"

def usage(argv):
    if isinstance(argv, list):
        print(f"Usage: {argv[0]} [OPTION]\n"
            + "Mandatory auguments:\n"
            + " -i input_dir \tSpecify the input dir\n"
            + " -o output_dir\tSpecify the output dir\n"        
            + "Optional auguments:\n"
            + " -g gaussian \t default 20, min 0, max 100\n"
            + " -m BW thresh method \t0:Simple, 1:Gauss, 2:Outso\n"
            + " -t BW Simple/Outso Thresh Min Value\tdefault 210, min 0, max 255\n"
            + " -b BW Gauss block size\tdefault 64, min 0, max 1000\n"
            + " -n BBox min surfac (% total)\tdefault 2, min 0, max 100\n"
            + " -f BBOX fill thresh\tdefault 10, min 0, max 100\n"
            + " -k Dilate kernel size (0=disabled)\tdefault 0, min 0, max 500\n"
        )

def run(input_dir, output_dir, slice_para):
    file_list = os.listdir(input_dir)
    image_list = [os.path.join(input_dir, file_item) for file_item in file_list  if len(re.findall(image_regex, file_item))>0]
    slicer = Autoslicer(params=slice_para)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for image_file in image_list:
        slicer.load_image(image_file)
        bboxes , image = slicer.autodetect_slices(update_status_callback=print)
        for i_slice, bbox in enumerate(bboxes):
            slicer.save_slice(bbox, os.path.join(output_dir, os.path.basename(image_file)[:-4]+f"_{i_slice}"+image_file[-4:]))


def main(argv):
    
    if True:
        opts, args = getopt.getopt(argv[1:], 'i:o:')
        param_dict = {}
        for item in opts:
            param_dict.update({item[0][-1]:item[1]})

        #print('param dict: ',param_dict)
        config_dict={}

        if 'i' not in param_dict.keys() :
            print("-i is manatory augument")
            usage(argv)
            return
        config_dict.update({'input_dir': param_dict['i']})

        if 'o' not in param_dict.keys() :
            print("-o is manatory augument")
            usage(argv)
            return
        config_dict.update({'output_dir': param_dict['o']})

        slice_para = AutoslicerParams()

        if 'g' in param_dict.keys() :
            slice_para.gaussian.set(int(param_dict['g']))
        if 'm' in param_dict.keys() :
            slice_para.bw_method.set(int(param_dict['m']))
        if 't' in param_dict.keys() :
            slice_para.bw_thresh.set(int(param_dict['t']))
        if 'b' in param_dict.keys() :
            slice_para.bw_gauss.set(int(param_dict['b']))
        if 'm' in param_dict.keys() :
            slice_para.bbox_min_size_prop.set(int(param_dict['m']))
        if 'f' in param_dict.keys() :
            slice_para.bbox_fill_thresh.set(int(param_dict['f']))
        if 'k' in param_dict.keys() :
            slice_para.dilate_kernel.set(int(param_dict['k']))

        config_dict.update({'slice_para': slice_para})
        
        #print('config dict: ',config_dict)
        #print(f'Options Tuple is {opts}')
        #print(f'Additional Command-line arguments list is {args}')
    #except:
    #    print("Input error.")
    #    usage(argv)
        return
    run(**config_dict)

if __name__ == "__main__":
    argv = sys.argv
    main(argv)