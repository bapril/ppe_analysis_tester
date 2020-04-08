#!/usr/bin/python3
"""
Simple tool to turn the corpus of breath test results into a csv suitable for Excel
One test per row.
"""

import os
import csv
import re




OUT = open("outfile.csv", "w")
ROOT_DIR = './output/'
for dirName, subdirList, fileList in os.walk(ROOT_DIR):
    print('Found directory: %s' % dirName)
    d = re.match("./output/(\d+)", dirName)
    if d:
        cal_serial = int(d.groups()[0])
        for fname in fileList:
            f = re.match("(\d+)-breath_test.csv", fname)
            if f:
                file_serial = int(f.groups()[0])
                output_row = "%i-%i," % (cal_serial, file_serial)
                with open(dirName+"/"+fname, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        output_row += "%s," % row['data']
                OUT.write(output_row+"\n")

OUT.close()
