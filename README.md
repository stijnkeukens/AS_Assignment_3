# Example README File

Created by: EPA133a Group 11

|Group Number|11|
|:---:|:-------:|
| Jonathan Vermeulen | 5144434 |
| Stijn Keukens | 5072700 |
| Scipio Bruijn | 5868181 |
| Evi de Kok | 5878179 |
|Annette Dorresteijn | 5868629 |

## Introduction

Every project should have a README file to help a first-time user understand what it is about and how they might be able to use it. This file is where you (as a group) shall provide the information needed by the TAs to evaluate and grade your work.

If you are looking for information about the Demo model of Assignment 3, navigate to the [model/README.md](model/README.md) in the [model](model) directory. Have **fun** modeling in Python!

## How to Use

### Project Preparation
1. Create and activate a virtual environment (`conda` or `venv`).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running
Run the model from `model/model_run.py` (from the project root):

```bash
python model/model_run.py
```

- Set `SINGLE_RUN = True` to run one simulation.
- Output is printed saved to `experiment/model_results.csv`.
- Set `SINGLE_RUN = False` to run the full scenario analysis (Scenarios 0-8, 10 replications each).
- Output is saved to `experiment/scenario0.csv` through `scenario8.csv`.

To visualize the model, run `model/model_viz.py`.
This runs a single simulation with adjustable bridge breakdown probabilities.

## Project Structure

## Project Structure
```
EPA133a-G11-A2/
├─ data/
|  ├─ raw/
|  | ├─ _roads3.csv                       # Original dataset roads
|  | └─ BMMS_overview.xlsx                # Original dataset bridges
|  └─ processed/
|    ├─ demo-1.csv                        # Demo files for testing
|    ├─ demo-2.csv
|    ├─ demo-3.csv
|    └─ N1_AS2.csv                        # Output of components_cleaning.py to use for further modelling
├─ experiment/
|  ├─ result_scan.ipynb                   # Analyzing and visualizing data results
|  ├─ scenario0.csv                       # Experimental output files
|  ├─ scenario1.csv
|  ├─ scenario2.csv
|  ├─ scenario3.csv
|  ├─ scenario4.csv
|  ├─ scenario5.csv
|  ├─ scenario6.csv
|  ├─ scenario7.csv
|  └─ scenario8.csv
├─ img/
|  └─ total_wait_duration_per_scenario.png
├─ model/
|  ├─ ContinuousSpace/
|  |  ├─ simple_continuous_canvas.js 
|  |  └─ SimpleContinuousModule.py
|  ├─ components.py                       # Here we added components for delay and bridge selection functions
|  ├─ components_cleaning.py              # Data preparation pipeline
|  ├─ model.py                            # Added data collection elements and bridge break-down probabilities
|  ├─ model_run.py                        # Added data collection elements and scenario analysis option
|  ├─ model_viz.py                        # Added sliders in visualization for data exploration
|  └─ 
├─ requirements.txt                       # Python dependencies
└─ README.md                              # Project documentation
```

### Format

Most README files for data or software projects are now written in Markdown format, like this document. There are some different flavours, but they are easy to write. See here for more information https://www.markdownguide.org/basic-syntax

Most IDEs can render Markdown files directly.
