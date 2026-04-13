# Phase 2 MVP Progress Report

## Grow A Garden: AI Garden Planning Assistant

---

## 1. Objective and Current MVP Definition

### Minimum Viable Product

Our MVP for this project is a working system that takes a users personalized conditions and creates crop recommendations and a gardening schedule.

1. Input:

   * USDA hardiness zone or location
   * current date or season
   * available garden space
   * sunlight and watering preference

2. Output:

   * crop recommendations suited to their conditions
   * a structured weekly watering and planting schedule
   * explanations for why those recommendations were made

---

## 2. What Has Been Built So Far

At this stage, we have developed two working prototype systems that together demonstrate our MVP progress.

### A. Recommendation-Focused System (Primary Demo)

This system generates crop recommendations based on user inputs such as zone, sunlight, and watering preferences.

Capabilities:

* Uses a small, partially structured dataset and prompt-based logic
* Filters crops by approximate seasonal planting windows
* Matches crops to user constraints (sun, water, timing)
* Outputs recommendations with explanations

Limitations:

* Does not yet reliably pull from structured datasets at runtime
* Limited crop dataset  leads to more generic outputs
* Does not provide specific watering plan

This is our primary MVP feature because it directly addresses the objective of the project to provide recommendations, and it is more user friendly than the second prototype

---

### B. Scheduling-Focused System (Secondary Prototype)

While this system still provides plant recommendations, the main focus of this prototype is to show how we would pull from datasets and generate an 8-week gardening schedule.

Capabilities:

* Uses structured crop datasets
* Creates weekly planting and watering tasks
* Estimates irrigation needs
* Outputs structured schedules (tables, CSV, markdown)

This prototype demonstrates stronger use of datasets, but is currently less refined in usability and presentation.

---

### C. Data and Knowledge Base

We assembled an initial dataset including:

* USDA hardiness zone data
* plant growing seasons and temperature ranges
* watering requirements
* spacing and time-to-maturity information
* public gardening datasets (e.g., Kaggle)

---

### D. Workflow

The current system pipeline:

1. Load and preprocess crop data (used mostly for second prototype)
2. Interpret user inputs (zone, date, constraints)
3. Generate recommendations
4. Generate a schedule based on selected crops
5. Output results as tables and markdown summaries

---

## 3. Technical Bottlenecks

* **Limited dataset integration**: The first prototype does not fully utilize structured datasets
* **Limited dataset scope**: Most data is sourced from the United States and currently the datasets only have select crops, reducing the scope of the system
* **Lack of real-time data integration**: The system does not take into account current weather trends and changes in climate over time

---

## 4. What Does Not Work Yet

* Recommendation system produces outputs that can feel generic
* The first prototype does not pull from outside data, which limits the information that it can give
* Scheduling output is more functional but not visually refined
* No unified system combining recommendation + scheduling

---

## 5. Key Areas for Improvement

* Combine the two demo systems into a single workflow
* Improve the layout and readability of the scheduling output
* Expand dataset coverage beyond U.S.-based data
* Improve explanation quality to better reflect user-specific conditions

---

## 6. Evidence of Progress

We successfully built:

* A recommendation prototype
* A scheduling system
* A reproducible demo in Google Colab
* Exportable outputs (CSV and markdown)

---

## 7. Phase 3 Plans

### Planned Next Steps

1. Integrate structured datasets directly into the recommendation system

2. Combine recommendation + scheduling into one system

3. Expand and improve the dataset:

   * add more crops and regions
   * clean and standardize data fields

4. Add a retrieval or lookup layer to reduce generic outputs

5. Improve input handling and user personalization

6. Build a simple user interface (Colab, CLI, or web app)

