from nicegui import ui
from nicegui.events import UploadEventArguments
from fastavro import reader as avroreader
import os
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
import plotly.graph_objects as go

# get avro records
def getRecords(avroPath):
    with open(avroPath, "rb") as f:
        records = [r for r in avroreader(f)]
    return records

# get bvp values from avro file
def get_bvp_values(avroPath: str):
    users = getRecords(avroPath)
    bvp_values = users[0]["rawData"]["bvp"]["values"]
    return bvp_values

# get temp values from avro file
def get_temp_values(avroPath: str):
    users = getRecords(avroPath)
    temp = users[0]['rawData']['temperature']['values']
    return temp

# get eda values from avro file
def get_eda_values(avroPath: str):
    users = getRecords(avroPath)
    eda = users[0]['rawData']['eda']['values']
    return eda

# get sampling frequency from avro file
def get_sampling_frequency(avroPath: str, data_type: str):
    users = getRecords(avroPath)
    if data_type == "BVP":
        sampling_frequency = users[0]["rawData"]["bvp"]["samplingFrequency"]
    elif data_type == "Temperature":
        sampling_frequency = users[0]["rawData"]["temperature"]["samplingFrequency"]
    elif data_type == "EDA":
        sampling_frequency = users[0]["rawData"]["eda"]["samplingFrequency"]
    return sampling_frequency

# plot bvp values over time in seconds
def plot_bvp_values(bvp_values, sampling_rate):
    time_values = [i / sampling_rate for i in range(len(bvp_values))]
    normal_time = [
        time_values[i]
        for i in range(len(bvp_values))
        if bvp_values[i] < -0.02 or bvp_values[i] > 0.02
    ]
    normal_bvp = [
        bvp_values[i]
        for i in range(len(bvp_values))
        if bvp_values[i] < -0.02 or bvp_values[i] > 0.02
    ]
    lost_time = [
        time_values[i] for i in range(len(bvp_values)) if -0.02 <= bvp_values[i] <= 0.02
    ]
    lost_bvp = [
        bvp_values[i] for i in range(len(bvp_values)) if -0.02 <= bvp_values[i] <= 0.02
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=normal_time,
            y=normal_bvp,
            mode="lines",
            name="BVP Values",
            line=dict(color="blue"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=lost_time,
            y=lost_bvp,
            mode="lines",
            name="Lost Signal",
            line=dict(color="red"),
        )
    )
    fig.update_layout(
        title="BVP Values Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="BVP Value",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig

# plot temperature values over time in seconds
def plot_temp_values(temp_values, sampling_rate):
    time_values = [i / sampling_rate for i in range(len(temp_values))]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=temp_values,
            mode="lines",
            name="Temperature Values",
            line=dict(color="green"),
        )
    )
    fig.update_layout(
        title="Temperature Values Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Temperature Value",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig

# plot eda values over time in seconds
def plot_eda_values(eda_values, sampling_rate):
    time_values = [i / sampling_rate for i in range(len(eda_values))]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=eda_values,
            mode="lines",
            name="EDA Values",
            line=dict(color="purple"),
        )
    )
    fig.update_layout(
        title="EDA Values Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="EDA Value",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig

#TODO
# calculate bpm from bvp values and return bpm values over time (need work)
def calc_bpm(bvp_values, sampling_rate):
    def butter_bandpass(lowcut, highcut, fs, order=5):
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype="band")
        return b, a

    def bandpass_filter(data, lowcut, highcut, fs, order=5):
        b, a = butter_bandpass(lowcut, highcut, fs, order=order)
        y = filtfilt(b, a, data)
        return y

    filtered_bvp = bandpass_filter(bvp_values, 0.5, 5.0, sampling_rate)
    peaks, _ = find_peaks(filtered_bvp, distance=sampling_rate / 2)
    peak_intervals = np.diff(peaks) / sampling_rate
    bpm = 60 / peak_intervals
    time_values = [peaks[i] / (sampling_rate * 60) for i in range(1, len(peaks))]  # Convert to minutes
    return bpm, time_values

#TODO
# plot bpm values over time (needs work)
def plot_bpm_values(bpm_values, time_values):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_values,
            y=bpm_values,
            mode="lines",
            name="BPM Values",
            line=dict(color="orange"),
        )
    )
    fig.update_layout(
        title="BPM Values Over Time",
        xaxis_title="Time (minutes)",
        yaxis_title="BPM",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig

#TODO
# calculate statistics for values (need work)
def calc_statistics(values):
    # Filter out low signal values for BVP
    if graph_dropdown.value == "BVP":
        values = [v for v in values if v < -0.02 or v > 0.02]

    mean_val = np.mean(values)
    median_val = np.median(values)
    std_val = np.std(values)
    return mean_val, median_val, std_val

# handle file upload event
def handle_upload(event: UploadEventArguments):
    tmp_dir = "/tmp"
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    file_path = os.path.join(tmp_dir, event.name)
    with open(file_path, "wb") as f:
        f.write(event.content.read())

    global bvp_values, temp_values, eda_values, sampling_rate, current_file
    bvp_values = get_bvp_values(file_path)
    temp_values = get_temp_values(file_path)
    eda_values = get_eda_values(file_path)
    current_file = file_path
    graph_type = graph_dropdown.value
    sampling_rate = get_sampling_frequency(file_path, graph_type)

    update_plot()

# update plot based on selected graph type
def update_plot():
    global sampling_rate

    graph_type = graph_dropdown.value
    # print sampling frequency for each plot
    sampling_rate = get_sampling_frequency(current_file, graph_type)
    print(f"Updated Sampling Frequency for {graph_type}: {sampling_rate}")

    if graph_type == "BVP":
        fig = plot_bvp_values(bvp_values, sampling_rate)
        bpm_values, time_values = calc_bpm(bvp_values, sampling_rate)
        fig_bpm = plot_bpm_values(bpm_values, time_values)
        mean_bvp, median_bvp, std_bvp = calc_statistics(bvp_values)
        ui.label(f"BVP Graph for {os.path.basename(current_file)}: Mean: {mean_bvp:.2f}, Median: {median_bvp:.2f}, Std: {std_bvp:.2f}")
        ui.plotly(fig_bpm).classes("w-full h-100")
    elif graph_type == "Temperature":
        fig = plot_temp_values(temp_values, sampling_rate)
        mean_temp, median_temp, std_temp = calc_statistics(temp_values)
        ui.label(f"Temperature Graph for {os.path.basename(current_file)}: Mean: {mean_temp:.2f}, Median: {median_temp:.2f}, Std: {std_temp:.2f}")
    elif graph_type == "EDA":
        fig = plot_eda_values(eda_values, sampling_rate)
        mean_eda, median_eda, std_eda = calc_statistics(eda_values)
        ui.label(f"EDA Graph for {os.path.basename(current_file)}: Mean: {mean_eda:.2f}, Median: {median_eda:.2f}, Std: {std_eda:.2f}")

    ui.plotly(fig).classes("w-full h-100")

# enable dark mode
ui.dark_mode().enable()

# create the main ui elements
with ui.column().classes("w-full") as main_layout:
    ui.label("Avro Visualization").classes("text-2xl font-bold mb-2")
    ui.label("Select an Avro file and choose the type of data you want to visualize.").classes("mb-4")
    ui.label("Select Avro File(s)").classes("mb-2")

    with ui.row().classes("items-center mb-4"):
        ui.upload(on_upload=handle_upload, auto_upload=True).classes("max-w-full").style("color:#888")
        graph_dropdown = ui.select(
            options=["BVP", "Temperature", "EDA"],
            value="BVP",
            on_change=update_plot
        ).classes("w-full ml-4")

# start the NiceGUI app
ui.run()
