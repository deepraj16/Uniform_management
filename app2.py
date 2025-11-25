import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
import av
import cv2
from PIL import Image
import numpy as np
from datetime import datetime
import io

st.title("📸 Webcam Image Capture")
st.write("Click the 'Capture Image' button to take a photo from your webcam")

# Initialize session state for captured images
if 'captured_images' not in st.session_state:
    st.session_state.captured_images = []

class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.capture_flag = False
        self.captured_frame = None
    
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # If capture flag is set, save the frame
        if self.capture_flag:
            self.captured_frame = img.copy()
            self.capture_flag = False
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# Create the webrtc streamer
ctx = webrtc_streamer(
    key="webcam",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=VideoProcessor,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# Capture button
capture_button = st.button("📷 Capture Image", type="primary")

if capture_button and ctx.video_processor:
    ctx.video_processor.capture_flag = True
    st.success("✅ Image captured!")

# Check if a new image was captured
if ctx.video_processor and ctx.video_processor.captured_frame is not None:
    # Convert BGR to RGB for display
    img_rgb = cv2.cvtColor(ctx.video_processor.captured_frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    
    # Add to session state
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.captured_images.append({
        'image': pil_img,
        'timestamp': timestamp
    })
    
    # Clear the captured frame
    ctx.video_processor.captured_frame = None
    st.rerun()

# Show the most recent captured image right below the stream
if st.session_state.captured_images:
    st.write("### 📸 Latest Capture")
    latest_img = st.session_state.captured_images[-1]
    st.image(latest_img['image'], caption=f"Captured at {latest_img['timestamp']}", use_container_width=True)
    
    # Download button for latest image
    buf = io.BytesIO()
    latest_img['image'].save(buf, format='PNG')
    byte_im = buf.getvalue()
    
    st.download_button(
        label="💾 Download Latest Image",
        data=byte_im,
        file_name=f"capture_{latest_img['timestamp'].replace(':', '-')}.png",
        mime="image/png"
    )

# Display captured images
if st.session_state.captured_images:
    st.write("---")
    st.subheader("Captured Images")
    
    for idx, img_data in enumerate(reversed(st.session_state.captured_images)):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.image(img_data['image'], caption=f"Captured at {img_data['timestamp']}", use_container_width=True)
        
        with col2:
            # Download button for each image
            buf = io.BytesIO()
            img_data['image'].save(buf, format='PNG')
            byte_im = buf.getvalue()
            
            st.download_button(
                label="💾 Download",
                data=byte_im,
                file_name=f"capture_{img_data['timestamp'].replace(':', '-')}.png",
                mime="image/png",
                key=f"download_{idx}"
            )
    
    # Clear all button
    if st.button("🗑️ Clear All Images"):
        st.session_state.captured_images = []
        st.rerun()