"""EAS 510 - Project 1 - Phase 2: the V2 rule set.

Rules 1-3 are kept exactly as in `rules.py`. Your job is to ADD Rule 4 that
targets the systematic weakness you diagnosed from results_v1_hard.txt.

Constraint: the rules' `out_of` weights must still sum to 100 so the Final
Score stays on a /100 scale (the format validator enforces "Final Score:
<s>/100" equals the sum of the block's rule scores).

Example split that keeps the original spirit: Rules 1-3 -> 25/25/40 and
Rule 4 -> 10 (or trim the losers more aggressively).
"""

from functools import lru_cache
 
import cv2
import numpy as np
import rules

_original_rule1 = rules.rule1_metadata
_original_rule2 = rules.rule2_histogram
_original_rule3 = rules.rule3_template

RULES = ("rule1_metadata", "rule2_histogram", "rule3_template", "rule4_edges") 
# ---- Rule 4 tunables: calibrate on random/ first, then on the hard set -----
R4_OUT_OF = 50            # must match this rule's weight in the 100-point split
R4_MAX_DIM = 640          # downscale long side before ORB (speed)
R4_RATIO = 0.75           # Lowe ratio test
R4_MIN_MATCHES = 10       # ratio-test survivors needed to attempt a transform
R4_MIN_INLIERS = 12       # set just above the max seen on random/ (see notes)
R4_MIN_INLIER_RATIO = 0.35
R4_FULL_INLIERS = 30      # inliers at which the rule earns full points
R4_REPROJ_PX = 4.0        # RANSAC reprojection tolerance (pixels, downscaled)
R4_SCALE_RANGE = (0.2, 5.0)
 
_CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

def _rescale_v1(result, points):
    """Rescale V1 scores without changing their decisions."""
    result = dict(result)

    old_max = int(result.get("out_of", 0))
    old_score = int(result.get("score", 0))

    result["out_of"] = points

    if old_max:
        new_score = round(points * old_score / old_max)
        result["score"] = max(0, min(points, int(new_score)))
    else:
        result["score"] = 0

    return result

def rule1_metadata(target, input_path):
    return _rescale_v1(_original_rule1(target, input_path), 10)

def rule2_histogram(target, input_path):
    return _rescale_v1(_original_rule2(target, input_path), 20)

def rule3_template(target, input_path):
    return _rescale_v1(_original_rule3(target, input_path), 20) 
 
@lru_cache(maxsize=256)
def _orb_features(path):
    """Keypoint coordinates + ORB descriptors for one image, cached per path."""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None
    h, w = img.shape[:2]
    if max(h, w) > R4_MAX_DIM:
        s = R4_MAX_DIM / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    img = _CLAHE.apply(img)  # evens out brightness/contrast shifts before detection
    kps, des = cv2.ORB_create(nfeatures=1500).detectAndCompute(img, None)
    if des is None or len(kps) < 8:
        return None, None
    return np.float32([k.pt for k in kps]), des
 
 
def rule4_edges(target, input_path):
    """Keypoint matches that agree on one rotate+scale+shift (survives crop/resize)."""
    out = {"rule": 4, "name": "Edges", "fired": False, "score": 0,
           "out_of": R4_OUT_OF, "note": "No ORB Match", "metric": 0.0}
    try:
        pts1, des1 = _orb_features(target["path"])
        pts2, des2 = _orb_features(input_path)
        if des1 is None or des2 is None:
            return out
 
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des1, des2, k=2)
        best = {}  # keep one match per suspect keypoint
        for p in pairs:
            if len(p) == 2 and p[0].distance < R4_RATIO * p[1].distance:
                m = p[0]
                if m.trainIdx not in best or m.distance < best[m.trainIdx].distance:
                    best[m.trainIdx] = m
        good = list(best.values())
        if len(good) < R4_MIN_MATCHES:
            out["note"] = f"ORB: {len(good)} good matches (need {R4_MIN_MATCHES})"
            return out
 
        src = pts1[[m.queryIdx for m in good]].reshape(-1, 1, 2)
        dst = pts2[[m.trainIdx for m in good]].reshape(-1, 1, 2)
        M, mask = cv2.estimateAffinePartial2D(
            src, dst, method=cv2.RANSAC, ransacReprojThreshold=R4_REPROJ_PX)
        if M is None or mask is None:
            return out
 
        inliers = int(mask.sum())
        ratio = inliers / len(good)
        scale = float(np.hypot(M[0, 0], M[1, 0]))
        out["note"] = f"ORB: {inliers}/{len(good)} similarity inliers, scale {scale:.2f}"
 
        if (inliers >= R4_MIN_INLIERS and ratio >= R4_MIN_INLIER_RATIO
                and R4_SCALE_RANGE[0] <= scale <= R4_SCALE_RANGE[1]):
            metric = min(1.0, inliers / R4_FULL_INLIERS)
            out["metric"] = round(metric, 3)
            out["fired"] = True
            out["score"] = max(1, min(R4_OUT_OF, int(round(R4_OUT_OF * metric))))
    except (cv2.error, ValueError, TypeError, KeyError, IndexError) as exc:
        out["note"] = f"ORB error: {str(exc)[:80]}"
    return out
rules.rule1_metadata = rule1_metadata
rules.rule2_histogram = rule2_histogram
rules.rule3_template = rule3_template
