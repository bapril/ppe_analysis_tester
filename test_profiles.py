#!/usr/bin/python3

import os
import csv
import re

import profiles


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
                p1 = profiles.Profile("normal")
                p2 = profiles.Profile("high")
                with open(dirName+"/"+fname, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        p1.step(int(row['time']), float(row['data']))
                        p2.step(int(row['time']), float(row['data']))
                print("Test: %s-%s Profile: %s  %s  " % (cal_serial, file_serial, p1.report(), p2.report()))
