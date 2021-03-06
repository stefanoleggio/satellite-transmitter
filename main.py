import json
import math
import matplotlib.pyplot as plt
import numpy as np
import os

#
# Plotting functions
#

def square_wave_plot(data, T, total_duration, title):
    t = np.arange(0, total_duration, T)
    plt.step(t, data)
    plt.xlabel("n (sample)")
    plt.ylabel("value")
    plt.xticks(t)
    plt.title(title)
    plt.savefig("plots/"+title+".png")
    plt.close()

def iqPlot(values, title, plot_points):
    plt.plot(np.real(values[:plot_points]),np.imag(values[:plot_points]), '.')
    plt.title(title)
    plt.xlabel("Q")
    plt.ylabel("I")
    plt.grid()
    plt.savefig("plots/"+title+".png")
    plt.close()

def plot_prn_and_boc():
    fig, axis = plt.subplots(nrows=2, sharex=True, subplot_kw=dict(frameon=False)) # frameon=False removes frames
    t = np.arange(0, 10, 1)
    axis[0].scatter(t, PRN_SEQUENCE[:10])
    axis[0].set_ylabel("value")
    axis[1].set_xlabel("chip time")
    axis[0].set_xticks(t)
    axis[0].set_title("PRN sequence")

    t = np.arange(0, 10, 0.5)
    axis[1].scatter(t, BOC_SEQUENCE[:20])
    axis[1].set_ylabel("value")
    axis[1].set_xlabel("chip time")
    axis[1].set_xticks(t)
    axis[1].set_title("BOC modulated signal")

    axis[0].grid()
    axis[1].grid()
    fig.savefig("plots/PRN_with_BOC.png")
    plt.close()

#
# Quantizer function
#

def quantize_uniform(x, quant_min=-1.0, quant_max=1.0, quant_level=5):

    x_normalize = (x-quant_min) * (quant_level-1) / (quant_max-quant_min)
    x_normalize[x_normalize > quant_level - 1] = quant_level - 1
    x_normalize[x_normalize < 0] = 0
    x_normalize_quant = np.around(x_normalize)-pow(2,BIT_FOR_IQ-1)

    return x_normalize_quant

#
# Function for simulation of doppler shift
#

def simulate_doppler_shift(ds_duration, input_bits, freq_min, freq_max):

    total_points = ds_duration * F_S

    doppler_shift_vector = []

    max_length = input_bits * PRN_WITH_BOC_LENGHT /(2*CHIP_RATE-freq_max) * F_S

    doppler_shift_vector = np.random.uniform(freq_min,freq_max,math.ceil(max_length/total_points))

    phases_shifts_vector = []

    time_list = np.arange(0, ds_duration, 1/F_S)

    # Phase shift calculation
    for i in range(len(doppler_shift_vector)):
        if(i>0):
            phases_shifts_vector.append(2*math.pi*doppler_shift_vector[i-1]*ds_duration + phases_shifts_vector[i-1])
        else:
            phases_shifts_vector.append(0)


    # Wave generation
    wave_list = []
    for i in range(len(doppler_shift_vector)):
        wave_list = np.concatenate((wave_list,np.cos(2*math.pi*doppler_shift_vector[i]*time_list + phases_shifts_vector[i]) + 1j * np.sin(2*math.pi*doppler_shift_vector[i]*time_list + phases_shifts_vector[i])))
    

    return wave_list, doppler_shift_vector

#
# Function for simulation of path loss
#

def simulate_path_loss(pl_duration, input_bits, val_min, val_max, freq_max):

    total_points = pl_duration * F_S


    path_loss_vector = []

    j = 0

    max_length = input_bits * PRN_WITH_BOC_LENGHT /(2*CHIP_RATE-freq_max) * F_S

    while(j<max_length):
        x = np.random.uniform(val_min,val_max,1)[0]
        i = 0
        while(i<total_points):
            path_loss_vector.append(x)
            i += 1

        j += i

    return path_loss_vector

if __name__ == '__main__':

    if(os.path.exists("output.bin")):
        os.remove("output.bin")

    message = open("message.bin", "rb")
    codes = json.load(open("codes.json", "r"))
    output_file = open("output.bin","ab")

    # PRN sequences already modulated with BOC

    BOC_SEQUENCE = codes['boc_sequence']
    BOC_SEQUENCE_INVERSE = codes['boc_sequence_inverse']
    PRN_SEQUENCE = codes['prn_sequence']
    PRN_SEQUENCE_INVERSE = codes['prn_sequence_inverse']
    PRN_LENGHT = codes['prn_lenght']
    PRN_WITH_BOC_LENGHT = PRN_LENGHT * 2

    plot_prn_and_boc()

    # Chanel costants

    BOLTZMANN_COSTANT = 1.3809649 * pow(10,-23)
    CHIP_RATE = 1.023 * pow(10,6)
    F_S = 4.092*pow(10,6) # Sampling frequency
    BIT_FOR_IQ = 16

    # Channel Parameters

    ds_duration_default = 0.2
    pl_duration_default = 0.1995
    ds_freq_max_default = 5000
    ds_freq_min_default = 2000
    pl_val_min_default = -25
    pl_val_max_default = -20
    snr_default = 20

    print("\n### Satellite transmitter simulator ###\n")
    print("legend: [unit of measure] (default value)\n")

    ds_duration = float(input("Set update period of doppler shift [s] (" + str(ds_duration_default) + "): ") or ds_duration_default) # Set update period of doppler shift (s) 

    pl_duration = float(input("Set update period of path loss [s] (" + str(pl_duration_default) + "): ") or pl_duration_default)

    ds_freq_max = int(input("Set doppler shift max freq [Hz] (" + str(ds_freq_max_default) + "): ") or ds_freq_max_default)

    ds_freq_min = int(input("Set doppler shift min freq [Hz] (" + str(ds_freq_min_default) + "): ") or ds_freq_min_default)

    pl_val_min = float(input("Set path loss gain min value [dB] (" + str(pl_val_min_default) + "): ") or pl_val_min_default)

    pl_val_max = float(input("Set path loss gain max value [dB] (" + str(pl_val_max_default) + "): ") or pl_val_max_default)

    snr =  float(input("Set SNR value [dB] (" + str(snr_default) + "): ") or snr_default)

    N_0 = (pow(10,np.mean([pl_val_min,pl_val_max])/10))/pow(10,snr/10)

    V_SAT = np.sqrt(pow(10,pl_val_max/10)) # Computing the saturation value of the quantizer

    pathLossFlag = input("Insert Path Loss? [Y/N] (Y)")

    if(pathLossFlag.lower() == "y"):
        pathLossFlag = True
    elif(pathLossFlag.lower() == "n"):
        pathLossFlag = False
    else:
        pathLossFlag = True

    awgnFlag = input("Insert AWGN? [Y/N] (Y)")

    if(awgnFlag.lower() == "y"):
        awgnFlag = True
    elif(awgnFlag.lower() == "n"):
        awgnFlag = False
    else:
        awgnFlag = True

    writeOutput = input("Write IQ samples output? [Y/N] (N)")

    if(writeOutput.lower() == "y"):
        writeOutput = True
    elif(writeOutput.lower() == "n"):
        writeOutput = False
    else:
        writeOutput = False

    ## Counting previously the message bits for creating the simulation vectors

    message_tmp = open("message.bin", "rb")
    input_size = 0
    for line in message_tmp.readlines():
        input_size += len(line)
    
    ####

    ds_wave_list, doppler_shift_vector = simulate_doppler_shift(ds_duration, input_size, ds_freq_min, ds_freq_max)

    path_loss_vector = simulate_path_loss(pl_duration, input_size, pow(10, pl_val_min/10), pow(10,pl_val_max/10), ds_freq_max)
 
    bit_counter = 0
    boc_output = []
    current_time = 0
    remainder = 0
    message_bits_to_plot = [] # Buffer for plotting
    messagePlotFlag = True
    bocPlotFlag = True
    prnPlotFlag = True

    while(True):
        
        message_bit = message.read(1)

        message_bits_to_plot.append(message_bit)

        if(len(message_bits_to_plot)>10 and messagePlotFlag):
            square_wave_plot(message_bits_to_plot, 1, len(message_bits_to_plot), "Message")
            messagePlotFlag = False

        boc_sequence = []

        try:
            int(message_bit,2)
        except:
            break

        # Just for plotting: PRN adding
        PRN_sequence = []
        if(int(message_bit,2)):
            PRN_sequence = PRN_SEQUENCE_INVERSE
        else:
            PRN_sequence = PRN_SEQUENCE

        if(prnPlotFlag):
            square_wave_plot(PRN_sequence[:10],1,10,"Message with PRN")
            prnPlotFlag = False

        # PRN and BOC modulation, the BOC(1,1) sequence already contains the PRN

        if(int(message_bit,2)):
            boc_sequence = BOC_SEQUENCE_INVERSE
        else:
            boc_sequence = BOC_SEQUENCE

        if(bocPlotFlag):
            square_wave_plot(boc_sequence[:10],1,10,"Message modulated with Boc(1,1)")
            bocPlotFlag = False

        # Doppler shift implementation

        repetitions = []

        for i in range(len(boc_sequence)):
            index = math.floor(current_time/ds_duration)
            current_time += 1/(2*CHIP_RATE+doppler_shift_vector[index])
            repetitions.append(1/(2*CHIP_RATE+doppler_shift_vector[index])*F_S)

        

        for i in range(len(boc_sequence)):
            remainder += repetitions[i]

            j = 0
            while(j<math.modf(remainder)[1]):
                boc_output.append(boc_sequence[i])
                j+=1
            remainder = math.modf(remainder)[0]


        bit_counter += 1


    iqPlot(boc_output, "IQ samples of the BOC(1,1)", len(boc_output)-1)

    signal = boc_output * ds_wave_list[:len(boc_output)] 

    iqPlot(signal, "IQ samples with Doppler Shift", len(signal)-1)

    # AWGN simulation

    awgn_vector = (np.random.randn(len(signal)) + 1j*np.random.randn(len(signal))) * np.sqrt(N_0/2)


    if(pathLossFlag):

        # Apply Path Loss

        signal = signal * np.sqrt(path_loss_vector[:len(signal)])

        iqPlot(signal, "IQ samples with Doppler Shift and Path Loss", len(signal)-1)
    
    if(awgnFlag):

        # Apply AWGN

        signal = signal + awgn_vector

        iqPlot(signal, "IQ samples with Doppler Shift, Path Loss and AWGN", len(signal)-1)

    plt.scatter(np.arange(0,len(signal[814000:820000])), np.real(signal[814000:820000]))
    plt.title("Real part of the sampled signal\n with Doppler Shift, Path Loss and AWGN")
    plt.xlabel("n (sample)")
    plt.ylabel("amplitude")
    plt.savefig("plots/sampled signal with doppler shift - path loss - awgn.png")
    plt.show()


    if(writeOutput):

        print("\nWriting output...")

        # IQ samples writing

        for signal_bit in signal:
            real_sample = int(quantize_uniform(np.array([np.real(signal_bit)]), -V_SAT, V_SAT,pow(2,BIT_FOR_IQ))[0])
            imag_sample = int(quantize_uniform(np.array([np.imag(signal_bit)]), -V_SAT, V_SAT,pow(2,BIT_FOR_IQ))[0])
            output_file.write(real_sample.to_bytes(2,byteorder='big',signed=True))
            output_file.write(imag_sample.to_bytes(2,byteorder='big',signed=True))
            output_file.flush()