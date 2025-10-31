from django.urls import path
from . import views
# You don't need to import auth_views if you don't use their class-based views directly
# from django.contrib.auth import views as auth_views 
from django.urls import include # Keep include, but ensure it's not used incorrectly

urlpatterns = [
    # 1. BASE AND AUTHENTICATION HANDLERS
    # The root path. Must be UNPROTECTED.
    path('', views.index, name='index'), 

    # CRITICAL FIX: The ONLY path for handling login POST/GET (Maps to custom logic)
    path('login/', views.handle_unified_login, name='login'), 
    
    # Logout is handled by your custom view which calls django.contrib.auth.logout()
    path('logout/', views.user_logout, name='logout'),
    
    # Post-login router
    path('post-login-redirect/', views.redirect_to_dashboard, name='post_login_redirect'),
    
    # 2. DASHBOARDS (Cleaned up redundant definitions)
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Dashboards (Aliases: Assuming these should be kept for compatibility, but recommend using the /dashboard/ path)
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
   

    # 3. EXAM AND APP PAGES
    path('exam-flow/', views.exam_flow, name='exam_flow'),  # NEW: Master exam flow with step-by-step
    path('mic-test/', views.mic_test, name='mic_test'),
    path('webcam-test/', views.webcam_test, name='webcam_test'),
    path('exam-rules/', views.exam_rules, name='exam_rules'),
    path('start-exam/', views.start_exam, name='start_exam'),
    path('blocked/', views.blocked_page, name='blocked_page'),
    
    # 🛑 REMOVED CONFLICTING LINES: 🛑
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),  <-- Duplicates your user_logout view
    # path('accounts/', include('django.contrib.auth.urls')),          <-- Causes TemplateDoesNotExist error

    # 4. API ENDPOINTS
    path('api/start-session/', views.start_session, name='start_session_api'),
    path('api/upload-frame/', views.upload_frame, name='upload_frame'),
    path('api/upload-audio/', views.upload_audio, name='upload_audio'),
    path('api/end-session/', views.end_session, name='end_session'),
    path('api/verify-face/', views.verify_face, name='verify_face'),
    path('api/report-event/', views.report_event, name='report_event'),
    path('api/get_sessions/', views.get_sessions, name='get_sessions_api'),
    path('api/block/', views.proctor_block_view, name='proctor_block'),
    path('api/unblock/', views.proctor_unblock_view, name='proctor_unblock'),
    path('api/mark-step/', views.mark_step_complete, name='mark_step_complete'),  # NEW: Mark exam flow step
    path('api/submit-exam/', views.submit_exam, name='submit_exam'),  # NEW: Submit exam
    
    # 5. PROCTOR VIEWS
    path('proctor/view/<int:candidate_id>/', views.proctor_view, name='proctor_view'),
    
    # 6. EXAM RESULTS AND CERTIFICATE
    path('result/<int:session_id>/', views.exam_result, name='exam_result'),
    path('certificate/<int:session_id>/download/', views.generate_certificate, name='generate_certificate'),
    path('certificate/<int:session_id>/preview/', views.preview_certificate, name='preview_certificate'),
    
    # URL to mark a quiz/code challenge complete
  
]