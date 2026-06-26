# RippleGUItester: Change-Aware Exploratory Testing

RippleGUItester is a **change-driven exploratory GUI-Level testing system**.  
It treats a code change as the epicenter of a *ripple effect* and systematically explores its broader, user-visible impacts through the graphical user interface (GUI).

---

# Part I: Getting Started Guide

This guide provides a quick validation of the artifact setup in approximately 30 minutes.

## Installation

RippleGUItester uses a Visual Studio Code Dev Container to set up and run the project environment. The Dev Container installs the required Python dependencies and prepares the development environment automatically. See `.devcontainer/devcontainer.json` and `.devcontainer/postCreateCommand.sh`.

To install and run RippleGUItester, follow these steps:

1. Install Visual Studio Code and the **Dev Containers** extension.

2. Open RippleGUItester in Visual Studio Code:

   ```bash
   code <main_dir_of_this_project>
   ```

3. Reopen the project in the Dev Container:

   Open the Command Palette:

   - Windows/Linux: `Ctrl + Shift + P`
   - macOS: `Cmd + Shift + P`

   Then select:

   `Dev Containers: Rebuild and Reopen in Container`

4. **Configure API Keys** (Optional):

   API keys are **not required** for the standard artifact evaluation. You can use the provided pre-computed outputs to reproduce the reported results.

   API keys are only needed if you want to run the full RippleGUItester pipeline. To do so, create two token files in the project root:

   Create two token files in the project root with your API keys:

   ```bash
   # Create .anthropic_token file with your Anthropic API key
   echo "sk-ant-api03-xxxxx..." > .anthropic_token
   ```
   
   ```bash
   # Create .openai_token file with your OpenAI API key
   echo "sk-proj-xxxxx..." > .openai_token
   ```

---

## Data Download

Download and extract the data:

This creates a `data/` directory containing the Scenario Knowledge Base (SKB) and pull requests for testing.

```bash
wget https://github.com/SuYanqi/RippleGUItester/releases/download/data/data.zip
unzip data.zip
```


Download the evaluation results:

This creates an `output/` directory containing labeled evaluation results and analysis summaries.

```bash
wget https://github.com/SuYanqi/RippleGUItester/releases/download/data/output.zip
unzip output.zip
```

## Quick Validation

Verify the setup by running evaluation scripts:

```bash
# Reproduce RQ3 (Bug Distribution - generates Figure 8)
python -m scripts.evaluation.calculate_recall_on_known_bugs
```

```bash
# Reproduce RQ4 (Overhead breakdown - generates Figure 9)
python -m scripts.evaluation.calculate_overhead_breakdown
```

Expected output: Figures matching the paper's reported results.

---

# Part II: Step-by-Step Instructions

## Running RippleGUItester

### 1. Create Vector Stores (One-time setup)

Choose a repository and create vector stores for the Scenario Knowledge Base:

**Clear vector stores** (if needed):
```bash
python -m scripts.preparation.clear_vector_stores --repo Zettlr
```

**Create vector stores**:
```bash
python -m scripts.preparation.create_vector_stores --repo Zettlr
```

⚠️ **Quick Validation Tip:** This process is time-consuming (but only needs to run once per repository). For a quick validation of the pipeline, you can proceed to Step 2 once `data/{RepoName}/vector_store_ids.json` is created, without waiting for all vector stores to complete.

### 2. Run Testing

```bash
# Run a specific PR number
python -m scripts.execution.app --repo Zettlr --pr 5976
```

```bash
# Run all PRs for a repository
python -m scripts.execution.app --repo Zettlr
```

⚠️ **Quick Validation Tip:** This process is expensive and time-consuming. Averages are **$5.996 and 54.8 minutes per PR**. Each PR generates and executes multiple test scenarios stored in numbered folders (0, 1, 2, ...). For a quick validation, you can proceed to Step 3 once the first test scenario (folder `0`) completes, without waiting for all scenarios to finish.

### 3. Post-Process Bug Reports (Optional)

After test execution, you can post-process the detected bugs to filter out false positives:

```bash
# Post-process bugs for a specific PR
python -m scripts.execution.post_process_bug_reports --repo Zettlr --pr 5976
```

```bash
# Process all PRs for a repository
python -m scripts.execution.post_process_bug_reports --repo Zettlr
```

### 4. Understanding Output Structure

After running RippleGUItester, results are saved in the `output/` directory with the following structure:

```
output/{Repository}/output/{PR_ID}/
└── generator_{model}_{timestamp}/
    ├── generator.json        # Test scenarios (initial)
    ├── path_enhancer.json    # Test scenarios with path enhancement
    ├── data_enhancer.json    # Test scenarios with path + data enhancement
    ├── post_processor.json   # ✨ Bug filtering (optional)
    └── {scenario_index}/     # Per-scenario results (0, 1, 2, ...)
        ├── 📄 OUTPUT.pdf     # ⭐ Visual report (start here!)
        ├── replayer.pdf      # Execution trace
        ├── player.json       # LLM interactions
        ├── replayer.json     # UI actions
        ├── detector_*.json   # Detected bugs
        └── SCREENSHOT/
            ├── SCREENSHOT_{N}.png              # After version
            ├── SCREENSHOT_BEFORE_CHANGE_{N}.png # Before version
            └── PARSED_SCREENSHOT_{N}.png       # With diff annotations
```

---

## Known Differences from the Accepted Paper

⚠️ **Note**: The artifact contains a **correction** to the evaluation statistics:

* **Issue.** In the accepted paper, one Firefox true positive (TP) bug was mistakenly counted as a false positive (FP).

* **Correction.** This artifact includes the corrected evaluation results:

  * **Table 1:** Firefox TP +1, FP −1 -> Total TP +1, Total FP −1
  * **RQ2:** The number of analyzed false-positive bugs decreases by 1.

* **Impact.** This correction affects only the reported statistics and does **not** change the experimental findings or the conclusions of the paper.

* **Camera-ready.** We intend to incorporate this correction into the camera ready version.

---

## Results Reported in the Paper

To reproduce the results reported in **Table 1 (Bug Detection)**, run:

```bash
python -m scripts.evaluation.calculate_bug_detection_metrics
```

### RQ1: Effectiveness in Detecting Previously Unknown Bugs 

The main RQ1 result is reported as **Bugs#** in **Table 1 (Bug Detection)**:

- **Bugs#**: Number of previously unknown unique bugs detected by RippleGUItester.

#### Reported Bugs

The following real-world bugs were discovered and reported by RippleGUItester:

| No. | Project | Bug ID / Link                                                                                                |
| --: | ------- | ------------------------------------------------------------------------------------------------------------ |
|   1 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6067](https://github.com/Zettlr/Zettlr/issues/6067)                 |
|   2 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6090](https://github.com/Zettlr/Zettlr/issues/6090)                 |
|   3 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6091](https://github.com/Zettlr/Zettlr/issues/6091)                 |
|   4 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6092](https://github.com/Zettlr/Zettlr/issues/6092)                 |
|   5 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6093](https://github.com/Zettlr/Zettlr/issues/6093)                 |
|   6 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6099](https://github.com/Zettlr/Zettlr/issues/6099)                 |
|   7 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6101](https://github.com/Zettlr/Zettlr/issues/6101)                 |
|   8 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6102](https://github.com/Zettlr/Zettlr/issues/6102)                 |
|   9 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6103](https://github.com/Zettlr/Zettlr/issues/6103)                 |
|  10 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6104](https://github.com/Zettlr/Zettlr/issues/6104)                 |
|  11 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6106](https://github.com/Zettlr/Zettlr/issues/6106)                 |
|  12 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6108](https://github.com/Zettlr/Zettlr/issues/6108)                 |
|  13 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6109](https://github.com/Zettlr/Zettlr/issues/6109)                 |
|  14 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6128](https://github.com/Zettlr/Zettlr/issues/6128)                 |
|  15 | Zettlr  | [https://github.com/Zettlr/Zettlr/issues/6129](https://github.com/Zettlr/Zettlr/issues/6129)                 |
|  16 | JabRef  | [https://github.com/JabRef/jabref/issues/14654](https://github.com/JabRef/jabref/issues/14654)               |
|  17 | JabRef  | [https://github.com/JabRef/jabref/issues/14789](https://github.com/JabRef/jabref/issues/14789)               |
|  18 | JabRef  | [https://github.com/JabRef/jabref/issues/14804](https://github.com/JabRef/jabref/issues/14804)               |
|  19 | JabRef  | [https://github.com/JabRef/jabref/issues/14805](https://github.com/JabRef/jabref/issues/14805)               |
|  20 | JabRef  | [https://github.com/JabRef/jabref/issues/14807](https://github.com/JabRef/jabref/issues/14807)               |
|  21 | JabRef  | [https://github.com/JabRef/jabref/issues/14821](https://github.com/JabRef/jabref/issues/14821)               |
|  22 | JabRef  | [https://github.com/JabRef/jabref/issues/14822](https://github.com/JabRef/jabref/issues/14822)               |
|  23 | Godot   | [https://github.com/godotengine/godot/issues/114157](https://github.com/godotengine/godot/issues/114157)     |
|  24 | Firefox | [https://bugzilla.mozilla.org/show_bug.cgi?id=2010360](https://bugzilla.mozilla.org/show_bug.cgi?id=2010360) |
|  25 | Firefox | [https://bugzilla.mozilla.org/show_bug.cgi?id=1986295](https://bugzilla.mozilla.org/show_bug.cgi?id=1986295) |
|  26 | Firefox | [https://bugzilla.mozilla.org/show_bug.cgi?id=1986162](https://bugzilla.mozilla.org/show_bug.cgi?id=1986162) |

---

### RQ2: Precision of Reported Bugs

The main RQ2 result is reported as **Precision** in **Table 1 (Bug Detection)**:

* **Precision**: The proportion of reported bugs that are manually verified as true positives.
* **Precision** = TP / (TP + FP)

To reproduce the false-positive analysis, run:

```bash
python -m scripts.evaluation.analyze_false_positive_bugs
```

The output reproduces the false-positive distribution analysis discussed in RQ2.

### RQ3: Recall on Previously Known Regression Bugs

The main RQ3 result is reported in **Figure 8**, which illustrates the overlap between bugs detected by RippleGUItester and the ground-truth introduced bugs.

To reproduce the RQ3 results, run:

```bash
python -m scripts.evaluation.calculate_recall_on_known_bugs
```

#### Analysis of Missed Ground-Truth Bugs

To reproduce the analysis of missed ground-truth bugs reported in **Section 4.4.1**, run:

```bash
python -m scripts.evaluation.analyze_missed_ground_truth_bugs
```

### RQ4: Computational and Monetary Costs

The main RQ4 results analyze the execution time and monetary costs of RippleGUItester across different phases.

#### SKB Construction Overhead

To calculate the one-time SKB (Scenario Knowledge Base) construction overhead, run:

```bash
python -m scripts.evaluation.calculate_skb_overhead
```

#### Overhead Breakdown (Figure 9)

To reproduce the overhead breakdown visualization shown in **Figure 9**, run:

```bash
python -m scripts.evaluation.calculate_overhead_breakdown
```

