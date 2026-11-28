import streamlit as st
from PIL import Image
from pathlib import Path
import tempfile
import os

from inference import predict_image


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="AMSF-GNet | Deepfake Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #0b1020;
        color: #f1f5f9;
    }

    .main-title {
        font-size: 42px;
        font-weight: 800;
        text-align: center;
        color: #ffffff;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 16px;
        margin-bottom: 35px;
    }

    .result-card {
        padding: 25px;
        border-radius: 15px;
        background: #151e32;
        border: 1px solid #26344d;
        text-align: center;
        margin-top: 15px;
    }

    .real-result {
        color: #34d399;
        font-size: 36px;
        font-weight: 800;
    }

    .fake-result {
        color: #fb7185;
        font-size: 36px;
        font-weight: 800;
    }

    .footer {
        text-align: center;
        color: #64748b;
        font-size: 13px;
        margin-top: 55px;
    }

    div[data-testid="stFileUploader"] {
        background: #151e32;
        padding: 20px;
        border-radius: 12px;
        border: 1px dashed #475569;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">AMSF-GNet</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Robust Facial Deepfake Detection Using '
    'Degradation-Aware Adaptive Spatial-Frequency Graph Learning'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# --------------------------------------------------
# INTRODUCTION
# --------------------------------------------------

st.markdown("### Image Authenticity Analysis")

st.write(
    "Upload a facial image to analyse whether it is classified "
    "as REAL or FAKE by the trained AMSF-GNet V3 model."
)

st.info(
    "Supported formats: JPG, JPEG, PNG and WEBP. "
    "The model processes images at 160 × 160 resolution."
)


# --------------------------------------------------
# IMAGE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload an image for detection",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=False
)


# --------------------------------------------------
# IMAGE PREVIEW AND PREDICTION
# --------------------------------------------------

if uploaded_file is not None:

    try:
        image = Image.open(uploaded_file).convert("RGB")

        left, right = st.columns([1, 1], gap="large")

        with left:
            st.markdown("### Uploaded Image")
            st.image(
                image,
                caption=uploaded_file.name,
                use_container_width=True
            )

        with right:
            st.markdown("### Detection")

            if st.button(
                "Analyse Image",
                type="primary",
                use_container_width=True
            ):

                temp_path = None

                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=Path(uploaded_file.name).suffix
                    ) as temp_file:

                        temp_file.write(uploaded_file.getvalue())
                        temp_path = temp_file.name

                    with st.spinner(
                        "AMSF-GNet is analysing the image..."
                    ):
                        result = predict_image(temp_path)

                    st.success("Image analysis completed.")

                    prediction = result["prediction"]
                    confidence = result["confidence"]

                    st.markdown(
                        '<div class="result-card">',
                        unsafe_allow_html=True
                    )

                    if prediction == "REAL":
                        st.markdown(
                            '<div class="real-result">REAL</div>',
                            unsafe_allow_html=True
                        )
                        st.write("The model classified this image as REAL.")

                    else:
                        st.markdown(
                            '<div class="fake-result">FAKE</div>',
                            unsafe_allow_html=True
                        )
                        st.write("The model classified this image as FAKE.")

                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown("### Prediction Confidence")

                    st.metric(
                        "Model confidence",
                        f"{confidence:.2f}%"
                    )

                    st.markdown("### Class Probabilities")

                    st.write(
                        f"REAL: {result['real_probability']:.2f}%"
                    )
                    st.progress(
                        result["real_probability"] / 100
                    )

                    st.write(
                        f"FAKE: {result['fake_probability']:.2f}%"
                    )
                    st.progress(
                        result["fake_probability"] / 100
                    )

                    st.caption(
                        "Confidence represents the model's softmax "
                        "output. It is not a guarantee of authenticity."
                    )

                except Exception as error:
                    st.error(f"Prediction failed: {error}")

                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)

    except Exception as error:
        st.error(f"Unable to open the uploaded image: {error}")


# --------------------------------------------------
# MODEL INFORMATION
# --------------------------------------------------

st.divider()

with st.expander("About the detection model"):

    st.markdown("""
    **Model:** AMSF-GNet V3 – Model B

    **Architecture components:**
    - Spatial feature extraction using MobileNetV3-Large
    - Frequency feature extraction using FFT and Haar wavelets
    - Residual feature extraction
    - Multi-head graph attention
    - Adaptive branch gating
    - Binary classification head

    **Classes:**
    - REAL (0)
    - FAKE (1)

    **Input resolution:** 160 × 160 pixels

    **Inference device:** CUDA GPU when available, otherwise CPU
    """)


# --------------------------------------------------
# DISCLAIMER
# --------------------------------------------------

st.markdown(
    '<div class="footer">'
    'AMSF-GNet Research Prototype | Deepfake Detection System'
    '<br>Predictions are model outputs and should not be treated '
    'as definitive forensic proof.'
    '</div>',
    unsafe_allow_html=True
)
