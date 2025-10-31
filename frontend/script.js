document.addEventListener('DOMContentLoaded', () => {
    let courses = JSON.parse(localStorage.getItem('studyCourses')) || [];
    let activeCourseIndex = null;
    let currentDayIndex = 0;
    let deleteCourseIndex = null;
    let deleteCountdownInterval = null;
    let isCountdownFinished = false; // FLAG for delete logic

    // --- Selectors ---
    const courseListView = document.getElementById('course-list-view');
    const dashboardView = document.getElementById('dashboard-view');
    const addCourseModal = document.getElementById('add-course-modal');
    const coursesContainer = document.getElementById('courses-container');
    const emptyStateContainer = document.getElementById('empty-state-container');
    const homeLogoBtn = document.getElementById('home-logo-btn');
    const addCourseBtn = document.getElementById('add-course-btn');
    const addCoursePlanBtn = document.getElementById('add-course-plan-btn');
    const addCourseForm = document.getElementById('add-course-form');
    
    const themeToggle = document.getElementById('theme-toggle');
    const simpleDeleteModal = document.getElementById('simple-delete-modal');
    const complexDeleteModal = document.getElementById('complex-delete-modal');
    const simpleDeleteConfirmBtn = document.getElementById('simple-delete-confirm-btn');
    const complexDeleteConfirmBtn = document.getElementById('complex-delete-confirm-btn');
    const deleteConfirmInput = document.getElementById('delete-confirm-input');
    const deleteErrorMsg = document.getElementById('delete-error-msg');
    const deleteCountdownEl = document.getElementById('delete-countdown');
    
    // Video & Notes Selectors
    const videoPlayerContainer = document.getElementById('video-player-container');
    const videoPlayerIframeWrapper = document.getElementById('video-player-iframe-wrapper');
    const notesSection = document.getElementById('notes-section');
    const notesEditor = document.getElementById('notes-editor');
    const saveNotesBtn = document.getElementById('save-notes-btn');
    const downloadNotesBtn = document.getElementById('download-notes-btn');

    // Toolbar button selectors
    const notesBold = document.getElementById('notes-bold');
    const notesItalic = document.getElementById('notes-italic');
    const notesUnderline = document.getElementById('notes-underline');
    const formatBlockSelect = document.getElementById('formatBlockSelect');
    const fontSizeSelect = document.getElementById('fontSizeSelect');

    // Quiz View Selectors
    const quizView = document.getElementById('quiz-view');
    const quizViewTitle = document.getElementById('quiz-view-title');
    const quizProgressText = document.getElementById('quiz-progress-text');
    const quizProgressBar = document.getElementById('quiz-progress-bar');
    const quizQuestionContainer = document.getElementById('quiz-question-container');
    const quizQuestionText = document.getElementById('quiz-question-text');
    const quizOptionsContainer = document.getElementById('quiz-options-container');
    const quizResultsContainer = document.getElementById('quiz-results-container');
    const quizResultsIcon = document.getElementById('quiz-results-icon');
    const quizResultsScore = document.getElementById('quiz-results-score');
    const quizResultsSummary = document.getElementById('quiz-results-summary');
    const quizFinishBtn = document.getElementById('quiz-finish-btn');
    
    // Quiz State
    let currentQuiz = [];
    let currentQuizQuestionIndex = 0;
    let currentQuizScore = 0;
    let currentQuizDayIndex = 0;

    // --- NEW: Practice Lab Selectors ---
    const labView = document.getElementById('lab-view');
    const labTitle = document.getElementById('lab-title');
    const labCloseBtn = document.getElementById('lab-close-btn');
    const labQuestion = document.getElementById('lab-question');
    const labRunCodeBtn = document.getElementById('lab-run-code-btn');
    const labTabBtns = document.querySelectorAll('.lab-tab-btn');
    const labTabContents = document.querySelectorAll('.lab-tab-content');
    const htmlEditor = document.getElementById('html-editor');
    const cssEditor = document.getElementById('css-editor');
    const jsEditor = document.getElementById('js-editor');
    const labPreviewIframe = document.getElementById('lab-preview-iframe');
    const labChatMessages = document.getElementById('lab-chat-messages');
    const labChatInput = document.getElementById('lab-chat-input');
    const labGetHintBtn = document.getElementById('lab-get-hint-btn');

    // --- NEW: Practice Lab State ---
    let currentLabChallenge = null;
    let labTryCount = 0;


    // --- Helper to get YouTube Video ID ---
    function getYoutubeVideoID(url) {
        let videoID = '';
        try {
            const urlObj = new URL(url);
            if (urlObj.hostname === 'youtu.be') {
                videoID = urlObj.pathname.slice(1);
            } else if (urlObj.hostname === 'www.youtube.com' || urlObj.hostname === 'youtube.com') {
                videoID = urlObj.searchParams.get('v');
            }
        } catch (e) {
            console.error("Invalid URL:", e);
            return null;
        }
        return videoID;
    }

    // --- Event Listeners ---
    homeLogoBtn.addEventListener('click', showCourseListView);
    [addCourseBtn, addCoursePlanBtn].forEach(btn => btn.addEventListener('click', () => addCourseModal.classList.remove('hidden')));
    document.querySelectorAll('.cancel-modal-btn, .close-modal-btn').forEach(btn => btn.addEventListener('click', (e) => {
        e.target.closest('.modal-overlay').classList.add('hidden');
        if (e.target.closest('.modal-overlay') === complexDeleteModal) {
            clearInterval(deleteCountdownInterval); // Stop countdown on close
        }
    }));

    // --- Add Course (CONNECTED TO BACKEND) ---
    addCourseForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const courseTitle = document.getElementById('course-title-input').value.trim();
        const courseLink = document.getElementById('course-link-input').value.trim();
        const dailyStudyHours = parseInt(document.getElementById('study-hours-input').value);
        
        if (!getYoutubeVideoID(courseLink)) {
            alert("Please enter a valid YouTube link.");
            return;
        }

        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.textContent = 'Generating...';
        submitButton.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:5000/generate-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    courseTitle,
                    courseLink, 
                    dailyStudyHours 
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate plan.');
            }

            const newCourse = await response.json();
            
            // Add 'notes' and 'download' property to each module
            newCourse.dailyPlan.forEach(day => {
                day.notes = ''; // For rich text editor
                day.quickNotes = ''; // For quick notes tab
                day.isVideoDownloaded = false;
                day.challenge = null; // For caching challenge
            });
            
            courses.push(newCourse);
            saveCourses();
            activeCourseIndex = courses.length - 1;
            showDashboardView(activeCourseIndex);
            addCourseModal.classList.add('hidden');
            e.target.reset();
        } catch (error) {
            alert(`Error: ${error.message}`);
            console.error('Fetch error:', error);
        } finally {
            submitButton.textContent = 'Create Plan';
            submitButton.disabled = false;
        }
    });

    // --- Core ---
    function saveCourses() {
        localStorage.setItem('studyCourses', JSON.stringify(courses));
    }

    // --- Views ---
    function showCourseListView() {
        // FIX: Re-load courses from storage every time we show the list
        // This fixes the "vanishing card" bug.
        courses = JSON.parse(localStorage.getItem('studyCourses')) || [];
        
        dashboardView.classList.add('hidden');
        courseListView.classList.remove('hidden');
        videoPlayerContainer.classList.add('hidden'); // Hide the whole video/notes container
        renderCourseList();
    }

    function showDashboardView(index) {
        if (index === null || !courses[index]) {
            console.error("Invalid index or course not found.", index, courses);
            return; // Exit if index is bad
        }
        activeCourseIndex = index;
        const course = courses[index];
        currentDayIndex = course.dailyPlan.findIndex(d => !d.completed);
        if (currentDayIndex === -1) currentDayIndex = 0;
        courseListView.classList.add('hidden');
        dashboardView.classList.remove('hidden');
        renderDashboard(course);
    }

    function showVideoPlayer(videoID, start, end) {
        const embedUrl = `https://www.youtube.com/embed/${videoID}?start=${start}&end=${end}&autoplay=1&rel=0`;
        videoPlayerIframeWrapper.innerHTML = `<iframe src="${embedUrl}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
        videoPlayerContainer.classList.remove('hidden'); // Show the whole card
        videoPlayerContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Load notes for the current module
        loadNotes();
    }

    // --- Rendering ---
    function renderCourseList() {
        coursesContainer.innerHTML = '';
        if (courses.length === 0) {
            emptyStateContainer.classList.remove('hidden');
            coursesContainer.classList.add('hidden'); // Hide the grid
            return;
        }

        emptyStateContainer.classList.add('hidden');
        coursesContainer.classList.remove('hidden'); // Show the grid

        courses.forEach((course, index) => {
            const card = document.createElement('div');
            card.className = 'card course-card';
            const statusClass = course.progress === 100 ? 'completed' : 'in-progress';
            const statusText = course.progress === 100 ? 'Completed' : 'In Progress';
            
            const gradients = [
                ['#a18cd1', '#fbc2eb'], ['#ff9a9e', '#fecfef'], ['#84fab0', '#8fd3f4'], 
                ['#f6d365', '#fda085'], ['#d4fc79', '#96e6a1'], ['#a1c4fd', '#c2e9fb']
            ];
            const gradient = gradients[index % gradients.length];
            const gradientPlaceholder = `https://placehold.co/600x360/${gradient[0].substring(1)}/${gradient[1].substring(1)}?text=${encodeURIComponent(course.courseTitle.split(' ').slice(0,3).join(' '))}&font=manrope`;

            const videoID = course.videoID;
            const thumbnailUrlMax = `https://img.youtube.com/vi/${videoID}/maxresdefault.jpg`;
            const thumbnailUrlHq = `https://img.youtube.com/vi/${videoID}/hqdefault.jpg`;
            
            const onErrorScript = `this.onerror=null; this.src='${thumbnailUrlHq}'; this.onerror=function(){this.onerror=null; this.src='${gradientPlaceholder}';}`;

            card.innerHTML = `
                <img class="course-card-image" src="${thumbnailUrlMax}" alt="${course.courseTitle} banner" onerror="${onErrorScript}">
                <div class="course-card-content">
                    <h3>${course.courseTitle}</h3>
                    <p>${course.courseDescription || 'No description available.'}</p>
                </div>
                <div> <!-- Wrapper for footer -->
                    <div class="course-card-footer">
                        <div class="status-badge ${statusClass}">${statusText}</div>
                        <span>${course.progress}% Complete</span>
                    </div>
                    <div class="course-card-actions">
                        <button class="btn btn-danger delete-course-btn" data-index="${index}"><i class="fas fa-trash"></i> Delete</button>
                    </div>
                </div>
            `;
    
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-course-btn')) {
                    showDashboardView(index);
                }
            });
            
            card.querySelector('.delete-course-btn').addEventListener('click', (e) => {
                e.stopPropagation(); 
                openDeleteModal(index);
            });
            coursesContainer.appendChild(card);
        });
    }

    async function renderDashboard(course) { // Made async
        if (!course) {
            console.error("renderDashboard called with no course.");
            showCourseListView(); 
            return;
        }
        renderCourseHeader(course);
        renderProgressOverview(course);
        renderDailyPlan(course.dailyPlan);
        await renderCourseModule(course.dailyPlan[currentDayIndex]); // Await this
    }

    function renderCourseHeader(course) {
        const headerEl = document.getElementById('course-header');
        headerEl.innerHTML = `
            <div class="course-header-text">
                <h1>${course.courseTitle}</h1>
                <p>${course.courseDescription || 'No description available.'}</p>
            </div>
            <div class="course-header-actions">
                <div class="streak-counter">🔥 ${course.streak || 0} Day Streak</div>
            </div>
        `;
    }
    
    function renderProgressOverview(course) {
        const overviewEl = document.getElementById('progress-overview');
        const completedModules = course.dailyPlan.filter(d => d.completed).length;
        const totalModules = course.dailyPlan.length;
        
        overviewEl.innerHTML = `
            <h2>Progress Overview</h2>
            <p>${completedModules} of ${totalModules} modules completed (${course.progress}%)</p>
            <div class="progress-bar-bg">
                <div class="progress-bar-fg" style="width: ${course.progress}%;"></div>
            </div>
        `;
    }

    
    function renderDailyPlan(plan) {
        const planListEl = document.getElementById('daily-plan-list');
        planListEl.innerHTML = '';
        if (!plan) return; 
        
        const firstIncompleteIndex = plan.findIndex(d => !d.completed);

        plan.forEach((day, index) => {
            const isCurrent = index === currentDayIndex;
            const isCompleted = day.completed;
            const isLocked = !isCurrent && !isCompleted && (index > firstIncompleteIndex && firstIncompleteIndex !== -1);

            let statusIcon = '';
            let statusClass = '';

            if (isCompleted) {
                statusIcon = '<i class="fas fa-check-circle"></i>';
                statusClass = 'completed';
            } else if (isCurrent) {
                statusIcon = '<i class="fas fa-play-circle"></i>';
                statusClass = 'current';
            } else if (isLocked) {
                statusIcon = '<i class="fas fa-lock"></i>';
                statusClass = 'locked';
            } else {
                statusIcon = '<i class="far fa-circle"></i>'; // Simple circle
                statusClass = 'todo';
            }


            const totalTime = day.totalDuration || (day.duration + (day.quizDuration || 0));
            const videoTime = day.duration || 1;
            const quizTime = day.quizDuration || 0.15;

            const item = document.createElement('div');
            item.className = `day-item ${statusClass}`;
            item.innerHTML = `
                <div class="day-number">${day.day}</div>
                <div class="day-info">
                    <h3>${day.title}</h3>
                    <p>
                        <span><i class="fas fa-clock"></i> ${totalTime.toFixed(1)}h total</span>
                        <span><i class="fas fa-video"></i> ${videoTime.toFixed(1)}h</span>
                        <span><i class="fas fa-puzzle-piece"></i> ${quizTime.toFixed(1)}h</span>
                    </p>
                </div>
                <div class="day-status-icon">${statusIcon}</div>
            `;
            if (!isLocked) {
                item.addEventListener('click', () => {
                    currentDayIndex = index;
                    videoPlayerContainer.classList.add('hidden'); // Hide video/notes
                    renderDashboard(courses[activeCourseIndex]);
                });
            }

            planListEl.appendChild(item);
        });
    }

    // --- UPDATED: Renders the new Module Tab UI ---
    async function renderCourseModule(dayData) { // Made async
        const modulesSection = document.getElementById('course-modules-section');
        if (!dayData) {
             modulesSection.innerHTML = `<h2 class="module-section-header">Module not found</h2><div class="card"><p>Could not load module data.</p></div>`;
             return;
        }

        const firstIncompleteIndex = courses[activeCourseIndex].dailyPlan.findIndex(d => !d.completed);
        const isLocked = dayData.day - 1 > firstIncompleteIndex && firstIncompleteIndex !== -1;

        if (isLocked) {
            document.getElementById('module-section-title').textContent = `Day ${dayData.day}: ${dayData.title}`;
            modulesSection.querySelector('.card').innerHTML = `<p>🔒 This module is locked. Complete the previous day's module to unlock it.</p>`;
            return;
        }

        // --- NEW: Fetch challenge data ---
        const challenge = await fetchChallenge(dayData);
        let practiceLabBtn = '';
        if (challenge && challenge.type !== 'none') {
            practiceLabBtn = `<button class="btn btn-primary practice-lab-btn" data-day-index="${dayData.day - 1}"><i class="fas fa-laptop-code"></i> Practice Lab</button>`;
        }
        // --- End new challenge logic ---

        const totalTime = dayData.totalDuration || (dayData.duration + (dayData.quizDuration || 0));
        const videoTime = dayData.duration || 1;
        const quizTime = dayData.quizDuration || 0.15;

        // --- Populate Title ---
        document.getElementById('module-section-title').textContent = `Day ${dayData.day}: ${dayData.title}`;

        // --- Populate Info Boxes ---
        document.getElementById('info-box-video').innerHTML = `
            <div class="info-icon"><i class="fas fa-video"></i></div>
            <div class="info-text">
                <strong>Video Learning</strong>
                <span>${videoTime.toFixed(1)} hours (85%)</span>
            </div>`;
        document.getElementById('info-box-quiz').innerHTML = `
            <div class="info-icon"><i class="fas fa-puzzle-piece"></i></div>
            <div class="info-text">
                <strong>Quiz Assessment</strong>
                <span>${quizTime.toFixed(1)} hours (15%)</span>
            </div>`;
        document.getElementById('info-box-total').innerHTML = `
            <div class="info-icon"><i class="fas fa-clock"></i></div>
            <div class="info-text">
                <strong>Total Time</strong>
                <span>${totalTime.toFixed(1)} hours</span>
            </div>`;

        // --- Populate Tabs ---
        document.getElementById('module-summary-text').textContent = dayData.module.description;
        document.getElementById('module-key-points-list').innerHTML = 
            dayData.module.keyPoints.map(p => `<li><i class="fas fa-check"></i> ${p}</li>`).join('');
        
        // --- Populate Quick Notes ---
        const quickNotesEditor = document.getElementById('quick-notes-editor');
        quickNotesEditor.value = dayData.quickNotes || '';
        // Add event listener for saving quick notes
        document.getElementById('save-quick-notes-btn').onclick = () => {
            dayData.quickNotes = quickNotesEditor.value;
            saveCourses();
            const btn = document.getElementById('save-quick-notes-btn');
            btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
            setTimeout(() => {
                btn.innerHTML = '<i class="fas fa-save"></i> Save Quick Note';
            }, 2000);
        };

        // --- Handle Tab Switching ---
        const moduleTabBtns = modulesSection.querySelectorAll('.module-tab-btn');
        const moduleTabContents = modulesSection.querySelectorAll('.module-tab-content');
        moduleTabBtns.forEach(btn => {
            btn.onclick = () => {
                moduleTabBtns.forEach(b => b.classList.remove('active'));
                moduleTabContents.forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(btn.dataset.tab).classList.add('active');
            };
        });
        // Reset to first tab
        moduleTabBtns[0].classList.add('active');
        moduleTabContents[0].classList.add('active');
        moduleTabBtns[1].classList.remove('active');
        moduleTabContents[1].classList.remove('active');
        moduleTabBtns[2].classList.remove('active');
        moduleTabContents[2].classList.remove('active');


        // --- Populate Action Buttons ---
        let watchVideoBtn = `<button class="btn btn-primary watch-video-btn" data-day-index="${dayData.day - 1}">▶ Watch Video (${videoTime.toFixed(1)}h)</button>`;
        let downloadVideoBtn = '';
        if (dayData.isVideoDownloaded) {
            downloadVideoBtn = `<button class="btn btn-completed" disabled><i class="fas fa-check"></i> Video Downloaded</button>`;
        } else {
            downloadVideoBtn = `<button class="btn btn-secondary download-video-btn" data-day-index="${dayData.day - 1}"><i class="fas fa-download"></i> Download Video</button>`;
        }
        let quizBtn = `<button class="btn btn-outline take-quiz-btn" data-day-index="${dayData.day - 1}"><i class="fas fa-vial"></i> Take Quiz (${quizTime.toFixed(1)}h)</button>`;
        
        // --- NEW: Download Notes Button ---
        let downloadNotesBtn = `<button class="btn btn-secondary download-notes-doc-btn"><i class="fas fa-file-word"></i> Download Notes (.docx)</button>`;

        let actionButtonsHTML = dayData.completed
            ? `<button class="btn btn-completed">Completed ✓</button>`
            : `${watchVideoBtn} ${quizBtn}`;
        
        actionButtonsHTML += practiceLabBtn + downloadVideoBtn + downloadNotesBtn;
        
        document.getElementById('module-actions-container').innerHTML = actionButtonsHTML;

        // --- Add Event Listeners for Buttons ---
        modulesSection.querySelector('.watch-video-btn')?.addEventListener('click', () => showVideoPlayer(courses[activeCourseIndex].videoID, dayData.startTime || 0, dayData.endTime || 0));
        modulesSection.querySelector('.take-quiz-btn')?.addEventListener('click', () => startQuiz(dayData));
        modulesSection.querySelector('.download-video-btn')?.addEventListener('click', (e) => downloadVideo(e.target, dayData.day - 1));
        modulesSection.querySelector('.practice-lab-btn')?.addEventListener('click', () => startPracticeLab(dayData));
        modulesSection.querySelector('.download-notes-doc-btn')?.addEventListener('click', (e) => downloadNotesDoc(e.target, dayData));
    }
    
    
    async function markDayAsComplete(dayIndex) {
        const course = courses[activeCourseIndex];
        const day = course.dailyPlan[dayIndex];
        if (day.completed) return;

        day.completed = true;
        course.streak = (course.streak || 0) + 1;
        const completedCount = course.dailyPlan.filter(d => d.completed).length;
        course.progress = Math.round((completedCount / course.dailyPlan.length) * 100);
        saveCourses();
        // Re-render dashboard to show progress
        await renderDashboard(course); 

        // Fetch motivation message from backend
        try {
            const response = await fetch('http://127.0.0.1:5000/get-motivation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ moduleTitle: day.title, courseTitle: course.courseTitle }),
            });
            const data = await response.json();
            // We don't need to alert() it here, the quiz results page shows the summary.
            console.log("Motivation:", data.message);
        } catch (error) {
            console.error("Could not fetch motivation:", error);
        }
    }

    // --- NEW: Quiz Logic (Full Screen & Backend Connected) ---

    async function startQuiz(dayData) {
        currentQuizDayIndex = dayData.day - 1;

        // Check if quiz data is already loaded
        if (!dayData.quiz || dayData.quiz.length === 0) {
            // Show loading state in quiz modal (optional)
            quizViewTitle.textContent = "Generating Quiz...";
            quizQuestionContainer.classList.add('hidden');
            quizResultsContainer.classList.add('hidden');
            quizView.classList.remove('hidden');

            try {
                // Fetch from backend
                const response = await fetch('http://127.0.0.1:5000/generate-quiz', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        moduleTitle: dayData.title, 
                        keyPoints: dayData.module.keyPoints 
                    }),
                });

                if (!response.ok) throw new Error("Failed to generate quiz.");
                
                const quizData = await response.json();
                
                // Save fetched quiz to our main data object
                courses[activeCourseIndex].dailyPlan[currentQuizDayIndex].quiz = quizData;
                saveCourses();
                
                currentQuiz = quizData;
            } catch (error) {
                console.error("Quiz generation failed:", error);
                alert("Could not load the quiz. Please try again.");
                quizView.classList.add('hidden');
                return;
            }
        } else {
            // Quiz data already exists
            currentQuiz = dayData.quiz;
        }

        // Start the quiz
        currentQuizQuestionIndex = 0;
        currentQuizScore = 0;
        
        quizViewTitle.textContent = `${dayData.title} - Quiz`;
        quizResultsContainer.classList.add('hidden');
        quizQuestionContainer.classList.remove('hidden');
        
        if (quizView.classList.contains('hidden')) {
            quizView.classList.remove('hidden');
        }
        
        showQuizQuestion();
    }

    function showQuizQuestion() {
        const question = currentQuiz[currentQuizQuestionIndex];
        const totalQuestions = currentQuiz.length;

        // Update progress
        quizProgressText.textContent = `Question ${currentQuizQuestionIndex + 1} of ${totalQuestions}`;
        quizProgressBar.style.width = `${((currentQuizQuestionIndex + 1) / totalQuestions) * 100}%`;

        // Update question
        quizQuestionText.textContent = question.question;

        // Create options
        quizOptionsContainer.innerHTML = '';
        Object.entries(question.options).forEach(([key, val]) => {
            const optionBtn = document.createElement('button');
            optionBtn.className = 'quiz-option-btn';
            optionBtn.dataset.key = key;
            optionBtn.innerHTML = `
                <span class="option-letter">${key}</span>
                <span class="option-text">${val}</span>
            `;
            optionBtn.addEventListener('click', () => selectQuizAnswer(optionBtn, key, question.correct_answer));
            quizOptionsContainer.appendChild(optionBtn);
        });
    }

    function selectQuizAnswer(selectedButton, selectedKey, correctKey) {
        // Disable all buttons
        document.querySelectorAll('.quiz-option-btn').forEach(btn => {
            btn.disabled = true;
            // Mark other buttons
            if (btn.dataset.key !== selectedKey) {
                btn.classList.add('is-other');
            }
        });

        if (selectedKey === correctKey) {
            // Correct
            selectedButton.classList.add('is-correct');
            currentQuizScore++;
        } else {
            // Incorrect
            selectedButton.classList.add('is-incorrect');
            // Highlight the correct one
            const correctBtn = document.querySelector(`.quiz-option-btn[data-key="${correctKey}"]`);
            if (correctBtn) {
                correctBtn.classList.add('is-correct');
                correctBtn.classList.remove('is-other');
            }
        }

        // Wait, then move to next question or results
        setTimeout(() => {
            currentQuizQuestionIndex++;
            if (currentQuizQuestionIndex < currentQuiz.length) {
                showQuizQuestion();
            } else {
                showQuizResults();
            }
        }, 1500); // 1.5 second delay to see feedback
    }

    function showQuizResults() {
        quizQuestionContainer.classList.add('hidden');
        quizResultsContainer.classList.remove('hidden');

        const score = currentQuizScore;
        const total = currentQuiz.length;
        const percentage = Math.round((score / total) * 100);

        quizResultsScore.textContent = `Your Score: ${score} / ${total} (${percentage}%)`;

        if (percentage === 100) {
            quizResultsIcon.innerHTML = `<i class="fas fa-trophy"></i>`;
            quizResultsIcon.className = 'is-perfect';
            quizResultsSummary.textContent = "Perfect! You aced it. Marking this module as complete.";
            markDayAsComplete(currentQuizDayIndex);
        } else if (percentage >= 70) {
            quizResultsIcon.innerHTML = `<i class="fas fa-check-circle"></i>`;
            quizResultsIcon.className = 'is-good';
            quizResultsSummary.textContent = "Great job! You must get 100% to complete the module.";
        } else {
            quizResultsIcon.innerHTML = `<i class="fas fa-times-circle"></i>`;
            quizResultsIcon.className = 'is-fail';
            quizResultsSummary.textContent = "Keep trying! You must get 100% to complete the module.";
        }
    }

    quizFinishBtn.addEventListener('click', () => {
        quizView.classList.add('hidden');
        // Re-render dashboard to show completion status if changed
        renderDashboard(courses[activeCourseIndex]);
    });


    // --- NEW: Delete Logic (Cooldown) ---
    
    function checkDeleteButtonState() {
        const isTextCorrect = deleteConfirmInput.value === 'CONFIRM TO DELETE COURSE';
        if (isCountdownFinished && isTextCorrect) {
            complexDeleteConfirmBtn.disabled = false;
        } else {
            complexDeleteConfirmBtn.disabled = true;
        }
    }

    function openDeleteModal(index) {
        deleteCourseIndex = index;
        if (!courses[deleteCourseIndex]) {
            console.error("Delete modal opened with invalid index.");
            return;
        }
        const course = courses[index];
        
        if (course.progress === 100) {
            simpleDeleteModal.classList.remove('hidden');
        } else {
            complexDeleteModal.classList.remove('hidden');
            startDeleteCountdown();
        }
    }

    function startDeleteCountdown() {
        clearInterval(deleteCountdownInterval);
        isCountdownFinished = false; // Reset flag
        let timeLeft = 10;
        deleteCountdownEl.textContent = timeLeft;
        deleteCountdownEl.style.color = 'var(--danger-color)'; // Reset color
        deleteConfirmInput.value = '';
        deleteErrorMsg.classList.add('hidden');
        complexDeleteConfirmBtn.disabled = true;

        deleteCountdownInterval = setInterval(() => {
            timeLeft--;
            deleteCountdownEl.textContent = timeLeft;
            if (timeLeft <= 0) {
                clearInterval(deleteCountdownInterval);
                isCountdownFinished = true; // Set flag
                deleteCountdownEl.textContent = "✔";
                deleteCountdownEl.style.color = 'var(--completed-color)';
                checkDeleteButtonState(); // Check if text is already correct
            }
        }, 1000);
    }

    deleteConfirmInput.addEventListener('input', () => {
        const typedText = deleteConfirmInput.value;
        if (typedText.length > 0 && !'CONFIRM TO DELETE COURSE'.startsWith(typedText)) {
            deleteErrorMsg.classList.remove('hidden');
        } else {
            deleteErrorMsg.classList.add('hidden');
        }
        checkDeleteButtonState();
    });

    complexDeleteConfirmBtn.addEventListener('click', () => {
        if (deleteConfirmInput.value === 'CONFIRM TO DELETE COURSE' && isCountdownFinished) {
            deleteCourse();
        } else {
            deleteErrorMsg.classList.remove('hidden');
        }
    });
    
    simpleDeleteConfirmBtn.addEventListener('click', deleteCourse);

    function deleteCourse() {
        clearInterval(deleteCountdownInterval);
        if (deleteCourseIndex === null) return;
        
        courses.splice(deleteCourseIndex, 1);
        saveCourses();

        // FIX: Check if the *active* course is the one being deleted
        if (deleteCourseIndex === activeCourseIndex) {
            activeCourseIndex = null;
            currentDayIndex = 0;
            showCourseListView(); // Go back to home view
        } else {
            // If a different course was deleted, just re-render the list
            renderCourseList();
            // And if we are in the dashboard, force a re-render
            if (!dashboardView.classList.contains('hidden')) {
                // Adjust activeCourseIndex if it was after the deleted one
                if (activeCourseIndex > deleteCourseIndex) {
                    activeCourseIndex--;
                }
                renderDashboard(courses[activeCourseIndex]);
            }
        }
        
        // FIX: Explicitly hide both modals
        simpleDeleteModal.classList.add('hidden');
        complexDeleteModal.classList.add('hidden');
        deleteCourseIndex = null;
    }

    // --- NEW: Download .docx Notes ---
    // Helper function to convert hex string to byte array
    function hexToBytes(hex) {
        let bytes = new Uint8Array(hex.length / 2);
        for (let i = 0; i < hex.length; i += 2) {
            bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
        }
        return bytes;
    }

    async function downloadNotesDoc(button, dayData) {
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating...`;

        try {
            const response = await fetch('http://127.0.0.1:5000/generate-notes-doc', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    moduleTitle: dayData.title, 
                    summary: dayData.module.description,
                    keyPoints: dayData.module.keyPoints
                }),
            });
            if (!response.ok) throw new Error("Failed to generate .docx file.");

            const data = await response.json();
            const fileBlobHex = data.file_blob;
            const fileName = data.file_name;

            // Convert hex string back to bytes
            const bytes = hexToBytes(fileBlobHex);
            const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);

            button.innerHTML = `<i class="fas fa-check"></i> Downloaded!`;
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = `<i class="fas fa-file-word"></i> Download Notes (.docx)`;
            }, 3000);

        } catch (error) {
            console.error("Failed to download .docx:", error);
            button.disabled = false;
            button.innerHTML = `<i class="fas fa-file-word"></i> Download Notes (.docx)`;
            alert("Sorry, could not generate the notes document.");
        }
    }
    
    // --- NEW: SIMULATED Video Download ---
    function downloadVideo(button, dayIndex) {
        if (!button) return;
        
        // 1. Set to loading state
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Downloading...`;
        
        // 2. Simulate download time (3 seconds)
        setTimeout(() => {
            // 3. Update data model
            courses[activeCourseIndex].dailyPlan[dayIndex].isVideoDownloaded = true;
            saveCourses();
            
            // 4. Update button to "Downloaded" state
            button.innerHTML = `<i class="fas fa-check"></i> Video Downloaded`;
            button.classList.remove('btn-secondary');
            button.classList.add('btn-completed');
            // button remains disabled
            
        }, 3000);
    }

    // --- NEW: Upgraded Notes Editor Logic ---
    
    // Standard commands
    document.querySelectorAll('.notes-toolbar .notes-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.execCommand(btn.dataset.command, false, null);
            notesEditor.focus();
            updateToolbarState(); // Update state after command
        });
    });
    
    // Select commands (value is needed)
    document.querySelectorAll('.notes-toolbar .notes-select').forEach(select => {
        select.addEventListener('change', (e) => {
            document.execCommand(e.target.dataset.command, false, e.target.value);
            if (e.target.dataset.command === 'fontSize') {
                e.target.value = '3'; // Reset font size select to default
            }
            notesEditor.focus();
            updateToolbarState(); // NEW: Update state after command
        });
    });

    // Color picker
    document.querySelector('.notes-toolbar .notes-color-picker').addEventListener('input', (e) => {
         document.execCommand(e.target.dataset.command, false, e.target.value);
         notesEditor.focus();
         updateToolbarState(); // NEW: Update state after command
    });


    saveNotesBtn.addEventListener('click', () => {
        const notesHTML = notesEditor.innerHTML;
        courses[activeCourseIndex].dailyPlan[currentDayIndex].notes = notesHTML;
        saveCourses();
        // Simple feedback
        saveNotesBtn.innerHTML = '<i class="fas fa-check"></i> Saved!';
        setTimeout(() => {
            saveNotesBtn.innerHTML = '<i class="fas fa-save"></i> Save Notes';
        }, 2000);
    });

    function loadNotes() {
        const notesHTML = courses[activeCourseIndex].dailyPlan[currentDayIndex].notes || '<p>Start typing your notes here...</p>';
        notesEditor.innerHTML = notesHTML;
        updateToolbarState(); // NEW: Update toolbar when notes are first loaded
    }
    
    downloadNotesBtn.addEventListener('click', () => {
        // Use innerText to get a plain text representation
        const notesText = notesEditor.innerText;
        const moduleTitle = courses[activeCourseIndex].dailyPlan[currentDayIndex].title;
        
        const blob = new Blob([notesText], { type: 'text/plain;charset=utf-8' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `My ${moduleTitle} Notes.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    });

    // --- NEW: Toolbar State Logic ---
    notesEditor.addEventListener('keyup', updateToolbarState);
    notesEditor.addEventListener('mouseup', updateToolbarState);
    notesEditor.addEventListener('focus', updateToolbarState);
    
    function updateToolbarState() {
        // Check simple button states
        notesBold.classList.toggle('is-active', document.queryCommandState('bold'));
        notesItalic.classList.toggle('is-active', document.queryCommandState('italic'));
        notesUnderline.classList.toggle('is-active', document.queryCommandState('underline'));

        // Check dropdown states
        let block = document.queryCommandValue('formatBlock').toLowerCase();
        if (block === '' || block === 'div' || block === 'p') {
            block = 'p'; // Default to paragraph
        }
        formatBlockSelect.value = block;
        
        let fontSize = document.queryCommandValue('fontSize');
        if (fontSize === '') {
            fontSize = '3'; // Default to normal
        }
        fontSizeSelect.value = fontSize;
    }

    // --- NEW: Theme Toggle Logic ---
    
    function setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeToggle.checked = true;
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            themeToggle.checked = false;
            localStorage.setItem('theme', 'light');
        }
    }
    
    themeToggle.addEventListener('change', () => {
        setTheme(themeToggle.checked ? 'dark' : 'light');
    });


    // --- NEW: Practice Lab Logic ---

    // Fetch challenge from backend (with caching)
    async function fetchChallenge(dayData) {
        if (dayData.challenge) {
            return dayData.challenge; // Return cached challenge
        }
        
        try {
            const response = await fetch('http://127.0.0.1:5000/generate-challenge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    moduleTitle: dayData.title, 
                    keyPoints: dayData.module.keyPoints 
                }),
            });
            if (!response.ok) throw new Error("Failed to generate challenge.");
            
            const challengeData = await response.json();
            // Cache the challenge
            dayData.challenge = challengeData;
            courses[activeCourseIndex].dailyPlan[currentDayIndex] = dayData;
            saveCourses();
            
            return challengeData;
        } catch (error) {
            console.error("Failed to fetch challenge:", error);
            return { type: "none" }; // Return a non-challenge type
        }
    }

    // Open and set up the lab
    function startPracticeLab(dayData) {
        currentLabChallenge = dayData.challenge;
        labTryCount = 0; // Reset try count

        if (!currentLabChallenge || currentLabChallenge.type === 'none') {
            alert("No practice lab available for this module.");
            return;
        }

        // Setup UI
        labTitle.textContent = `Practice Lab: ${currentLabChallenge.title}`;
        labQuestion.textContent = currentLabChallenge.question;
        htmlEditor.value = currentLabChallenge.starting_code.html;
        cssEditor.value = currentLabChallenge.starting_code.css;
        jsEditor.value = currentLabChallenge.starting_code.js;
        
        // Reset chat
        labChatMessages.innerHTML = `
            <div class="chat-message ai">
                <i class="fas fa-robot"></i>
                <div class="message-content">
                    <p>Stuck? Type your question or click "Get a Hint" and I'll see how I can help!</p>
                </div>
            </div>`;
        labChatInput.value = '';

        // Show the lab
        labView.classList.remove('hidden');
        updateLabPreview(); // Run code on open
    }

    // Close lab
    labCloseBtn.addEventListener('click', () => {
        labView.classList.add('hidden');
    });

    // Handle Tab switching in Lab
    labTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Deactivate all
            labTabBtns.forEach(b => b.classList.remove('active'));
            labTabContents.forEach(c => c.classList.remove('active'));

            // Activate clicked
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // Run Code
    labRunCodeBtn.addEventListener('click', updateLabPreview);

    function updateLabPreview() {
        const html = htmlEditor.value;
        const css = cssEditor.value;
        const js = jsEditor.value;

        const srcDoc = `
            <html>
                <head>
                    <style>${css}</style>
                </head>
                <body>
                    ${html}
                    <script>${js}</script>
                </body>
            </html>
        `;
        labPreviewIframe.srcdoc = srcDoc;

        // Auto-switch to preview tab
        labTabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === 'lab-preview-panel'));
        labTabContents.forEach(c => c.classList.toggle('active', c.id === 'lab-preview-panel'));
    }

    // AI Chat "Get a Hint" button
    labGetHintBtn.addEventListener('click', () => {
        const userMessage = labChatInput.value.trim();
        if (userMessage) {
            // If user typed a question, just add it to chat (we'll send it with the hint)
            addChatMessage(userMessage, 'user');
            labChatInput.value = '';
        }
        requestAiHint();
    });
    
    // Also send on Enter key
    labChatInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            labGetHintBtn.click();
        }
    });

    // Add a message to the chat window
    function addChatMessage(message, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${sender}`;
        const iconClass = sender === 'ai' ? 'fa-robot' : 'fa-user';
        
        // Convert newlines to <br> for proper formatting
        const formattedMessage = message.replace(/\n/g, '<br>');

        msgDiv.innerHTML = `
            <i class="fas ${iconClass}"></i>
            <div class="message-content">
                <p>${formattedMessage}</p>
            </div>
        `;
        labChatMessages.appendChild(msgDiv);
        labChatMessages.scrollTop = labChatMessages.scrollHeight; // Auto-scroll
    }

    // Fetch hint from AI
    async function requestAiHint() {
        labTryCount++; // Increment attempt counter
        
        const userCode = {
            html: htmlEditor.value,
            css: cssEditor.value,
            js: jsEditor.value
        };

        addChatMessage("Thinking...", 'ai'); // Show loading state
        
        try {
            const response = await fetch('http://127.0.0.1:5000/get-hint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    challenge_question: currentLabChallenge.question,
                    user_code: userCode,
                    solution: currentLabChallenge.solution,
                    try_count: labTryCount
                }),
            });

            if (!response.ok) throw new Error("Failed to get hint from AI.");

            const data = await response.json();
            
            // Remove "Thinking..." message
            labChatMessages.removeChild(labChatMessages.lastChild);

            // Add the real AI hint
            addChatMessage(data.hint, 'ai');

        } catch (error) {
            console.error("Failed to get hint:", error);
            // Remove "Thinking..." message
            labChatMessages.removeChild(labChatMessages.lastChild);
            addChatMessage("Sorry, I'm having trouble connecting right now. Please try again in a moment.", 'ai');
        }
    }


    // --- Initialize ---
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    showCourseListView();
});