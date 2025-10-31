from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Candidate, Session, Event, StudentProfile
from deepface import DeepFace
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# -----------------------------
# Candidate Admin
# -----------------------------
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'roll_number', 'email', 'photo_thumbnail', 'has_embedding',
                    'created_at', 'updated_at', 'blocked', 'blocked_reason')
    readonly_fields = ('photo_thumbnail', 'created_at', 'updated_at')
    list_filter = ('blocked',)

    # Display photo thumbnail
    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:50%;" />',
                obj.photo.url
            )
        return "-"
    photo_thumbnail.short_description = "Photo"

    # Show if embedding exists
    def has_embedding(self, obj):
        return bool(obj.authorized_embedding)
    has_embedding.boolean = True
    has_embedding.short_description = "Embedding"

    # Save model and generate embedding if photo exists
    def save_model(self, request, obj, form, change):
        if obj.photo:
            try:
                img_path = obj.photo.path
                embedding = DeepFace.represent(
                    img_path=img_path,
                    model_name="Facenet512",
                    enforce_detection=True
                )[0]['embedding']
                obj.authorized_embedding = embedding
            except Exception as e:
                print(f"Error generating embedding for {obj.name}: {e}")
        super().save_model(request, obj, form, change)

    # Custom action to unblock candidates
    actions = ['unblock_candidates']

    def unblock_candidates(self, request, queryset):
        updated = queryset.update(blocked=False, blocked_reason='')
        self.message_user(request, f"{updated} candidate(s) unblocked.")
    unblock_candidates.short_description = "Unblock selected candidates"


# -----------------------------
# Session Admin
# -----------------------------
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'candidate_name', 'started_at', 'ended_at', 'verdict', 'get_suspicion_score', 'blocked')
    readonly_fields = ('candidate_name', 'suspicion_score', 'started_at', 'ended_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_score=Sum('events__score'))

    def get_suspicion_score(self, obj):
        return getattr(obj, 'total_score', 0) or 0
    get_suspicion_score.short_description = "Suspicion Score"
    get_suspicion_score.admin_order_field = 'total_score'

    def candidate_name(self, obj):
        return obj.candidate.name if obj.candidate else "Unknown"
    candidate_name.short_description = "Candidate"


# -----------------------------
# Event Admin
# -----------------------------
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('pk', 'session_info_safe', 'event_type', 'score', 'frame_preview', 'audio_file_link', 'timestamp')
    readonly_fields = ('frame_preview', 'timestamp')

    def session_info_safe(self, obj):
        if obj.session:
            candidate_name = obj.session.candidate.name if obj.session.candidate else "Unknown"
            return f"Session {obj.session.id} - {candidate_name}"
        return "-"
    session_info_safe.short_description = "Session"

    def frame_preview(self, obj):
        if obj.frame_file:
            return format_html('<img src="{}" width="80" style="object-fit:cover;"/>', obj.frame_file.url)
        return "-"
    frame_preview.short_description = "Frame"

    def audio_file_link(self, obj):
        if obj.audio_file:
            return format_html('<a href="{}" target="_blank">Play Audio</a>', obj.audio_file.url)
        return "-"
    audio_file_link.short_description = "Audio"


# -----------------------------
# Custom User Admin with StudentProfile
# -----------------------------
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Info'

class CustomUserAdmin(UserAdmin):
    inlines = (StudentProfileInline,)
    list_display = ('username', 'email', 'is_active', 'is_staff')

# Unregister default User and register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# -----------------------------
# StudentProfile Admin (optional)
# -----------------------------
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'roll_number')
    search_fields = ('full_name', 'roll_number', 'user__username')

