"""
Study Mode Page - Advanced Evaluation
(UI/evaluation-layer changes only: uses DOI column if present, verdict-aware prediction,
fixes dataframe sizing parameters, and removes seaborn dependency.)
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils.ui_helpers import hero, lucide
from utils.auditor import audit_citation
from config import TOK
from datetime import datetime


def _clean_doi(val) -> str | None:
    """Presentation/eval-layer helper: normalize DOI-like values from CSV."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
        return None
    return s


def _predict_label(verdict: str, score: float, threshold: float) -> int:
    """
    Verdict-aware prediction:
      - VERIFIED => Real (0)
      - HALLUCINATED => Hallucination (1)
      - UNCERTAIN => threshold on score
    """
    v = (verdict or "").strip().upper()
    if v == "VERIFIED":
        return 0
    if v == "HALLUCINATED":
        return 1
    return int(float(score) < float(threshold))


def render():
    """Render the study mode page"""
    hero(
        "Study Mode - Advanced Evaluation",
        "Upload a dataset with ground truth labels to generate classification reports, calibration plots, and threshold optimization.",
        badges=["Ground truth evaluation", "Calibration plots", "Threshold sweep", "Precision-Recall curves"],
    )

    uploaded_file = st.file_uploader(
        "Upload CSV with citations and human labels",
        type=["csv"],
        help="CSV should contain 'citation' and 'human_label' columns (0=real, 1=hallucinated). Optional: 'doi' column.",
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)

            if "citation" not in df.columns:
                st.error("CSV must contain column: ['citation']")
                return

            st.success(f"Loaded {len(df)} citations from dataset")

            with st.expander("Dataset preview", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)

            if st.button("Run evaluation", use_container_width=True):
                with st.spinner("Running batch evaluation..."):
                    results = []
                    threshold = float(st.session_state.get("threshold", 0.20))

                    has_doi = "doi" in df.columns
                    has_human = "human_label" in df.columns

                    for idx, row in df.iterrows():
                        citation = str(row["citation"])
                        doi_val = _clean_doi(row.get("doi")) if has_doi else None

                        # IMPORTANT: pass DOI through to enable registry verification tier
                        result = audit_citation(citation, doi_val)

                        pred = _predict_label(result.label, result.score, threshold)

                        results.append(
                            {
                                "index": idx,
                                "citation": citation,
                                "doi": doi_val if doi_val else "",
                                "score": float(result.score),
                                "predicted_label": int(pred),
                                "actual_label": int(row["human_label"]) if has_human and pd.notna(row["human_label"]) else None,
                                "verdict": result.label,
                                "tier": result.tier,
                            }
                        )

                    results_df = pd.DataFrame(results)
                    st.session_state["study_results"] = results_df

                    st.markdown("### Evaluation metrics")

                    if has_human:
                        # Ensure clean numeric arrays
                        eval_df = results_df.dropna(subset=["actual_label"]).copy()
                        y_true = eval_df["actual_label"].astype(int).values
                        y_pred = eval_df["predicted_label"].astype(int).values
                        y_scores = eval_df["score"].astype(float).values

                        from sklearn.metrics import (
                            accuracy_score,
                            precision_score,
                            recall_score,
                            f1_score,
                            classification_report,
                            confusion_matrix,
                        )

                        accuracy = accuracy_score(y_true, y_pred)
                        precision = precision_score(y_true, y_pred, average="binary", zero_division=0)
                        recall = recall_score(y_true, y_pred, average="binary", zero_division=0)
                        f1 = f1_score(y_true, y_pred, average="binary", zero_division=0)

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Accuracy", f"{accuracy:.3f}")
                        c2.metric("Precision", f"{precision:.3f}")
                        c3.metric("Recall", f"{recall:.3f}")
                        c4.metric("F1 Score", f"{f1:.3f}")

                        st.markdown("### Classification Report")
                        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
                        report_df = pd.DataFrame(report).transpose()
                        st.dataframe(report_df, use_container_width=True)

                        st.markdown("### Confusion matrix")
                        cm = confusion_matrix(y_true, y_pred)
                        fig, ax = plt.subplots(figsize=(7.2, 5.2))
                        im = ax.imshow(cm)
                        ax.set_xticks([0, 1], labels=["Real", "Hallucinated"])
                        ax.set_yticks([0, 1], labels=["Real", "Hallucinated"])
                        ax.set_xlabel("Predicted")
                        ax.set_ylabel("Actual")
                        for (i, j), v in np.ndenumerate(cm):
                            ax.text(j, i, str(v), ha="center", va="center")
                        st.pyplot(fig)

                        st.markdown("### Score Distribution")
                        fig, ax = plt.subplots(figsize=(9.5, 5.3))
                        for label in [0, 1]:
                            scores = eval_df.loc[eval_df["actual_label"] == label, "score"].astype(float).values
                            if len(scores):
                                ax.hist(scores, alpha=0.6, label=f"Label {label}", bins=20)
                        ax.axvline(x=threshold, color="red", linestyle="--", label=f"Threshold = {threshold:.3f}")
                        ax.set_xlabel("Plausibility Score")
                        ax.set_ylabel("Count")
                        ax.legend()
                        st.pyplot(fig)

                        st.markdown("### Threshold Optimization")
                        thresholds = np.linspace(0.1, 0.9, 50)
                        precisions, recalls, f1_scores = [], [], []

                        for t in thresholds:
                            # IMPORTANT: use the same verdict-aware rule in sweep
                            y_pred_t = np.array(
                                [
                                    _predict_label(v, s, float(t))
                                    for v, s in zip(eval_df["verdict"].values, eval_df["score"].values)
                                ],
                                dtype=int,
                            )
                            precisions.append(precision_score(y_true, y_pred_t, zero_division=0))
                            recalls.append(recall_score(y_true, y_pred_t, zero_division=0))
                            f1_scores.append(f1_score(y_true, y_pred_t, zero_division=0))

                        fig, ax = plt.subplots(figsize=(9.5, 5.3))
                        ax.plot(thresholds, precisions, label="Precision", marker=".")
                        ax.plot(thresholds, recalls, label="Recall", marker=".")
                        ax.plot(thresholds, f1_scores, label="F1 Score", marker=".")
                        ax.axvline(x=threshold, color="red", linestyle="--", label=f"Current = {threshold:.3f}")
                        ax.set_xlabel("Threshold")
                        ax.set_ylabel("Score")
                        ax.legend()
                        ax.grid(True, alpha=0.3)
                        st.pyplot(fig)

                        best_idx = int(np.argmax(f1_scores))
                        best_threshold = float(thresholds[best_idx])

                        st.markdown(
                            f"""
### Recommendation
**Optimal threshold for maximum F1: {best_threshold:.3f}**

Current threshold ({threshold:.3f}) F1: {f1:.3f}  
Optimal threshold F1: {float(f1_scores[best_idx]):.3f}
""".strip()
                        )

                    st.markdown("### Detailed Results")
                    st.dataframe(results_df, use_container_width=True, hide_index=True)

                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="Download Results CSV",
                        data=csv,
                        file_name=f"study_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

    else:
        st.markdown(
            f"""
<div class="cv-idle-state">
  <div style="margin-bottom:14px;opacity:0.7;color:{TOK['accent']};" class="cv-ico">{lucide('flask-conical')}</div>
  <div style="font-weight:700;font-size:15px;color:{TOK['subtext']};margin-bottom:6px;">
    Study Mode Ready
  </div>
  <div style="font-size:13px;color:{TOK['muted']};max-width:38ch;line-height:1.6;">
    Upload a CSV file with citations and ground truth labels to begin evaluation.
    The file should contain a 'citation' column and optionally a 'human_label' column.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )