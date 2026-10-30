import cv2, os

video_path = r'C:/Users/yashm/.gemini/antigravity/brain/f2c8165e-4c1c-4b8e-9e81-840977aaf3eb/.user_uploaded/media_1793353414447_16f8d2ec.mp4'
cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
print('Total frames:', total_frames, 'FPS:', fps, 'Duration sec:', total_frames / max(1, fps))

# Sample 8 frames across the video
indices = [int(total_frames * i / 7) for i in range(7)] + [total_frames - 1]
for i, idx in enumerate(indices):
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f'video_frame_{i}.png', frame)
        print(f'Saved video_frame_{i}.png (frame {idx})')
cap.release()

