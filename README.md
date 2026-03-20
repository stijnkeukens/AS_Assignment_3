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
|    ├─ intersections.csv                 # Demo files for testing
|    └─ network_AS3.csv                   # Output of components_cleaning.py to use for further modelling
├─ experiment/
|  ├─ all_scenarios.csv                   #
|  ├─ run_metrics.csv
|  ├─ scenarioX.csv                       # Experimental output files of all scenarios separately
|  └─ summary.csv                         # Overview of metrics per scenario
├─ img/
|  ├─ experiments_viz/                    # This file includes all experimental visualizations for the report
|  └─ intersection_viz/                   # This file includes all intersection visualizations for the bonus assignment
├─ model/
|  ├─ Bonus Assignment/
|  |  ├─ gis/                             # This file includes the shapefiles used for the bonus assignment
|  |  ├─ _roads3.csv
|  |  ├─ intersections.csv                # csv file  of all the intersections present in the model
|  |  └─ shapefile exploration.ipynb      # This notebook includes the code for the bonus assignment visualization
|  ├─ ContinuousSpace/
|  |  ├─ simple_continuous_canvas.js 
|  |  └─ SimpleContinuousModule.py
|  ├─ components.py                       
|  ├─ datacleaning.py                     # Data preparation pipeline
|  ├─ model.py                            
|  ├─ model_run.py                        
|  └─ model_viz.py  
├─ notebook/
|  ├─ results.ipynb                       # Here the results plots are generated
|  └─ test.ipynb                          # Here data cleaning is tested
├─ requirements.txt                       # Python dependencies
└─ README.md                              # Project documentation
```

### Format

Most README files for data or software projects are now written in Markdown format, like this document. There are some different flavours, but they are easy to write. See here for more information https://www.markdownguide.org/basic-syntax

Most IDEs can render Markdown files directly.
