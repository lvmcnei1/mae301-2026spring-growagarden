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

   * crop recommendations for user's specific conditions
   * an 8 week watering and planting schedule
   * explanations for recommendations made

---

## 2. What Has Been Built So Far

At this stage, we have developed two working prototype systems that together demonstrate our MVP progress.

### A. Recommendation-Focused System (Primary Demo)

This system generates crop recommendations based on user inputs such as zone, sunlight, and watering preferences.

Technical Approach:
The recommendation system is a command-line chatbot that uses a small structured dataset of plants. Each plant has attributes such as preferred season, sunlight, water needs, and space requirements. The system collects a user profile (location, month, sun, water, etc.) and converts it into conditions like season and climate.

It then calculates a suitability score for each plant by comparing plant attributes to user inputs. Based on this score, it generates personalized recommendations along with explanations and care guidance. This ensures outputs are consistent and based on structured data rather than purely generic responses.

Capabilities:

* Uses a small internal structured dataset
* Filters crops by approximate seasonal planting windows
* Matches crops to user constraints (sun, water, timing)
* Outputs top recommendations with explanations

Limitations:

* Does not yet reliably pull from structured datasets at runtime
* Limited crop dataset and generic results
* Does not provide specific watering plan

This is our primary MVP feature because it directly addresses the objective of the project to provide recommendations, and it is more user friendly than the second prototype

---

### B. Scheduling-Focused System (Secondary Prototype)

While this system still provides plant recommendations, the main focus of this prototype is to show how we would pull from datasets and generate an 8-week gardening schedule.

Technical Approach:
This system is a Colab-based pipeline that loads plant datasets and generates an 8-week gardening plan. It takes inputs such as date, zone, garden size, sun hours, and watering preference.

The system processes structured crop data and produces recommendations along with a weekly planting and watering schedule. Outputs are saved as tables (CSV) and markdown summaries, making them easy to review and reproduce.

Capabilities:

* Integrates structured crop datasets
* Creates top recommended plants with actionable steps
* Estimates irrigation needs per area and per plant
* Outputs structured 8 week planting and watering schedules as a table
* Personalized results based on many different factors and creates schedule that simplifies the user's role

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

* **Limited dataset integration**: The main technical bottleneck is integrating structured datasets into the recommendation system while maintaining flexibility in generated outputs.
* **Limited dataset scope**: Most data is sourced from the United States and currently the datasets only have select crops, reducing the scope of the system
* **Lack of real-time data integration**: The system does not take into account current weather trends and changes in climate over time

---
## 4. Baseline Comparison

A general-purpose AI system can provide gardening advice, but outputs are often generic and not tied to structured datasets.

Our system improves on this by:
* using structured agricultural data
* enforcing user-specific constraints
* generating consistent schedules instead of general advice

---
  
## 5. What Does Not Work Yet

* Recommendation system produces outputs that can feel generic
* The first prototype does not pull from outside data, which limits the information that it can give
* Scheduling output is more functional but not visually refined
* No unified system combining recommendation + scheduling

---

## 6. Key Areas for Improvement

* Combine the two demo systems into a single workflow
* Improve the layout and readability of the scheduling output
* Expand dataset coverage beyond U.S.-based data
* Improve explanation quality to better reflect user-specific conditions

---

## 7. Evidence of Progress

We successfully built the following, with demos and datasets used located in the github:

* A recommendation prototype
* A scheduling system

Example:

Input:
Zone 9b, April, 8 hours sun, medium watering

Output:
- Tomatoes
- Peppers
- Basil

Schedule excerpt:
Week 1: Plant tomatoes, water 3x/week
Week 2: Maintain watering
Week 6–8: Expected harvest window

Full outputs are available in the GitHub demo.

---

## 8. Phase 3 Plans

### Planned Next Steps

1. Integrate structured datasets directly into the recommendation system

2. Combine recommendation + scheduling into one system

3. Expand and improve the dataset:

   * add more crops and regions
   * clean and standardize data fields

4. Add a retrieval or lookup layer to reduce generic outputs

5. Improve input handling and user personalization

6. Build a simple user interface (Colab, CLI, or web app)

