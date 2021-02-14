import numpy as np
from labjack import ljm
# eventually, add another process to send over raw photometry data
# for saving

def stream(handle, gui_info, plot_widgets):
    scan_list = gui_info.scan_list
    n_ports = len(scan_list)
    new_scan_rate = ljm.eStreamStart(handle, gui_info.scans_per_read,
                                     n_ports, scan_list, gui_info.scan_rate)

    sine_plot = plot_widgets['sine']
    signal_plot = plot_widgets['signal']
    # TODO: make smarter, and/or conditional
    while True:
        # don't need the other information for now
        data = ljm.eStreamRead(handle)[0]
        data = np.array(data).reshape(-1, n_ports)
        # first 2, plot in the sine plot
        sine_plot.clear()
        sine_plot.plot(y=data[:, 0])
        sine_plot.plot(y=data[:, 1])

        # next 2, plot in the signal plot
        signal_plot.clear()
        signal_plot.plot(y=data[:, 2])
        signal_plot.plot(y=data[:, 3])