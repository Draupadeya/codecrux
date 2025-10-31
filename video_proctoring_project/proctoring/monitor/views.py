import io, base64, uuid
import numpy as np
import json
import datetime
from PIL import Image

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods 
from django.db.models import Sum 
from deepface import DeepFace 
from django.views.decorators.csrf import csrf_protect

# NOTE: Ensure your models are imported correctly from your app's models.py
from .models import Candidate, Session, Event, StudentProfile
from . import analyzer # Assuming 'analyzer' contains analyze_audio/analyze_frame logic

# Get the custom or default User model
User = get_user_model() 

# ==========================
# Base Index and Authentication Router
# ==========================


# ==========================
# Base Index and Authentication Router
# ==========================

def index(request: HttpRequest):
    # Retrieve and remove the login error message from the session
    login_error = request.session.pop('login_error', None)
    
    if request.user.is_authenticated:
        return redirect('post_login_redirect')
        
    context = {}
    if login_error:
        context['error'] = login_error
        
    return render(request, "monitor/index.html", context)


@csrf_protect # Crucial for handling browser POST data
def handle_unified_login(request: HttpRequest):
    """Handles POST requests from the unified login form."""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        # 2. If standard authentication fails, attempt manual DOB check
        if user is None:
            # ... (Manual DOB check logic remains the same) ...
            try:
                user = User.objects.get(username=username)
                if not user.is_staff and not user.is_superuser:
                    profile = getattr(user, 'studentprofile', None)
                    if profile and profile.date_of_birth:
                        dob_string = profile.date_of_birth.strftime('%Y%m%d') 
                        if password != dob_string:
                            user = None
                    else:
                        user = None
            except User.DoesNotExist:
                user = None
            except Exception as e:
                print(f"Error during manual DOB authentication: {e}")
                user = None 
        
        # 3. Final Check and Routing
        if user is not None:
            login(request, user)
            return redirect('post_login_redirect')
        
        # If authentication failed (user is None)
        request.session['login_error'] = "Invalid credentials. Please check your username/roll number and password."
        return redirect('index') # Use redirect for clean Post/Redirect/Get
    
    # If accessed via GET (should be handled by the index view's redirect)
    return redirect('index')


# ... (rest of authentication/dashboard views: redirect_to_dashboard, student_dashboard, admin_dashboard, user_logout) ...

# ==========================
# Proctor Block/Unblock API Views (Restored and Correct)
# ==========================

@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt # API views use csrf_exempt because they don't send form tokens
def proctor_block_view(request):
    """Handles API request to block a candidate and all active sessions."""
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        reason = data.get('reason', 'Manual block by Proctor') 
        
        if not candidate_id:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate ID.'}, status=400)

        # 1. Block the candidate (permanent status)
        candidate = Candidate.objects.get(id=candidate_id)
        candidate.blocked = True
        candidate.blocked_reason = reason
        candidate.save()

        # 2. Block all active sessions for this candidate
        Session.objects.filter(candidate=candidate, ended_at__isnull=True).update(
            blocked=True,
            verdict='blocked',
            ended_at=datetime.datetime.now()
        )
        
        return JsonResponse({'status': 'success', 'message': f'Candidate {candidate_id} blocked successfully.'})

    except Candidate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Candidate ID {candidate_id} not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt # API views use csrf_exempt because they don't send form tokens
def proctor_unblock_view(request):
    """Handles API request to unblock a candidate."""
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        
        if not candidate_id:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate ID.'}, status=400)

        # 1. Unblock the candidate (permanent status)
        candidate = Candidate.objects.get(id=candidate_id)
        candidate.blocked = False
        candidate.blocked_reason = "" # Clear the reason
        candidate.save()
        
        # 2. Update any pending sessions back to clean/unblocked
        Session.objects.filter(candidate=candidate, ended_at__isnull=True, blocked=True).update(
             blocked=False,
             verdict='clean'
        )
        
        return JsonResponse({'status': 'success', 'message': f'Candidate {candidate_id} unblocked successfully.'})

    except Candidate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Candidate ID {candidate_id} not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)@login_required
def redirect_to_dashboard(request: HttpRequest):
    """Routes the authenticated user after login redirect."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_dashboard') 
    else:
        return redirect('student_dashboard')


def user_logout(request):
    """Logs the user out and redirects to the index/login page."""
    logout(request)
    return redirect('index') 

# ==========================
# Protected Dashboards and Core Logic
# ==========================

@login_required
def student_dashboard(request: HttpRequest):
    user = request.user
    candidate = None
    
    # --- 1. Fetch Candidate Profile and Block Status (Safeguarded) ---
    try:
        profile = getattr(user, 'studentprofile', None)
        if not profile:
             # Logged-in user has no profile (Data Integrity Error)
             return redirect('user_logout')

        if hasattr(profile, 'roll_number'):
            # Fetch Candidate using the roll_number
            candidate = Candidate.objects.get(roll_number=profile.roll_number)
            
            if candidate.blocked:
                if 'current_session' in request.session:
                    del request.session['current_session']
                return redirect('blocked_page') 
        else:
             # Logged-in user has profile but no roll_number field
             return redirect('user_logout')

    except Candidate.DoesNotExist:
        # User is logged in, but Candidate record is missing.
        print(f"Data Error: Logged-in user {user.username} Candidate record missing.")
        return redirect('user_logout')
    except Exception as e:
        print(f"Unhandled Error in dashboard: {e}")
        return redirect('user_logout') 

    # --- 2. Fetch or Create Current Session ---
    session = Session.objects.filter(candidate=candidate, active=True).first()
    if not session:
         session = Session.objects.create(candidate=candidate, active=True) 

    # --- 3. Check Statuses and Set current_session ---
    mic_tested = getattr(session, 'mic_tested', False) 
    webcam_tested = getattr(session, 'webcam_tested', False) 
    rules_confirmed = getattr(session, 'rules_confirmed', False) 
    
    mic_status = "complete" if mic_tested else "incomplete"
    webcam_status = "complete" if webcam_tested else "incomplete"
    rules_status = "complete" if rules_confirmed else "incomplete"
    
    all_checks_passed = mic_tested and webcam_tested and rules_confirmed
    
    if all_checks_passed and session:
        request.session['current_session'] = session.id
    else:
        if 'current_session' in request.session:
            del request.session['current_session']

    # --- 4. Prepare Context and Render ---
    total_checks = 3
    passed_checks = sum([1 for status in [mic_status, webcam_status, rules_status] if status == 'complete'])
    progress_percent = round((passed_checks / total_checks) * 100) if total_checks > 0 else 0
        
    context = {
        "session": session, 
        "mic_status": mic_status,
        "webcam_status": webcam_status,
        "rules_status": rules_status,
        "current_username": user.username,
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "progress_percent": progress_percent, 
    }
    
    return render(request, "monitor/student_dashboard.html", context)


def admin_dashboard(request):
    # Renders the admin monitoring dashboard
    return render(request, 'monitor/admin_dashboard.html')


@staff_member_required
def proctor_view(request, candidate_id):
    """Renders the live monitoring page for a specific candidate."""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    session = Session.objects.filter(candidate=candidate, ended_at__isnull=True).order_by('-started_at').first()

    return render(request, "monitor/proctor_view.html", {
        'candidate': candidate,
        'session': session,
    })
# ==========================
# Exam Rules Page
# ==========================
@login_required
@login_required
def exam_rules(request):
    session_id = request.session.get("current_session")
    session = Session.objects.filter(id=session_id).first()

    if request.method == "POST":
        # Check if the user accepted the rules (by form submission)
        if request.POST.get('rules_accepted'): 
            
            if session:
                # 🚨 ACTION: Update the session status to confirm rules 🚨
                # Assuming you have a 'rules_confirmed' field on the Session model.
                # If not, you should create one in your models.py.
                # For this fix, let's assume a 'rules_confirmed' boolean field exists.
                session.rules_confirmed = True 
                session.save()
            
            # 🚀 FINAL FIX: Redirect to the student dashboard 🚀
            return redirect('student_dashboard')

    # If GET request, just render the page
    return render(request, "monitor/exam_rules.html", {"session": session})


# ==========================
# Mic Test Page
# ==========================
@login_required
def mic_test(request):
    return render(request, "monitor/mic_test.html")


# ==========================
# Webcam Test Page
# ==========================
@login_required
def webcam_test(request):
    return render(request, "monitor/webcam_test.html")


# ==========================
# Start Exam Page
# ==========================
@login_required
def start_exam(request):
    """
    Loads the main exam page if a valid session ID is found in the user's 
    browser session. Otherwise, redirects to the dashboard.
    """
    
    # 1. Retrieve the session ID from the user's browser session
    session_id = request.session.get("current_session")
    
    # 2. Look up the Session object using the Django Model Manager
    # .filter() returns a QuerySet, .first() returns the object or None.
    try:
        session = Session.objects.filter(id=session_id).first()
    except Exception as e:
        # Optional: Log the error if the filter fails for unexpected reasons
        print(f"Error fetching session in start_exam: {e}")
        session = None

    if not session:
        # If no session ID was found in the browser, or the session object 
        # doesn't exist in the database, redirect the user to setup.
        return redirect('student_dashboard') # Assuming you have this URL name defined
        
    # 3. Render the exam template, passing the valid Session object
    # The exam template uses {{ session.id }} and other session attributes.
    return render(request, "monitor/start_exam.html", {"session": session})


# ==========================
# Blocked Page
# ==========================
@login_required
def blocked_page(request):
    return render(request, "monitor/blocked.html")


# ==========================
# Start Session API
# ==========================
@login_required
@csrf_exempt
def start_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    user = request.user
    profile = getattr(user, "studentprofile", None)
    if not profile:
        return JsonResponse({"error": "Profile not found"}, status=404)

    candidate, _ = Candidate.objects.get_or_create(
        roll_number=profile.roll_number,
        defaults={"name": profile.full_name, "email": user.email}
    )

    session = Session.objects.create(candidate=candidate)
    request.session["current_session"] = session.id

    return JsonResponse({"status": "ok", "session_id": session.id})


# ==========================
# End Session API
# ==========================
@login_required
@csrf_exempt
def end_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    session_id = request.POST.get("session_id")
    if not session_id or not session_id.isdigit():
        return JsonResponse({"error": "Invalid session ID"}, status=400)

    session = Session.objects.filter(id=int(session_id)).first()
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)

    # Mark the session as ended by setting ended_at
    session.ended_at = datetime.datetime.now()
    session.save()

    return JsonResponse({"status": "ok", "completed": True})


# ==========================
# Upload Audio (Mic Test) API
# ==========================
@login_required
@csrf_exempt
def upload_audio(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    session_id = request.POST.get('session_id')
    if not session_id or not session_id.isdigit():
        return JsonResponse({"error": "Invalid session ID"}, status=400)

    session = Session.objects.filter(id=int(session_id)).first()
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)

    b64_audio = request.POST.get('audio')
    if not b64_audio:
        return JsonResponse({"error": "No audio data sent"}, status=400)

    try:
        header, data = b64_audio.split(',', 1) if ',' in b64_audio else (None, b64_audio)
        audio_bytes = base64.b64decode(data)
    except Exception as e:
        return JsonResponse({"error": f"Invalid audio data: {str(e)}"}, status=400)

    # Analyze audio with analyzer
    events = analyzer.analyze_audio(audio_bytes, session)

    for ev in events:
        Event.objects.create(
            session=session,
            event_type=ev.get("type", "audio"),
            details=ev.get("details", ""),
            score=ev.get("score", 0.0)
        )

    return JsonResponse({"status": "ok", "events": events})


# ==========================
# Start Exam / Upload Frame + Tab Switch Handling
# ==========================
@csrf_exempt
def upload_frame(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    session_id = request.POST.get('session_id')
    if not session_id or not session_id.isdigit():
        return JsonResponse({"error": "Invalid session ID"}, status=400)

    session = Session.objects.get(id=int(session_id))

    # ----------------------
    # Handle tab switch event
    # ----------------------
    tab_switch = request.POST.get('tab_switch')
    if tab_switch == "true":
        Event.objects.create(
            session=session,
            event_type="tab_switch",
            details="User switched tab or minimized window",
            score=1.0
        )
        session.suspicion_score += 1
        if session.suspicion_score >= 3:
            session.verdict = "suspicious"
            session.blocked = True
            # Ensure Candidate block reason is explicitly set
            if session.candidate:
                session.candidate.blocked = True
                session.candidate.blocked_reason = "Exceeded suspicious activity threshold"
                session.candidate.save()
        session.save()
        return JsonResponse({"status": "ok", "events": [{"type": "tab_switch", "details": "User switched tab"}], "blocked": session.blocked})

    # ----------------------
    # Handle webcam frame
    # ----------------------
    b64 = request.POST.get('frame')
    if not b64:
        return JsonResponse({"error": "No frame sent"}, status=400)

    try:
        header, data = b64.split(',', 1) if ',' in b64 else (None, b64)
        img_bytes = base64.b64decode(data)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        frame = np.array(img)[:, :, ::-1]  # RGB -> BGR
    except Exception as e:
        return JsonResponse({"error": f"Invalid image data: {str(e)}"}, status=400)

    # Analyze frame
    events = analyzer.analyze_frame(frame, session)

    # Save events to DB
    for ev in events:
        if 'frame' in ev:
            pil_img = Image.fromarray(ev['frame'][:, :, ::-1])
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG')
            buf.seek(0)
            name = f"{uuid.uuid4().hex}.jpg"
            django_file = InMemoryUploadedFile(buf, None, name, 'image/jpeg', buf.getbuffer().nbytes, None)
            Event.objects.create(
                session=session,
                event_type=ev['type'],
                details=ev.get('details', ''),
                frame_file=django_file,
                score=ev.get('score', 0.0)
            )
        else:
            Event.objects.create(
                session=session,
                event_type=ev['type'],
                details=ev.get('details', ''),
                score=ev.get('score', 0.0)
            )

    # Update suspicion score & block logic
    # NOTE: This uses inefficient session.events.all() for total_score, consider optimization.
    total_score = sum(e.score for e in session.events.all())
    session.suspicion_score = total_score
    if total_score >= 3:
        session.verdict = "suspicious"
        session.blocked = True
        if session.candidate:
            session.candidate.blocked = True
            session.candidate.blocked_reason = "Exceeded suspicious activity threshold"
            session.candidate.save()
    session.save()

    # Prepare JSON response
    events_serializable = []
    for ev in events:
        ev_copy = ev.copy()
        if 'frame' in ev_copy:
            pil_img = Image.fromarray(ev_copy['frame'][:, :, ::-1])
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG')
            buf.seek(0)
            ev_copy['frame'] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        events_serializable.append(ev_copy)

    return JsonResponse({'status': 'ok', 'events': events_serializable, 'blocked': session.blocked})


# ==========================
# Face Verification API (No Change)
# ==========================
@login_required
@csrf_exempt
def verify_face(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    session_id = request.POST.get('session_id')
    if not session_id or not session_id.isdigit():
        return JsonResponse({"error": "Invalid session ID"}, status=400)

    session = Session.objects.filter(id=int(session_id)).first()
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)

    b64_frame = request.POST.get('frame')
    if not b64_frame:
        return JsonResponse({"error": "No frame sent"}, status=400)

    try:
        header, data = b64_frame.split(',', 1) if ',' in b64_frame else (None, b64_frame)
        img_bytes = base64.b64decode(data)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        frame = np.array(img)[:, :, ::-1]  # RGB -> BGR
    except Exception as e:
        return JsonResponse({"error": f"Invalid image data: {str(e)}"}, status=400)

    candidate = session.candidate
    if not candidate:
        return JsonResponse({"error": "Candidate not found"}, status=404)

    try:
        result = DeepFace.verify(
            np.array(img),
            candidate.photo.path,  # assuming you have a 'photo' field in Candidate model
            enforce_detection=False
        )
        verified = result.get('verified', False)
        confidence = result.get('distance', 0.0)
    except Exception as e:
        return JsonResponse({"error": f"Face verification failed: {str(e)}"}, status=500)

    Event.objects.create(
        session=session,
        event_type="face_verification",
        details=f"Verified: {verified}, Confidence: {confidence:.4f}",
        score=0.0 if verified else 1.0
    )

    return JsonResponse({"status": "ok", "verified": verified, "confidence": confidence})


# ==========================
# Report Event API
# ==========================
@login_required
@csrf_exempt
def report_event(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        # Try to parse JSON from request body
        data = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        # Fallback to form data if not JSON
        data = request.POST.dict()

    # Get session - for now, use the user's active session or create a default
    try:
        session_id = data.get('session_id') or request.POST.get('session_id')
        
        if session_id and str(session_id).isdigit():
            session = Session.objects.filter(id=int(session_id)).first()
            if not session:
                return JsonResponse({"error": "Session not found"}, status=404)
        else:
            # If no session_id provided, try to get/create one for current user
            from django.utils import timezone
            candidate, _ = Candidate.objects.get_or_create(
                user=request.user,
                defaults={'status': 'active'}
            )
            session, _ = Session.objects.get_or_create(
                candidate=candidate,
                status='active',
                defaults={'started_at': timezone.now()}
            )
    except Exception as e:
        print(f"Session error: {e}")
        return JsonResponse({"error": f"Session error: {str(e)}"}, status=400)

    event_type = data.get('event_type') or request.POST.get('event_type')
    details = data.get('description') or data.get('details') or request.POST.get('details', '')
    
    if not event_type:
        return JsonResponse({"error": "Event type required"}, status=400)

    try:
        Event.objects.create(
            session=session,
            event_type=event_type,
            details=str(details),
            score=0.0
        )
        print(f"✅ Event logged: {event_type} - {details}")
    except Exception as e:
        print(f"❌ Error creating event: {e}")
        return JsonResponse({"error": f"Failed to create event: {str(e)}"}, status=500)

    return JsonResponse({"status": "ok", "message": "Event reported"})


# ==========================
# Get Sessions API
# ==========================
@staff_member_required
def get_sessions(request):
    """
    API endpoint to fetch real-time session data for the Admin Dashboard.
    """
    try:
        # NOTE: Filter out completed sessions if dashboard should only show active/recent
        sessions = Session.objects.select_related('candidate').order_by('-started_at') 
        session_list = []

        for s in sessions:
            candidate = s.candidate
            
            # Safely get last event details
            last_event_type = "No alerts"
            last_event = s.events.order_by('-timestamp').first() 
            
            if last_event:
                last_event_type = f"{last_event.event_type.replace('_', ' ').title()}: {last_event.details}"

            session_list.append({
                "id": s.id,
                "candidate_id": candidate.id if candidate else None,
                "candidate_name": candidate.name if candidate else "Unidentified",
                "roll_number": candidate.roll_number if candidate else "N/A",
                "photo_url": candidate.photo.url if candidate and candidate.photo else "/static/img/default-avatar.png",
                "suspicion_score": s.suspicion_score or 0.0,
                "verdict": s.verdict or "clean",
                
                # Blocked status pulled from Candidate model for persistence
                "blocked": candidate.blocked if candidate else False, 
                "block_reason": candidate.blocked_reason if candidate else None,
                
                "last_event_type": last_event_type,
                "active": s.active,
                "started_at": s.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ended_at": s.ended_at.strftime("%Y-%m-%d %H:%M:%S") if s.ended_at else "Active",
            })

        # Calculate summary statistics
        data = {
            "total_candidates": Candidate.objects.count(), 
            "active_sessions": Session.objects.filter(ended_at__isnull=True).count(),
            # Assuming Suspicious Events means sessions marked as 'suspicious' or 'blocked'
            "suspicious_events": Session.objects.filter(verdict__in=['suspicious', 'blocked']).count(),
            "clean_sessions": Session.objects.filter(verdict='clean', ended_at__isnull=True).count(),
            "sessions": session_list
        }
        
        return JsonResponse(data) 

    except Exception as e:
        print(f"Error in get_sessions view: {e}")
        return JsonResponse({"error": f"Internal API Error during processing: {str(e)}"}, status=500)
    # monitor/views.py (Insert this block)

# NOTE: Ensure json, datetime, and Candidate, Session models are imported.
# You need: import json, datetime 
# from .models import Candidate, Session 

@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def proctor_block_view(request):
    """
    Handles API request to block a candidate and all active sessions.
    (This view was referenced in monitor/urls.py, line 48)
    """
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        reason = data.get('reason', 'Manual block by Proctor') 
        
        if not candidate_id:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate ID.'}, status=400)

        # 1. Block the candidate (permanent status)
        candidate = Candidate.objects.get(id=candidate_id)
        candidate.blocked = True
        candidate.blocked_reason = reason
        candidate.save()

        # 2. Block all active sessions for this candidate
        Session.objects.filter(candidate=candidate, ended_at__isnull=True).update(
            blocked=True,
            verdict='blocked',
            ended_at=datetime.datetime.now()
        )
        
        return JsonResponse({'status': 'success', 'message': f'Candidate {candidate_id} blocked successfully.'})

    except Candidate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Candidate ID {candidate_id} not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def proctor_unblock_view(request):
    """
    Handles API request to unblock a candidate.
    """
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        
        if not candidate_id:
            return JsonResponse({'status': 'error', 'message': 'Missing candidate ID.'}, status=400)

        # 1. Unblock the candidate (permanent status)
        candidate = Candidate.objects.get(id=candidate_id)
        candidate.blocked = False
        candidate.blocked_reason = "" # Clear the reason
        candidate.save()
        
        # 2. Update any pending sessions back to clean/unblocked
        Session.objects.filter(candidate=candidate, ended_at__isnull=True, blocked=True).update(
             blocked=False,
             verdict='clean'
        )
        
        return JsonResponse({'status': 'success', 'message': f'Candidate {candidate_id} unblocked successfully.'})

    except Candidate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Candidate ID {candidate_id} not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)
@login_required
def exam_flow(request: HttpRequest):
    """
    Master exam flow page with step-by-step progression:
    1. Mic Test
    2. Webcam Test
    3. Rules Acceptance
    4. Start Exam
    """
    user = request.user
    candidate = None
    
    # Fetch candidate profile
    try:
        profile = getattr(user, 'studentprofile', None)
        if not profile:
            return redirect('user_logout')

        if hasattr(profile, 'roll_number'):
            candidate = Candidate.objects.get(roll_number=profile.roll_number)
            
            if candidate.blocked:
                return redirect('blocked_page') 
        else:
            return redirect('user_logout')

    except Candidate.DoesNotExist:
        return redirect('user_logout')
    except Exception as e:
        print(f"Error in exam_flow: {e}")
        return redirect('user_logout')

    # Get or create current session
    session = Session.objects.filter(candidate=candidate, active=True).first()
    if not session:
        session = Session.objects.create(candidate=candidate, active=True)
    
    request.session['current_session'] = session.id
    
    context = {
        "session": session,
        "candidate": candidate,
        "user": user,
    }
    
    return render(request, "monitor/exam_flow.html", context)


@login_required
@require_http_methods(["POST"])
def mark_step_complete(request: HttpRequest):
    """API to mark a step complete in the exam flow."""
    try:
        data = json.loads(request.body)
        step = data.get('step')  # 'mic', 'webcam', 'rules'
        
        session_id = request.session.get('current_session')
        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'No active session'}, status=400)
        
        session = Session.objects.get(id=session_id, candidate__studentprofile__user=request.user)
        
        if step == 'mic':
            session.mic_tested = True
        elif step == 'webcam':
            session.webcam_tested = True
        elif step == 'rules':
            session.rules_confirmed = True
        
        session.save()
        
        return JsonResponse({'status': 'success'})
    
    except Session.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def practice_exam_redirect(request):
    return redirect("http://127.0.0.1:5000")
# monitor/views.py (Add this function alongside your other API views)


