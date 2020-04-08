# P.A.T. ppe_analysis_tester

![P.A.T.](/images/pat.jpg)

## Background
During the COVID-19 epidemic the team at the Amherst Makerspace
(https://www.amherstmakerspace.com/) decided to do something useful and produce
masks.(https://www.amherstmakerspace.com/covid-19-response/). Beeing the
collective of geeks we are, we wanted to know how effective the masks produced
are. Enter P.A.T.

## Theory of operation
P.A.T. has 2 primary modes, filter/media test and mask test. In both cases the
simulated lung generates an inhale/exhale cycle while a pressure sensor operates
in a chamber connected to the sumulated lung seperated from the ambient
atmosphere by the filter-meida. In the case of the mask-test there is also a
lux sensor for testing the fit of(opaque) masks.

Samples from the pressure sensor are gathered as the inhale/exhale cycle takes
place and compared against a known profile. The profiles are generated based on
a sequence of test samples. after each cycle the operator is presented with a
grpah showing the profile and where the subject mask performed against that
profile.

![Exmaple profile](/images/profile.png)

### Parts:
* Wig form
* tubing
* 4" PVC ~24" with end-cap for "lung"
* pneumatic piston
* pneumatic valve, I used a pilot operated spring-return single valve
![Valve](/images/5-2_valves_single.jpg)
* 80/20 or suitable frame
* Breadboard/wire.

### Electornic parts:
* Raspberry Pi
    * on the main I2C bus
        * MPLRS pressure sensor: https://www.adafruit.com/product/3965 (inside mask)
        * Light sensor: https://www.adafruit.com/product/439 (inside mask)
        * (Ambient) pressure, Humidity, Temp sensorr:  https://www.adafruit.com/product/2652
* Relay Module: https://americas.rsdelivers.com/product/parallax-inc/27115/single-10a-relay-module/8430834
* 2 buttons.
    * D18 - Red Button
    * D27 - Blue Button
* Powersupply for pneumatic valve.

## Acknowledgement
* Adafruit for approving my post quarantie parts order
* SAU 39 - for allowing us to use the space to help out in this time of need
* The whole Amherst Makerspace crew
* Everyone who contributed money or materials to the mask project.

