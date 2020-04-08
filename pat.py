#!/usr/bin/python3
"""
Code to operate P.A.T. PPE Analysis Test-stand
"""
import os
import time
import datetime
import sys
import select
import fcntl
import termios

import board
import busio
import digitalio
import adafruit_mprls
import adafruit_bme280
import adafruit_tsl2561
from adafruit_debouncer import Debouncer
import matplotlib.pyplot as plt
import profiles as pf
import pandas as pd
from colorama import Fore, Back, Style
from tqdm import tqdm

###############
#
# Setup Serial Interfaces
#
###############
I2C = busio.I2C(board.SCL, board.SDA)

###############
#
# Setup GPIO Devices
#
###############
SOLONOID = digitalio.DigitalInOut(board.D17)
SOLONOID.direction = digitalio.Direction.OUTPUT
SOLONOID.value = False

RED_BUTTON_PIN = digitalio.DigitalInOut(board.D18)
RED_BUTTON_PIN.direction = digitalio.Direction.INPUT
RED_BUTTON_PIN.pull = digitalio.Pull.UP
RED_BUTTON = Debouncer(RED_BUTTON_PIN)

BLUE_BUTTON_PIN = digitalio.DigitalInOut(board.D27)
BLUE_BUTTON_PIN.direction = digitalio.Direction.INPUT
BLUE_BUTTON_PIN.pull = digitalio.Pull.UP
BLUE_BUTTON = Debouncer(BLUE_BUTTON_PIN)

# In test mode the sensors are simulated and the (r) and (b) buttons on the
# keyboard will work in place of the GPIO buttons.

TEST_MODE = False

###############
#
# Setup I2C Devices
#
###############

if not TEST_MODE:

    # Address 18
    MPR = adafruit_mprls.MPRLS(I2C, psi_min=0, psi_max=25)

    # Address 77
    BME280 = adafruit_bme280.Adafruit_BME280_I2C(I2C)

    TLS2561 = adafruit_tsl2561.TSL2561(I2C)
    TLS2561.enabled = True
    time.sleep(1)

    # Set gain 0=1x, 1=16x
    TLS2561.gain = 1

    # Set integration time (0=13.7ms, 1=101ms, 2=402ms, or 3=manual)
    TLS2561.integration_time = 1

###############
#
# Setting Internal Variables
#
###############

if TEST_MODE:
    CAL = 0.0
else:
    CAL = MPR.pressure
CAL_CYCLES = 0
LAST_CAL = 0.0
LAST_CAL_SAMPLE_PASSED = False
CAL_DELTA_AVERAGE = 0.0
CAL_COUNT = 0
CAL_DF = pd.DataFrame()
CAL_TEMP = 0.0
CAL_RH = 0.0
i = 0
AVERAGE = 0.0
AVERAGE_TEMP = 0.0
AVERAGE_RH = 0.0
STATE = "start"
P_VAL = 0.0
SAMPLES_IN_RANGE = 0
CAL_VALUE = 0.0
MY_EMA = 0.0
P1 = None
P2 = None

VISIBLE_MAX = 0.0
VISIBLE_LIMIT = 150.00
PASS_VISIBLE = False
ENTER_STATE = True

CAL_SERIAL_FILE = "./cal_serial.txt"
TEST_SERIAL = 0

###############
#
# Build internal functions
#
###############


def menu(title, doc, red, blue):
    print("\n\n")
    print(Fore.BLACK + Back.WHITE + '{:^50}'.format(title) + Style.RESET_ALL)
    print(doc)
    if red == "":
        print(Fore.WHITE + Back.BLACK + "                         " + Style.RESET_ALL, end="")
    else:
        print(Fore.WHITE + Back.RED + '{:^25}'.format(red) + Style.RESET_ALL, end="")
    if blue == "":
        print(Fore.WHITE + Back.BLACK + "                         " + Style.RESET_ALL)
    else:
        print(Fore.WHITE + Back.BLUE + '{:^25}'.format(blue) + Style.RESET_ALL)

def read_integers(filename):
    with open(filename) as fhandle:
        return int(fhandle.read())

def check_red():
    if RED_BUTTON.fell:
        return True
    if TEST_MODE:
        _inp, _outp, _err = select.select([sys.stdin], [], [])
        char = sys.stdin.read()
        if char == 'r':
            return True
    return False

def check_blue():
    if BLUE_BUTTON.fell:
        return True
    if TEST_MODE:
        _inp, _outp, _err = select.select([sys.stdin], [], [])
        char = sys.stdin.read()
        if char == 'b':
            return True
    return False

def exponential_moving_average(period=500):
    """ Exponential moving average. Smooths the values in v over ther
    period. Send in values - at first it'll return a simple average,
    but as soon as it's gahtered 'period' values, it'll start to use
    the Exponential Moving Averge to smooth the values.
    period: int - how many values to smooth over (default=100). """
    multiplier = 2 / float(1 + period)
    cum_temp = yield None  # We are being primed

    # Start by just returning the simple average until we have enough data.
    for j in range(1, period + 1):
        cum_temp += yield cum_temp / float(j)

    # Grab the simple avergae
    EMA = cum_temp / period

    # and start calculating the exponentially smoothed average
    while True:
        EMA = (((yield EMA) - EMA) * multiplier) + EMA

###############
#
# Setup the environment
#
###############

fdescr = sys.stdin.fileno()
newattr = termios.tcgetattr(fdescr)
newattr[3] = newattr[3] & ~termios.ICANON
#newattr[3] = newattr[3] & ~termios.ECHO
termios.tcsetattr(fdescr, termios.TCSANOW, newattr)

oldterm = termios.tcgetattr(fdescr)
oldflags = fcntl.fcntl(fdescr, fcntl.F_GETFL)
fcntl.fcntl(fdescr, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

if os.path.exists(CAL_SERIAL_FILE):
    CAL_SERIAL = read_integers(CAL_SERIAL_FILE)
    CAL_SERIAL = CAL_SERIAL + 1
else:
    CAL_SERIAL = 1
OUTPUT_PATH = "./output/%i/" % CAL_SERIAL
CF = open(CAL_SERIAL_FILE, "w+")
CF.write("%i" % CAL_SERIAL)
CF.close()

print("Calibration Serial Number: %i" % CAL_SERIAL)

# Check for output directory.
if not os.path.isdir("./output"):
    os.makedirs("./output")

# Check for output/CAL_SERIAL directory
if not os.path.isdir("./output/%i" % CAL_SERIAL):
    os.makedirs("./output/%i" % CAL_SERIAL)

EMA = exponential_moving_average()
next(EMA)

###############
#
# Running Test Sequence.
#
###############

# Collect calibration data.
i = 0
while True:
    if TEST_MODE:
        AVERAGE = (0.0/3) + ((AVERAGE/3) * 2)
    else:
        AVERAGE = (MPR.pressure/3) + ((AVERAGE/3) * 2)
    RED_BUTTON.update()
    BLUE_BUTTON.update()
    i = i + 1
    if STATE == "start":
        if ENTER_STATE:
            menu("Starting P.A.T.", "Do you want to test or calibrate?", "Test", "Calibrate")
            ENTER_STATE = False
        if check_red():
            ENTER_STATE = True
            STATE = "light_or_dark"
        if check_blue():
            ENTER_STATE = True
            STATE = "foo"

    elif STATE == "light_or_dark":
        if ENTER_STATE:
            menu("Is this mask translucnet?", "We'll skip the light-test process if the\n" +
                 "mask is translucent or transprent.", "Opaque", "Translucent")
            ENTER_STATE = False
            TEST_SERIAL =+ 1
        if check_red():
            ENTER_STATE = True
            STATE = "pre_light_test"
        if check_blue():
            ENTER_STATE = True
            STATE = "calibrate_pressure"
    elif STATE == "calibrate_pressure":
        if ENTER_STATE:
            print("")
            print("Calibration Started. Do not disturb test stand.")
            print("Pressure test will begin automatically once calibration is complete.")
            ENTER_STATE = False
            SAMPLES_IN_RANGE = 0
            i = 0
            CAL_DF = pd.DataFrame([[0, 0, 0, 0]], columns=['time', 'pressure', 'ema',
		                                                         'samples_passed'])
            t = tqdm(total=100)
        if i > 500:
            MY_EMA = EMA.send(AVERAGE)
            P_VAL = AVERAGE - MY_EMA
            if P_VAL < 0.1 and P_VAL > -0.1:
                SAMPLES_IN_RANGE = SAMPLES_IN_RANGE + 1
                t.update(1)
            else:
                SAMPLES_IN_RANGE = 0
                t.reset(100)
            DF1 = pd.DataFrame([[i, P_VAL, MY_EMA, SAMPLES_IN_RANGE]],
                               columns=['time', 'pressure', 'ema', 'samples_passed'])
            CAL_DF = CAL_DF.append(DF1, ignore_index=True)
            if SAMPLES_IN_RANGE > 100:
                t.close()
                CAL_VALUE = MY_EMA
                ENTER_STATE = True
                STATE = "pressure_test"
                print("Calibration Complete")
                ENTER_STATE = True
                CAL_DF.to_csv("%s%i-cal_dataframe.csv" % (OUTPUT_PATH, TEST_SERIAL),
                              index=False, header=True)
    elif STATE == "pre_light_test":
        if ENTER_STATE:
            menu("Prepare for Light Test", "Install the mask and check the seal\n" +
                 "have a flashlight ready to scan the seal", "Begin", "Go Back")
            ENTER_STATE = False
        if check_red():
            ENTER_STATE = True
            STATE = "light_test"
        if check_blue():
            ENTER_STATE = True
            STATE = "light_or_dark"
    elif STATE == "light_test":
        if ENTER_STATE:
            plt.clf()
            menu("Light Test in process", "sweep flashlight around the edge of the mask.",
                 "Done", "")
            ENTER_STATE = False
            i = 0
            VISIBLE_MAX = 0.0
            LIGHT_DF = pd.DataFrame([[0, 0, 0, 0]], columns=['time',
                                                             'limit', 'reading', 'high_water'])
        if TEST_MODE:
            LUX = 0.0
        else:
            LUX = TLS2561.lux

        if LUX is not None:
            if LUX > VISIBLE_MAX:
                VISIBLE_MAX = LUX
            if LUX > VISIBLE_LIMIT:
                DF1 = pd.DataFrame([[i, VISIBLE_LIMIT, LUX, VISIBLE_MAX]],
                                   columns=['time', 'limit', 'reading', 'high_water'])
                LIGHT_DF = LIGHT_DF.append(DF1, ignore_index=True)
                plt.plot('time', 'limit', data=LIGHT_DF)
                plt.plot('time', 'reading', data=LIGHT_DF)
                plt.plot('time', 'high_water', data=LIGHT_DF)
                plt.legend()
                plt.show()
                ENTER_STATE = TRUE
                STATE = "pre_light_test"
                print("Light Test complete: FAILED")
                print("")
                print("Press Button to restart visual test.")
                LIGHT_DF.to_csv("%s%i-light_test.csv" % (OUTPUT_PATH, TEST_SERIAL),
                                index=False, header=True)
        else:
            LUX = 0.0
        DF1 = pd.DataFrame([[i, 0.5, LUX, VISIBLE_MAX]],
                           columns=['time', 'limit', 'reading', 'high_water'])
        LIGHT_DF = LIGHT_DF.append(DF1, ignore_index=True)
        if check_red():
            print("Light Test complete: PASSED")
            LIGHT_DF.to_csv("%s%i-light_test.csv" % (OUTPUT_PATH, TEST_SERIAL),
                            index=False, header=True)
            PASS_VISIBLE = True
            STATE = "calibrate_pressure"
            PASS_BREATHE = True
            plt.plot('time', 'limit', data=LIGHT_DF)
            plt.plot('time', 'reading', data=LIGHT_DF)
            plt.plot('time', 'high_water', data=LIGHT_DF)
            plt.legend()
            plt.show()
    elif STATE == "pressure_test":
        if ENTER_STATE:
            print("Starting Pressure test.")
            BREATHE_DF = pd.DataFrame([[0, 0, 0, 0]], columns=['time', 'high', 'data', 'low'])
            i = 0
            ENTER_STATE = False
            P1 = pf.Profile("normal")
            P2 = pf.Profile("high")

        P_VAL = AVERAGE - CAL_VALUE
        P1.step(i, P_VAL)
        high = P2.step_plot(i, P_VAL)

        DF1 = pd.DataFrame([[i, high['min'], P_VAL, high['max']]],
                           columns=['time', 'high', 'data', 'low'])
        BREATHE_DF = BREATHE_DF.append(DF1)

        if i == 5:
            SOLONOID.value = True
        elif i == 50:
            SOLONOID.value = False
        if i == 99:
            STATE = "report"
            ENTER_STATE = True
    elif STATE == "report":  # Generate report
        if ENTER_STATE:
            i = 0
            plt.plot('time', 'high', data=BREATHE_DF)
            plt.plot('time', 'data', data=BREATHE_DF)
            plt.plot('time', 'low', data=BREATHE_DF)
            plt.legend()
            plt.show()
            BREATHE_DF.to_csv("%s%i-breath_test.csv" % (OUTPUT_PATH, TEST_SERIAL),
                              index=False, header=True)
            print("")
            print("")
            print("")
            print("")
            print("")
            report = "Amherst Makerspace: PPE Analysis Test-stand (PAT)\n\n"
            report += "Test Serial #: %i-%i\n" % (CAL_SERIAL, TEST_SERIAL)
            now = datetime.datetime.now()
            report += "Tested At: %s \n" % now.strftime("%Y-%m-%d %H:%M:%S")
            if not TEST_MODE:
                report += "Raw Barometric Pressure: %f mPa\n" % MPR.pressure
                report += "Barometric Calibration Value: %f mPa\n" % CAL_VALUE
                report += "Temprature: %f Degrees C\n" % BME280.temperature
                report += "Reletive Humidity: %f %%\n\n\n" % BME280.humidity
            report += " ################## Visible Light Test ##################\n"
            if PASS_VISIBLE:
                report += "Test Status: Passed\n"
            else:
                report += "Test Status: Failed\n"
            report += "Maximum Light Level: %f (limit %f)\n" % (VISIBLE_MAX, VISIBLE_LIMIT)
            report += "\n\n"
            report += " ##################### Pressure Test ####################\n"
            report += " Profile: \n"
            normal = P1.report()
            if normal['passed']:
                report += "  %s   PASSED\n" % P1.name
            else:
                report += ("  %s   FAILED\n\t\t missed %d out of 100 %f %%" %
                           (P1.name,
                            normal['failed_points'],
                            (normal['failed_points'] / normal['points'])))

            high = P2.report()
            if high['passed']:
                report += "  %s   PASSED\n" % P2.name
            else:
                report += ("  %s   FAILED\n\t\t missed %d out of 100 %f %%" %
                           (P2.name,
                            high['failed_points'],
                            (high['failed_points'] / high['points'])))

            high = P2.report()
            report += "\n\n"
            report += "\n\n"

            RPT = open("%s%i-report.txt" % (OUTPUT_PATH, TEST_SERIAL), "w+")
            RPT.write(report)
            RPT.close()

            print(report)

            menu("Test complete", "", "Next Test", "")

            ENTER_STATE = False
        if check_red():
            print("Load Next Mask")
            PASS_VISIBLE = True
            ENTER_STATE = True
            STATE = "light_or_dark"
            i = 0
    else:
        if ENTER_STATE:
            print("Invalid state: %s" % STATE)
            ENTER_STATE = True
