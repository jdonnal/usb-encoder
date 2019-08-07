#!/usr/bin/python3

from joule import ReaderModule
from joule.utilities import time_now
import asyncio
from uldaq import get_daq_device_inventory, InterfaceType, ScanStatus, ScanOption, CInScanFlag
from uldaq import CounterMeasurementType, CounterMeasurementMode, CounterEdgeDetection, CounterTickSize
from uldaq import CounterDebounceMode, CounterDebounceTime, CConfigScanFlag, create_int_buffer, DaqDevice
import numpy as np


class MccdaqReader(ReaderModule):
    "Reads input from Mccdaq usbquad08, based on 5 encoders"

    """N.B. this function assumes that the z axis is connected to the 0 and 2 channels,
    the x axis to the 3 channel,
    the y axis to the 1 channel, and the extruder to the 4 channel"""

    async def run(self, parsed_args, output):
        aq_device = None
        ctr_device = None

        descriptor_index = 0
        interface_type = InterfaceType.USB
        low_encoder = 0
        encoder_count = 5
        sample_rate = 1000.0  # 1000 # Hz
        samples_per_channel = 10000  # 10000
        scan_options = ScanOption.CONTINUOUS
        scan_flags = CInScanFlag.DEFAULT

        encoder_type = CounterMeasurementType.ENCODER
        encoder_mode = CounterMeasurementMode.ENCODER_X4
        edge_detection = CounterEdgeDetection.RISING_EDGE
        tick_size = CounterTickSize.TICK_20ns
        debounce_mode = CounterDebounceMode.TRIGGER_AFTER_STABLE
        debounce_time = CounterDebounceTime.DEBOUNCE_7500ns
        config_flags = CConfigScanFlag.DEFAULT
        daq_device = None

        try:
            # Get descriptors for all of the available DAQ devices.
            devices = get_daq_device_inventory(interface_type)
            print(devices)
            number_of_devices = len(devices)
            if number_of_devices == 0:
                raise ValueError('Error: No DAQ devices found')
            # Create the DAQ device object associated with the specified descriptor index.
            daq_device = DaqDevice(devices[descriptor_index])

            # Get the CtrDevice object and verify that it is valid.
            ctr_device = daq_device.get_ctr_device()
            if ctr_device is None:
                raise ValueError('Error: The DAQ device does not support counters')

            # Verify that the specified device supports hardware pacing for counters.
            ctr_info = ctr_device.get_info()
            if not ctr_info.has_pacer():
                raise ValueError('Error: The specified DAQ device does not support hardware paced counter input')

            # Establish a connection to the DAQ device.
            descriptor = daq_device.get_descriptor()
            daq_device.connect()

            # Get the encoder counter channels.
            encoder_counters = get_supported_encoder_counters(ctr_info)
            if len(encoder_counters) == 0:
                raise ValueError('Error: The specified DAQ device does not support encoder channels')

            # Verify that the low_encoder number is valid.
            first_encoder = encoder_counters[0]
            if low_encoder < first_encoder:
                low_encoder = first_encoder

            if low_encoder > first_encoder + len(encoder_counters) - 1:
                low_encoder = first_encoder

            # Verify that the encoder count is valid.
            if encoder_count > len(encoder_counters):
                encoder_count = len(encoder_counters)

            # Set the high_encoder channel.
            high_encoder = low_encoder + encoder_count - 1
            if high_encoder > first_encoder + len(encoder_counters) - 1:
                high_encoder = first_encoder + len(encoder_counters) - 1

            # update the actual number of encoders being used
            encoder_count = high_encoder - low_encoder + 1

            # Clear the counter, and configure the counter as an encoder.
            for encoder in range(low_encoder, high_encoder + 1):
                ctr_device.c_config_scan(encoder, encoder_type, encoder_mode, edge_detection, tick_size, debounce_mode,
                                         debounce_time, config_flags)

            # Allocate a buffer to receive the data.
            data = create_int_buffer(encoder_count, samples_per_channel)

            # Start the scan
            ctr_device.c_in_scan(low_encoder, high_encoder, samples_per_channel, sample_rate, scan_options, scan_flags,
                                 data)

            # prev_samples_per_channel = 0
            # cur_samples_per_channel = 0
            prev_index = 0

            XVect = []
            YVect = []
            ZVect = []
            AllVect = []
            startX = 0.0
            startY = 0.0
            startZ = 0.0
            # newZ = []
            prev_index = 0

            start_time = time_now()
            cur_time = start_time + 1
            while not self.stop_requested:
                status, transfer_status = ctr_device.get_scan_status()
                # not sure if can await the above line
                index = transfer_status.current_index
                # print(index)

                # edge starting condition
                if index == -1:
                    AllVect = [0.0, 0.0, 0.0, 0.0, 0.0]

                # normal condition
                else:
                    # has not looped around
                    if prev_index < index:
                        AllVect = data[prev_index:index]
                    # has wrapped around
                    else:
                        AllVect = data[prev_index:] + data[0:index]
                    prev_index = index
                # print(AllVect)
                XVect = AllVect[3::5]
                YVect = AllVect[1::5]
                Z1Vect = AllVect[0::5]
                Z2Vect = AllVect[2::5]

                end_time = cur_time + (len(XVect) - 1) * 1e3  # cur_time is in us

                [XVect, startX] = processX(XVect, startX)
                [YVect, startY] = processY(YVect, startY)
                [ZVect, startZ] = processZ(Z1Vect, Z2Vect, startZ, cur_time, end_time)

                Xarray = np.array(XVect)
                Yarray = np.array(YVect)
                Zarray = np.array(ZVect)

                Xarray = np.vstack(Xarray)
                Yarray = np.vstack(Yarray)
                Zarray = np.vstack(Zarray)

                time_array = np.linspace(cur_time, end_time, len(XVect))

                time_array = np.vstack(time_array)

                # print("before all output")
                All_Output = np.hstack((time_array, Xarray, Yarray, Zarray))
                # print("after all output")
                # print(All_Output)
                await output.write(np.array(All_Output))
                # print("after writing")
                # print(len(YVect))
                # for i in range(len(YVect)):
                # print(str(YVect[i])+ "\t"+str(newY[i]))
                await asyncio.sleep(1)
                cur_time = end_time + 1e3
                if status != ScanStatus.RUNNING:
                    break

                # except (ValueError, NameError, SyntaxError):
                # break
                # print("next while loop cycle")

        except ValueError as e:
            print(str(e))
        except Exception as e:
            raise e

        finally:
            if daq_device:
                if ctr_device:
                    ctr_device.scan_stop()
                if daq_device.is_connected():
                    daq_device.disconnect()
                    daq_device.release()


def get_supported_encoder_counters(ctr_info):
    encoders = []

    number_of_counters = ctr_info.get_num_ctrs()
    for counter_number in range(number_of_counters):
        measurement_types = ctr_info.get_measurement_types(counter_number)

        if CounterMeasurementType.ENCODER in measurement_types:
            encoders.append(counter_number)
    return encoders


"""for encoder_index in range(encoder_count):
                    message = str('chan =' + str((encoder_index + low_encoder)) + ': '+str('{:.6f}'.format(data[index +encoder_index])))
                    curX=data[index+3] * (100.0/25726.0)
                    curY=data[index+1] * (100.0/25725.0)
                    curZ=(data[index]+ data[index+2])/2 * (10.0/40961)

                    #if wraparound
                    if abs(prevX-curX)>100:
                        if prevX<curX:
                            trueX = trueX-(Xthresh-curX+prevX)
                        else:
                            trueX = trueX + (Xthresh-prevX+curX)
                    #no wraparound
                    else:
                        trueX = trueX + (curX-prevX)
                    if abs(prevY-curY)>100:
                        if prevY<curY:
                            trueY = trueY-(Ythresh-curY+prevY)
                        else:
                            trueY = trueY + (Ythresh-prevY+curY)
                    else:
                        trueY = trueY + (curY-prevY)
                    if abs(prevZ-curZ)>10:
                        if prevZ<curZ:
                            trueZ = trueZ-(Zthresh-curZ+prevX)
                        else:
                            trueZ = trueZ + (Zthresh-prevZ+curZ)
                    else:
                        trueZ = trueZ + (curZ-prevZ)
                    prevX = curX
                    prevY = curY
                    prevZ = curZ
                    await output.write(np.array([[time_now(),trueX,trueY,trueZ, index]]))"""
# wrap-around variables
"""trueX = 0.0
trueY = 0.0
trueZ = 0.0
            
prevX = 0.0
prevY = 0.0
prevZ= 0.0"""

Xthresh = 254.8
Ythresh = 254.8
Zthresh = 16.0


def processX(X, startX):
    prevX = startX
    trueX = prevX
    trueXVect = []
    for x in X:
        curX = x * (100.0 / 25726.0)  # convert to mm
        if abs(prevX - curX) > 200:  # if wraparound
            if prevX < curX:
                trueX = trueX - (Xthresh - curX + prevX)
            else:
                trueX = trueX + (Xthresh - prevX + curX)
        # no wraparound
        else:
            trueX = trueX + (curX - prevX)
        trueXVect.append(trueX)
        prevX = curX
        if len(trueXVect) == 0:
            trueXVect = [trueX]
    return [trueXVect, trueXVect[len(trueXVect) - 1]]


def processY(Y, startY):
    # print("start method")
    prevY = startY
    trueY = prevY
    trueYVect = []
    # print("after array created")
    for y in Y:
        curY = y * (100.0 / 25725.0)
        if abs(prevY - curY) > 200:
            if prevY < curY:
                trueY = trueY - (Ythresh - curY + prevY)
            else:
                trueY = trueY + (Ythresh - prevY + curY)
        else:
            trueY = trueY + (curY - prevY)
        # trueYVect.append(trueY)
        trueYVect.append(trueY)
        prevY = curY
    if len(trueYVect) == 0:
        trueYVect = [trueY]
    # print(len(trueYVect))
    return [trueYVect, trueYVect[len(trueYVect) - 1]]


def processZ(Z1, Z2, startZ, ctime, etime):
    Z = []
    for i in range(len(Z1)):
        if abs(Z1[i] - Z2[i]) > 60000:
            Z.append(0)
        else:
            Z.append((Z1[i] + Z2[i]) / 2)
    prevZ = startZ % 16.0
    trueZ = startZ
    trueZVect = []
    for i in range(0, len(Z)):
        z = Z[i]
        curZ = z * (10.0 / 40961.0)
        if abs(prevZ - curZ) > 7:
            if prevZ < curZ:
                print("wrapped, prevZ<curZ " + str(time_now()), flush=True)

                trueZ = trueZ - (Zthresh - curZ + prevZ)
            else:
                print("Wrapped, prevZ>curZ " + str(time_now()), flush=True)

                trueZ = trueZ + (Zthresh - prevZ + curZ)
            print(Z1[i])
            print(Z2[i])
            print(prevZ)
            print(curZ)
            print(ctime)
            print(etime)
        else:
            trueZ = trueZ + (curZ - prevZ)
        trueZVect.append(trueZ)
        prevZ = curZ
    if len(trueZVect) == 0:
        trueZVect = [trueZ]
    return [trueZVect, trueZVect[len(trueZVect) - 1]]


def main():
    m = MccdaqReader()
    m.start()


if __name__ == "__main__":
    main()
