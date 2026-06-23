/** SASH-VPV dataset — public Kaggle release + full local research corpus (NUTECH). */

export const SASH_VPV_KAGGLE_URL =
  "https://www.kaggle.com/datasets/sashinoventures/sash-vpv-subcutaneous-vascular-palm-vein-data"

export const SASH_VPV_DATASET = {
  acronym: "SASH-VPV",
  title: "Secure Authentication via Subcutaneous Vascular Palm-Veins",
  subtitle: "Subcutaneous Vascular Palm Vein Data",
  publisher: "SASHINO Ventures",
  license: "CC BY 4.0",
  kaggleUrl: SASH_VPV_KAGGLE_URL,
  /** Full corpus on disk at `data/raw/img` — used for model training. */
  local: {
    subjects: "200+",
    images: 4652,
    handClasses: "400+",
    resolution: "480 × 640",
    format: "8-bit grayscale PNG",
    wavelength: "850 nm NIR",
    sensor: "XRTECH MagicVein Plus",
    captureDistance: "3–8 cm (contactless)",
    sessions: [
      { id: "S1", label: "Session 1", subjects: "001–073", images: 1439 },
      { id: "S2", label: "Session 2", subjects: "074–120", images: 1157 },
    ],
    imagesPerHand: { min: 4, max: 21, average: 10.9 },
    naming: "S{session}_{subjectID}_{L|R}_{index}.png",
    structure: "img/<subject>/<Left|Right>/",
  },
  /** Public Kaggle release is a subset; full dataset stays on the research machine. */
  kaggleNote:
    "A curated subset is published on Kaggle for the research community. The complete SASH-VPV corpus used to train our EfficientNet-B0 + ArcFace matcher is maintained locally at NUTECH.",
} as const
