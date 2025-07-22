# 📈 Candlestick Labelling Tool

I originally built this tool as a simple helper application for a personal machine learning project. Hence the name. I needed a way to quickly visualize and label financial data without relying on slow, web-based charting libraries or bloated trading platforms. As I added features, it evolved into something more: a fast, local, and highly hackable tool that I think could be genuinely useful for a niche of developers, analysts, and ML practitioners.

This is an open-source tool, built by a developer for developers. It's designed to be tinkered with.

<p align="center">
  <!-- 🚀 YOUR NAVIGATION GIF LINK GOES HERE -->
  <img src="https://i.imgur.com/WUc6M7G.gif" alt="Chart Navigation Demo" width="800">
</p>

---
> **Heads-Up:** The application requires data to be in the `.parquet` format with the specific columns listed in the "Preparing Your Data" section below.
---

## The Philosophy

This tool was built with a few core principles in mind:

*   **Fast & Responsive:** I was tired of tools that would choke on a full month of 1-minute data. The rendering core is built directly on **OpenGL**, so it can handle large datasets with buttery-smooth panning and zooming.
*   **Local & Private:** This is not a web app. It runs entirely on your machine. Your data, API keys (if you add them), and labels never leave your computer. There is no cloud backend, no telemetry, no nonsense.
*   **Customizable:** Your chart, your rules. I exposed as many style settings as possible through a simple preferences dialog. Change colors, line styles, and layout—the tool will remember your choices.
*   **Open & Hackable:** This isn't a black box. The code is organized to be understood and extended. If you want to add a new indicator, a different drawing tool, or connect it to a live data source, you can.

## Key Features

*   **Hardware-Accelerated Rendering:** Uses OpenGL VBOs to draw thousands of candles without breaking a sweat.
*   **Tweak Every Detail:** A comprehensive preferences dialog lets you control the appearance of candles, wicks, volume bars, grid lines, and the background. See it in action:
    ![Preferences Demo](https://i.imgur.com/mxCpkLJ.gif)
*   **Your Data, Your Machine:** Loads data from local Parquet files. The only limit to the dataset size is your machine's RAM.
*   **Intuitive Navigation:** Smooth panning (right-click drag) and cursor-centric zooming (mouse wheel).
*   **Modern & Clean UI:** A thoughtfully designed dark theme that's easy on the eyes during long sessions.

## Getting Started

### Prerequisites

*   Python 3.11 or newer (3.8 should work. I used 3.11 and didn't try 3.8 but I don't see why not)
*   `pip` and `venv`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/shaanatwal/module_regime_base_labeller.git
    cd your-repository-name
    ```

2.  **Create and activate a virtual environment:**
    *   **Linux/macOS:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    Note: I didn't install from requirements so you might have other dependencies to install. 

4.  **Run the application:**
    ```bash
    python main.py
    ```
    Personally I ran it with Python 3.11

## How to Use It

### Preparing Your Data

The tool reads financial data from **`.parquet`** files. This format is fast and efficient. Your Parquet file **must** have the following columns to be loaded correctly:

| Column Name | Data Type          | Description                                |
|-------------|--------------------|--------------------------------------------|
| `t`         | `datetime64[ns]`   | The timestamp for the start of the candle. |
| `o`         | `float64` / `float32`| The opening price.                           |
| `h`         | `float64` / `float32`| The highest price.                         |
| `l`         | `float64` / `float32`| The lowest price.                          |
| `c`         | `float64` / `float32`| The closing price.                           |
| `v`         | `int64` / `float64`  | The volume.                                |

### A Note on File Naming

This is entirely optional, but it's a quality-of-life feature I built for my own workflow. To get a nice, descriptive title in the app window, you can name your files like this:

`TICKER_TIMEFRAME_OHLCV_YEAR_MONTH.parquet`

For example, `AAPL_1h_OHLCV_2023_10.parquet` will be automatically displayed as `AAPL (1 Hour) - October 2023`.

If you don't follow this convention, it's no big deal! The tool will still work perfectly, it just won't be able to generate as pretty of a title.

## A Tool for Tinkering & Contributing

This tool was born from a personal need, and it's designed to be extended by others with their own unique needs. The codebase is deliberately modular. If you want to add a feature, here's where you might start:

*   **Want to add a new indicator (like an SMA or EMA)?**
    *   You'd modify `data_loader.py` to calculate it and add it as a column to the DataFrame.
    *   Then, you'd create a new VBO-based line renderer in `chart_renderers.py` to draw it.
*   **Want to add a new drawing tool (like trend lines)?**
    *   You'd add a new `ChartMode` to `chart_enums.py`.
    *   Then, you'd handle the mouse events for drawing in `candle_widget.py`.
*   **Want to connect to a live data source?**
    *   You could build a new worker in `main.py` to stream data and append it to the `ChartState`'s DataFrame.

The structure is there. Feel free to fork it, break it, and make it your own. If you build something cool, I'd love to see a pull request!

## Project Structure

*   `main.py`: The application entry point. Puts all the pieces together.
*   `candle_widget.py`: The heart of the app. An `QOpenGLWidget` that handles rendering and user input.
*   `chart_renderers.py`: Where the low-level graphics magic happens. Contains classes for drawing candles, volume, and overlays.
*   `chart_state.py`: The "single source of truth" for what the chart is currently displaying.
*   `style_manager.py`: A simple wrapper around `QSettings` to save and load your preferences.
*   `data_loader.py`: The first stop for your data. It loads, cleans, and prepares the `.parquet` file.

## Incomplete Features

*   As this project was literally created by myself to be modded a bit for my own specific use cases, there are a few features
    I initally planned on adding but didn't finish (such as the drawing brush, and other greyed out buttons). Generally, I found
    this to be a solid month-by-month parquet candlestick viewer so thought to open source it here. Feel free to do whatever you want
    to it to better fit your needs. 


## License

This project is licensed under the MIT License. See the `LICENSE` file for details. Do with it what you will.
