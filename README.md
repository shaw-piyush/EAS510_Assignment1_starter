# EAS 510 - Assignment 1: Digital Forensics Apprentice

A rule-based expert system that matches modified images back to their originals.

This is the **starter repository** for Project 1. Two repositories matter:

| Repository | Role |
|------------|------|
| `delveccj/EAS510_Assignment1_starter` (this repo) | Your **code** lives here. You will fork it, work in your fork, and push your final submission here. |
| `delveccj/EAS510_Assignment1` | The **dataset** (read-only). Clone it for the images; never commit it to your fork. |

## Setup on your Codio box

```bash
# 1. Fork this repo on GitHub, then in your box:
git clone https://github.com/YOUR-USERNAME/EAS510_Assignment1_starter.git
cd EAS510_Assignment1_starter

# 2. Clone the read-only dataset as a sibling folder (images live there):
cd ~/workspace
git clone https://github.com/delveccj/EAS510_Assignment1.git

# 3. Install dependencies:
cd ~/workspace/EAS510_Assignment1_starter
python3 -m pip install -r requirements.txt

# 4. Point this box at YOUR fork (run once):
./setup_git.sh
```

## Repository layout

```
forensics_detective.py   SimpleDetector: register targets + find_best_match
rules.py                 Rule functions (Rule 1: Metadata, Rule 2: Histogram, Rule 3: Template)
test_system.py           Runs the detector over the data folders and writes results_*.txt
scripts/check_output_format.py   Validates a results file against the required format
setup_git.sh, submit.sh  One-time setup + commit/push helper ("backup button")
```

## The task in one paragraph

Implement three interpretable rules (metadata, color histogram, template matching)
that combine into a 0-100 confidence score. Run your system on `modified_images/`
and `random/` and save the full output as `results_v1.txt`. In Phase 2, run on
`hard/`, diagnose a systematic failure, add a **Rule 4**, and save
`results_v1_hard.txt` and `results_v2.txt`. Full instructions are in the Codio guide
and in the assignment PDF in UBLearns.

## Running

```bash
# Phase 1 (easy + random) -> results_v1.txt
python3 test_system.py --modified --random --output results_v1.txt

# Phase 1 on hard cases -> results_v1_hard.txt
python3 test_system.py --hard --output results_v1_hard.txt

# Phase 2 (everything) -> results_v2.txt
python3 test_system.py --modified --hard --random --output results_v2.txt

# Validate any results file against the required format:
python3 scripts/check_output_format.py results_v1.txt
```

The data folders are resolved from a sibling clone of `EAS510_Assignment1`.
If your data is elsewhere, pass `--data-dir /path/to/EAS510_Assignment1`.

## Output format (do not alter)

```
Processing: modified_image_01.jpg
Rule 1 (Metadata): FIRED - Size ratio 0.85 -> 20/30 points
Rule 2 (Histogram): FIRED - Correlation 0.92 -> 25/30 points
Rule 3 (Template): FIRED - Match score 0.76 -> 30/40 points
Final Score: 75/100 -> MATCH to original_03.jpg
```

## Backup doctrine

Your Codio box can be reset at any time. **Your fork on GitHub is the only safe
copy.** After every milestone run `./submit.sh "describe what you did"`. A box
restart never touches GitHub.

## License

Apache 2.0. See `LICENSE`.


# Phase 2 Evaluation and Reflection

## Observed weakness in V1: what failed and why

The V1 detector used three rules: metadata comparison, histogram correlation, and template matching. Although these methods identified some modified images, their performance decreased when multiple transformations were applied.

V1 matched **32 out of 60 modified images (53.3%)** and **29 out of 60 hard images (48.3%)**. These results revealed weaknesses in handling cropping, resizing, rotation, brightness changes, and compression.

Each rule had specific limitations:

- **Rule 1 (Metadata):** Compared file size and retained image area rather than distinctive visual content. Cropping, resizing, and compression could change these properties, reducing the score of genuine matches.
- **Rule 2 (Histogram):** Compared color distributions without considering spatial layout. Brightness and contrast adjustments could reduce similarity, while unrelated images with similar color distributions could receive high scores.
- **Rule 3 (Template Matching):** Relied on direct pixel alignment. Cropping, resizing, and rotation could reduce correlation even when the underlying image content remained the same.

The common weakness was that the original rules were sensitive to transformations affecting global image properties or pixel alignment. When multiple transformations occurred together, the combined score could fall below the matching threshold.

This motivated the addition of a feature-based rule capable of identifying local visual similarities despite geometric modifications.

## Design decision for V2:

To address the limitations of V1, I implemented **ORB (Oriented FAST and Rotated BRIEF) feature matching with RANSAC geometric verification** as Rule 4.

Unlike the original rules, ORB identifies distinctive local image features rather than relying entirely on dimensions, color distributions, or fixed pixel positions.

### How Rule 4 works

1. **Preprocessing:** Images are resized to a maximum dimension of 640 pixels, and CLAHE is applied to improve local contrast.
2. **Feature extraction:** ORB detects keypoints across multiple image scales and generates rotation-aware binary descriptors.
3. **Feature matching:** A brute-force matcher compares descriptors using Hamming distance. Lowe's ratio test with a threshold of 0.75 removes ambiguous matches.
4. **Geometric verification:** RANSAC estimates a rotation-scale-translation transformation and identifies geometrically consistent feature correspondences.
5. **Scoring:** Rule 4 requires at least 12 inliers, an inlier ratio of 0.35, and a scale between 0.2 and 5.0. The score increases with the number of inliers, reaching the maximum at 30 inliers.

### Why I chose this approach

- **Cropping, rotation, and resizing:** Local keypoints can remain recognizable even when the overall image dimensions or alignment change.
- **Brightness and contrast:** CLAHE helps improve feature detection under different lighting conditions.
- **Spatial verification:** RANSAC checks that matching features follow a consistent geometric transformation, reducing accidental matches.
- **Metadata independence:** ORB compares visual structures rather than relying on file properties.

I assigned Rule 4 a higher weight because it directly addresses the geometric transformations that weakened V1. The original three rules were retained as supporting evidence.

### Rule Weight Comparison

| Rule | V1 Weight | V2 Weight |
|---|---:|---:|
| Metadata | 30 | 10 |
| Histogram | 30 | 20 |
| Template Matching | 40 | 20 |
| ORB Feature Matching | 0 | 50 |
| **Total** | **100** | **100** |

The revised distribution gives greater importance to feature-based matching while keeping the total score out of 100.

## Effect of the change: accuracy before/after on easy vs hard

Testing showed a substantial improvement in detection performance after introducing Rule 4.

### Performance Comparison

| Evaluation Metric | V1 | V2 |
|---|---:|---:|
| Modified images matched | 32/60 (53.3%) | 49/60 (81.7%) |
| Hard images matched | 29/60 (48.3%) | 57/60 (95.0%) |
| Random images falsely accepted | 0/15 | 0/15 |
| Number of detection rules | 3 | 4 |

V2 detected **17 additional modified images** and **28 additional hard images** compared with V1.

The modified-image match rate increased by approximately **28.3 percentage points**, while the hard-image match rate increased by approximately **46.7 percentage points**.

### Example of Improved Detection

One example from the hard dataset was:

`original_00__crop_keep60__resized__q45__v6.jpg`

- **V1 Result:** REJECTED
- **V2 Result:** MATCHED
- **Transformations:** Cropping, resizing, and JPEG compression.

These transformations can significantly affect metadata measurements and template correlation.

However, ORB can identify corresponding local features within the remaining image content, while RANSAC verifies their geometric consistency. This provides additional evidence that the modified image originated from the same source.

Other recovered examples involved off-center cropping, brightness adjustments, resizing, and compression. This suggests that the improvement was not limited to a single transformation type.

Importantly, both versions recorded **zero false accepts among the 15 random images tested**. This indicates that V2 improved detection without introducing additional false positives on the tested random dataset.

Overall, the results suggest that feature-based matching successfully addressed a major weakness of the original rule set.

## Trade-offs: what new costs or risks did Rule 4 introduce

The primary trade-off was increased computational cost. ORB requires keypoint extraction, descriptor matching, and RANSAC geometric verification, making V2 more computationally demanding than V1.

### Runtime Comparison

| Metric | V1 | V2 |
|---|---:|---:|
| Hard images processed | 60 | 60 |
| Execution time | 29.429 seconds | 33.416 seconds |
| Images matched | 29 | 57 |

V2 required approximately **3.99 additional seconds**, representing a **13.5% increase in wall-clock execution time** in the measured run.

To reduce this overhead, I limited image dimensions to 640 pixels and implemented feature caching to avoid repeatedly extracting features from the same image.

Another concern is the possibility of false positives. Images containing repetitive textures or similar visual structures may produce misleading feature correspondences. Lowe's ratio test and RANSAC verification help reduce this risk, although they cannot eliminate it completely.

Additionally, ORB may struggle with heavily blurred images, low-texture regions, or severe transformations that leave too few distinctive keypoints.

Increasing Rule 4's weight to 50 points also makes the final decision more dependent on feature matching. Incorrect ORB matches could therefore have a greater influence on the final score.

Despite these limitations, the evaluation demonstrated a substantial improvement in detecting modified images, particularly on the hard dataset, with a relatively small increase in measured execution time.

Overall, V2 improved robustness against geometric and visual transformations while maintaining zero observed false accepts on the random test set. The results support using local feature matching and geometric verification alongside the original three rules.
