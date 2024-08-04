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


# calculate bpm from bvp values
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
    return np.mean(bpm)


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
    # Ensure sampling frequency is calculated and printed each time update_plot is called
    sampling_rate = get_sampling_frequency(current_file, graph_type)
    print(f"Updated Sampling Frequency for {graph_type}: {sampling_rate}")

    if graph_type == "BVP":
        fig = plot_bvp_values(bvp_values, sampling_rate)
        bpm = calc_bpm(bvp_values, sampling_rate)
        ui.label(f"BVP Graph for {os.path.basename(current_file)}: Average BPM: {bpm:.2f}")
    elif graph_type == "Temperature":
        fig = plot_temp_values(temp_values, sampling_rate)
        ui.label(f"Temperature Graph for {os.path.basename(current_file)}:")
    elif graph_type == "EDA":
        fig = plot_eda_values(eda_values, sampling_rate)
        ui.label(f"EDA Graph for {os.path.basename(current_file)}:")

    ui.plotly(fig).classes("w-full h-100")


# enable dark mode
ui.dark_mode().enable()

# create the main ui elements
ui.upload(on_upload=handle_upload, auto_upload=True).classes("max-w-full").style(
    "color:#888"
)
ui.label("Select Avro File(s)")

# dropdown menu to select the type of graph
graph_dropdown = ui.select(
    options=["BVP", "Temperature", "EDA"],
    value="BVP",
    on_change=update_plot
).classes("w-full")

# start the NiceGUI app
ui.run()