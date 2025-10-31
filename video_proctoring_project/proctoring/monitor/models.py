from django.db import models
from django.contrib.auth.models import User

# ------------------------------
# Student profile for login
# ------------------------------
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=128)
    dob = models.DateField()  # Date of Birth
    roll_number = models.CharField(max_length=50, unique=True, null=False, blank=False)
    def __str__(self):
        return self.full_name


# ------------------------------
# Candidate monitored for exam
# ------------------------------
class Candidate(models.Model):
    name = models.CharField(max_length=128)
    roll_number = models.CharField(max_length=50, unique=True, null=False, blank=False)
    email = models.EmailField(blank=True, null=True, unique=True)
    photo = models.ImageField(upload_to="candidate_photos/", blank=True, null=True)
    authorized_embedding = models.JSONField(blank=True, null=True)  # Face embeddings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Block system ---
    blocked = models.BooleanField(default=False)  # True if blocked by proctoring
    blocked_reason = models.TextField(blank=True, null=True)  # Reason for blocking

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


# ------------------------------
# Exam / monitoring session
# ------------------------------
class Session(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    verdict = models.CharField(
        max_length=16,
        choices=[("clean", "Clean"), ("suspicious", "Suspicious")],
        default="clean",
    )
    suspicion_score = models.FloatField(default=0.0)
    blocked = models.BooleanField(default=False)  # Block candidate if >3 suspicious events
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)  # ✅ Add this line
    updated_at = models.DateTimeField(auto_now=True)
    
    # Exam completion fields
    exam_completed = models.BooleanField(default=False)
    exam_score = models.FloatField(null=True, blank=True)  # Score out of 100
    total_questions = models.IntegerField(null=True, blank=True)
    correct_answers = models.IntegerField(null=True, blank=True)
    certificate_generated = models.BooleanField(default=False)

    def __str__(self):
        return f"Session {self.id} - {self.candidate.name if self.candidate else 'Unknown'}"


# ------------------------------
# Suspicious / proctoring events
# ------------------------------
class Event(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="events")
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(
        max_length=64,
        choices=[
            ("face_mismatch", "Face Mismatch"),
            ("gaze_offscreen", "Gaze Offscreen"),
            ("multi_face", "Multiple Faces Detected"),
            ("audio_others", "Other Voices Detected"),
            ("device_detected", "Gadget Detected"),
        ],
    )
    details = models.TextField(blank=True)
    score = models.FloatField(default=0.0)  # Suspicion score for this event
    frame_file = models.ImageField(upload_to="evidence/frames/", null=True, blank=True)
    audio_file = models.FileField(upload_to="evidence/audio/", null=True, blank=True)

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.timestamp.strftime('%H:%M:%S')}"


# ------------------------------
# Exam scheduling (admin-controlled)
# ------------------------------
class ExamSchedule(models.Model):
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Exam @ {self.start_time} for {self.duration_minutes} mins ({'active' if self.is_active else 'inactive'})"

    @property
    def end_time(self):
        from datetime import timedelta
        return self.start_time + timedelta(minutes=self.duration_minutes)
