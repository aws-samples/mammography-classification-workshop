#pip install opencv-python

# Script to resize images in local folder.

import cv2

import os

# TODO:
#replace with absolute path to directory where raw-jpg and resize folders are
go_back_home = "<<absolute path to directory where raw-jpg and resize folders are>>"

raw_directory = go_back_home + "/raw-jpg/"
resize_directory = go_back_home + "/resize/"

override_file = False

# debug = True
debug = False

for subdir, dirs, files in os.walk(raw_directory):

    for file in files:

        #print os.path.join(subdir, file)
        filepath = subdir + os.sep + file

        if (filepath.endswith(".jpg") or filepath.endswith(".bmp") or filepath.endswith(".jpeg") or filepath.endswith(".png")) and "resize" not in filepath:

            if debug:
                print("filepath: " + filepath)

            img = cv2.imread(filepath)

            # height,width,channel
            res = cv2.resize(img,(150,300),interpolation=cv2.INTER_AREA)

            new_path = ''
            if "CCD" in filepath:
                # print (filepath )
                # print ("CCD"+ os.sep + "resize_" + file)
                new_path = "CCD"
            elif "CCE" in filepath:
                new_path = "CCE"
            elif "MLOD" in filepath:
                new_path = "MLOD"
            elif "MLOE" in filepath:
                new_path = "MLOE"
            elif "NAO" in filepath:
                new_path = "NAO"

            objective = ''
            if "train" in filepath:
                objective = "train"
            elif "test" in filepath:
                objective = "test"
            elif "validate" in filepath:
                objective = "validate"

            objective_path = resize_directory + os.sep + objective
            classification_path = objective_path + os.sep + new_path

            if not os.path.exists(resize_directory):
                os.mkdir(resize_directory)
                if debug:
                    print("Creating directory: " + resize_directory)

            if not os.path.exists(objective_path):
                os.mkdir(objective_path)
                if debug:
                    print("Creating directory: " + objective_path)

            if not os.path.exists(classification_path):
                os.mkdir(classification_path)
                if debug:
                    print("Creating directory: " + classification_path)

            os.chdir(classification_path)

            new_file = "resize_" + file
            if not os.path.exists (new_file) or override_file:
                cv2.imwrite(new_file, res)
                if debug:
                    print("Creating file: " + new_file )

            else:
                if debug:
                    print("File already exists: " + new_file )



print("Process finished")

