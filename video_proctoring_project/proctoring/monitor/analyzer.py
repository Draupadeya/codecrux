import cv2
import numpy as np
from ultralytics import YOLO
from .models import Event
import speech_recognition as sr
from pydub import AudioSegment
import json

SIM_THRESHOLD = 0.6  # face similarity threshold

# Load YOLOv8 model (pretrained on COCO)
yolo_model = YOLO("yolov8n.pt")  # small, fast version

# Expanded gadget synonyms for detection
GADGET_SYNONYMS = [
    "cell phone", "cellphone", "mobile", "phone", "laptop", "notebook",
    "book", "keyboard", "mouse", "remote", "tv remote",
    "headphones", "earphones", "earbuds", "headset", "watch", "smartwatch", "tablet"
]
GADGET_NAMES = set(n.lower() for n in GADGET_SYNONYMS)

# ------------------------------
# Cosine similarity for face embeddings
# ------------------------------
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ------------------------------
# Load DeepFace embedding
# ------------------------------
def get_embedding_from_frame(face_img):
    from deepface import DeepFace
    try:
        face_resized = cv2.resize(face_img, (160, 160))
        rgb_face = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
        embedding = DeepFace.represent(rgb_face, model_name='Facenet')[0]["embedding"]
        emb_array = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(emb_array)
        if norm > 0:
            emb_array /= norm
        return emb_array
    except:
        return None

# ------------------------------
# Robustly read candidate embedding
# ------------------------------
def read_candidate_embedding(candidate):
    if not candidate or not candidate.authorized_embedding:
        return None
    raw = candidate.authorized_embedding
    emb = None
    if isinstance(raw, str):
        try:
            arr = json.loads(raw)
            emb = np.array(arr, dtype=np.float32)
        except:
            try:
                emb = np.fromstring(raw, sep=",", dtype=np.float32)
            except:
                return None
    elif isinstance(raw, (list, tuple)):
        emb = np.array(raw, dtype=np.float32)
    elif isinstance(raw, np.ndarray):
        emb = raw.astype(np.float32)
    if emb is not None:
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb /= norm
    return emb

# ------------------------------
# Analyze video frame
# ------------------------------
def analyze_frame(frame_bgr, session):
    events = []

    # Face detection
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(40, 40))
    hF, wF = frame_bgr.shape[:2]

    if len(faces) == 0:
        events.append({
            'type': 'no_face',
            'details': 'No face detected',
            'score': 0.2,
            'frame': frame_bgr,
            'box_coords': None
        })
        return events

    if len(faces) > 1:
        events.append({
            'type': 'multi_face',
            'details': f'{len(faces)} faces detected',
            'score': 0.6,
            'frame': frame_bgr,
            'box_coords': [int(faces[0][0]), int(faces[0][1]), int(faces[0][0]+faces[0][2]), int(faces[0][1]+faces[0][3])]
        })

    candidate_embedding = read_candidate_embedding(session.candidate)

    # Face verification & gaze
    for (x, y, w, h) in faces:
        face = frame_bgr[y:y+h, x:x+w]
        emb = get_embedding_from_frame(face)
        box_coords = [int(x), int(y), int(x+w), int(y+h)]

        if emb is not None and candidate_embedding is not None:
            sim = cosine_similarity(emb, candidate_embedding)
            if sim < SIM_THRESHOLD:
                events.append({
                    'type': 'face_mismatch',
                    'details': f'sim={sim:.2f}',
                    'score': 0.8,
                    'frame': frame_bgr,
                    'box_coords': box_coords
                })
        elif emb is None:
            events.append({
                'type': 'face_unknown',
                'details': 'embedding failed',
                'score': 0.2,
                'frame': frame_bgr,
                'box_coords': box_coords
            })

        # Gaze offscreen
        cx = x + w / 2
        if cx < 0.15 * wF or cx > 0.85 * wF:
            events.append({
                'type': 'gaze_offscreen',
                'details': 'face center offscreen',
                'score': 0.3,
                'frame': frame_bgr,
                'box_coords': box_coords
            })

    # Gadget detection using YOLO
    results = yolo_model.predict(frame_bgr, imgsz=640, conf=0.25, verbose=False)
    for r in results:
        if r.boxes is None or len(r.boxes) == 0:
            continue
        for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
            label = yolo_model.model.names[int(cls_id)].lower()
            if label in GADGET_NAMES:
                x1, y1, x2, y2 = [int(coord) for coord in box]
                events.append({
                    'type': 'device_detected',
                    'details': f'{label} detected ({float(conf):.2f})',
                    'score': 0.5,
                    'frame': frame_bgr,
                    'box_coords': [x1, y1, x2, y2]
                })

    # Session blocking logic
    suspicious_count = session.events.filter(event_type__in=[
        'face_mismatch', 'gaze_offscreen', 'multi_face', 'device_detected'
    ]).count() + sum(1 for ev in events if ev['type'] in [
        'face_mismatch', 'gaze_offscreen', 'multi_face', 'device_detected'
    ])

    if suspicious_count >= 3:
        session.blocked = True
        session.save()
        if session.candidate:
            session.candidate.blocked = True
            session.candidate.blocked_reason = "Exceeded suspicious activity threshold"
            session.candidate.save()

    return events

# ------------------------------
# Analyze audio for suspicious events
# ------------------------------
def analyze_audio(audio_file, session):
    events = []

    try:
        audio = AudioSegment.from_file(audio_file).set_channels(1).set_frame_rate(16000)
        wav_path = f"/tmp/{np.random.randint(0,100000)}.wav"
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                if text.strip():
                    events.append({
                        'type': 'audio_others',
                        'details': f"Speech detected: {text[:50]}",
                        'score': 0.5,
                        'box_coords': None
                    })
            except:
                pass

        # Detect loud noises
        samples = np.array(audio.get_array_of_samples())
        rms = np.sqrt(np.mean(samples**2))
        if rms > 2000:
            events.append({
                'type': 'audio_noise',
                'details': f"Loud noise detected (RMS={rms:.0f})",
                'score': 0.3,
                'box_coords': None
            })

    except Exception as e:
        events.append({
            'type': 'audio_error',
            'details': f"Audio processing failed: {str(e)}",
            'score': 0.2,
            'box_coords': None
        })

    # Blocking logic
    suspicious_count = session.events.filter(event_type__in=[
        'face_mismatch', 'gaze_offscreen', 'multi_face', 'device_detected', 'audio_others', 'audio_noise'
    ]).count() + sum(1 for ev in events if ev['type'] in [
        'face_mismatch', 'gaze_offscreen', 'multi_face', 'device_detected', 'audio_others', 'audio_noise'
    ])

    if suspicious_count >= 3:
        session.blocked = True
        session.save()
        if session.candidate:
            session.candidate.blocked = True
            session.candidate.blocked_reason = "Exceeded suspicious activity threshold"
            session.candidate.save()

    return events
