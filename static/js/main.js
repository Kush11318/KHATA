// Main JavaScript functionality for Khata

document.addEventListener('DOMContentLoaded', function() {
    // Initialize standard page interactions
    initializePage();
    // Initialize SPA smooth AJAX navigation
    initSPANavigation();
    // Initialize premium header scroll tracking
    initScrollTracker();

    // Smooth entrance transition for initial page load
    const currentMain = document.querySelector('main');
    if (currentMain && typeof gsap !== 'undefined') {
        const path = window.location.pathname;
        const isDashboard = path === '/seller' || path === '/seller/';
        const isAnalytics = path.includes('/seller/customer-analytics');
        
        if (isDashboard || isAnalytics) {
            // Let the dashboard's or analytics' own script handle the card entrance animations.
            // We only do a quick fade-in of the outer container to avoid double-offset conflicts.
            gsap.fromTo(currentMain, 
                { opacity: 0 },
                { 
                    opacity: 1, 
                    duration: 0.25, 
                    ease: 'power1.out',
                    clearProps: 'opacity'
                }
            );
        } else {
            gsap.fromTo(currentMain, 
                { opacity: 0, y: 15 },
                { 
                    opacity: 1, 
                    y: 0, 
                    duration: 0.5, 
                    ease: 'power2.out',
                    clearProps: 'transform,opacity'
                }
            );
            
            // Stagger key child elements if NOT dashboard/analytics (which handle their own staggers)
            const animTargets = currentMain.querySelectorAll(
                '.comic-card, .form-section-header, .grid > div, form > div, table tbody tr, .card, h1, h2'
            );
            if (animTargets.length > 0) {
                const visibleTargets = Array.from(animTargets)
                    .filter(el => el.offsetHeight > 0 || el.getBoundingClientRect().height > 0)
                    .slice(0, 12);
                
                gsap.fromTo(visibleTargets,
                    { opacity: 0, y: 15 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.45,
                        stagger: 0.04,
                        ease: 'power2.out',
                        clearProps: 'transform,opacity'
                    }
                );
            }
        }
    }
});

function initScrollTracker() {
    const handleScroll = () => {
        const header = document.querySelector('.premium-header');
        if (header) {
            if (window.scrollY > 10) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }
    };
    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Check immediately on load
}

function initializePage() {
    // User menu dropdown toggle
    const toggle = document.getElementById('userToggle');
    const dropdown = document.getElementById('userDropdown');
    if (toggle && dropdown) {
        // Remove existing listener to prevent duplicate binding
        const newToggle = toggle.cloneNode(true);
        toggle.parentNode.replaceChild(newToggle, toggle);
        
        newToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        document.addEventListener('click', function () {
            dropdown.classList.remove('show');
        });
    }

    // Premium profile dropdown toggle
    const premiumTrigger = document.getElementById('premiumProfileTrigger');
    const premiumDropdown = document.getElementById('premiumProfileDropdown');
    if (premiumTrigger && premiumDropdown) {
        // Remove existing listener to prevent duplicate binding
        const newTrigger = premiumTrigger.cloneNode(true);
        premiumTrigger.parentNode.replaceChild(newTrigger, premiumTrigger);
        
        newTrigger.addEventListener('click', function (e) {
            e.stopPropagation();
            premiumDropdown.classList.toggle('show');
            const icon = newTrigger.querySelector('.material-symbols-outlined');
            if (icon) {
                if (premiumDropdown.classList.contains('show')) {
                    icon.style.transform = 'rotate(180deg)';
                } else {
                    icon.style.transform = 'none';
                }
            }
        });
        document.addEventListener('click', function () {
            premiumDropdown.classList.remove('show');
            const icon = newTrigger.querySelector('.material-symbols-outlined');
            if (icon) {
                icon.style.transform = 'none';
            }
        });
    }
}

// Progressive SPA/Pjax smooth page transitions
function initSPANavigation() {
    // Intercept clicks on body for internal link delegation
    document.body.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (!link) return;
        
        if (shouldHandleLink(link)) {
            e.preventDefault();
            const href = link.getAttribute('href');
            navigateToPage(href);
        }
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', () => {
        navigateToPage(window.location.pathname + window.location.search, false);
    });
}

function shouldHandleLink(link) {
    const href = link.getAttribute('href');
    if (!href) return false;
    
    // Skip external links
    if (href.startsWith('http') && !href.startsWith(window.location.origin)) return false;
    
    // Skip anchor tags and JS templates
    if (href.startsWith('#') || href.startsWith('javascript:')) return false;
    
    // Skip target _blank or download
    if (link.getAttribute('target') === '_blank' || link.hasAttribute('download')) return false;
    
    // Skip logout (needs full reload to clear server sessions)
    if (href.includes('/logout')) return false;
    
    return true;
}

// // Globally accessible navigation function
window.navigateToPage = async function(url, pushState = true) {
    // Reset navbar intro active flag during SPA transitions to prevent animation delays
    window.navbarIntroActive = false;
    showProgressBar();
    
    // Check if we are navigating to the seller dashboard
    let targetPath = '';
    try {
        targetPath = new URL(url, window.location.origin).pathname;
    } catch (e) {
        targetPath = url;
    }
    const isDashboard = targetPath === '/seller' || targetPath === '/seller/';
    const isAnalytics = targetPath.includes('/seller/customer-analytics');
    
    // Start fetching immediately in the background in parallel with fade-out animation
    const fetchPromise = fetch(url).then(async response => {
        if (!response.ok) throw new Error("Fetch failed");
        return response.text();
    });
    
    const currentMain = document.querySelector('main');
    
    // Run fade-out animation in parallel with the fetch request
    if (currentMain && typeof gsap !== 'undefined') {
        if (isDashboard || isAnalytics) {
            // Fast fade-out
            await new Promise(resolve => {
                gsap.to(currentMain, {
                    opacity: 0,
                    duration: 0.12,
                    ease: 'power1.in',
                    onComplete: resolve
                });
            });
        } else {
            // Fade out and shift
            await new Promise(resolve => {
                gsap.to(currentMain, {
                    opacity: 0,
                    y: 8,
                    duration: 0.12,
                    ease: 'power2.in',
                    onComplete: resolve
                });
            });
        }
    }
    
    try {
        // Wait for fetch to complete (if it hasn't already)
        const html = await fetchPromise;
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Swap Title
        document.title = doc.title;
        
        // Swap Main Content Area
        const newMain = doc.querySelector('main');
        if (currentMain && newMain) {
            currentMain.innerHTML = newMain.innerHTML;
            
            // Reset scroll position to top of the page instantly
            window.scrollTo({ top: 0, behavior: 'instant' });
            
            // Execute any scripts within the dynamic content block (e.g., canvas shaders)
            executeScripts(currentMain);

            if (typeof gsap !== 'undefined') {
                if (isDashboard || isAnalytics) {
                    // Set starting state for new content (only opacity)
                    gsap.set(currentMain, { opacity: 0 });
                    
                    // Fade in container smoothly
                    gsap.to(currentMain, {
                        opacity: 1,
                        duration: 0.2,
                        ease: 'power1.out',
                        clearProps: 'opacity'
                    });
                } else {
                    // Set starting state for new content
                    gsap.set(currentMain, { opacity: 0, y: 12 });
                    
                    // Fade in container smoothly
                    gsap.to(currentMain, {
                        opacity: 1,
                        y: 0,
                        duration: 0.25,
                        ease: 'power2.out',
                        clearProps: 'transform,opacity'
                    });

                    // Stagger key child elements if NOT dashboard (dashboard handles its own beautiful staggers)
                    const animTargets = currentMain.querySelectorAll(
                        '.comic-card, .form-section-header, .grid > div, form > div, table tbody tr, .card, h1, h2'
                    );
                    if (animTargets.length > 0) {
                        const visibleTargets = Array.from(animTargets)
                            .filter(el => el.offsetHeight > 0 || el.getBoundingClientRect().height > 0)
                            .slice(0, 12);
                        
                        gsap.fromTo(visibleTargets,
                            { opacity: 0, y: 10 },
                            {
                                opacity: 1,
                                y: 0,
                                duration: 0.35,
                                stagger: 0.03,
                                ease: 'power2.out',
                                clearProps: 'transform,opacity'
                            }
                        );
                    }
                }
            }
        }
        
        // Update URL path in history
        if (pushState) {
            window.history.pushState(null, '', url);
        }
        
        // Sync active styling state in header navs
        updateNavLinks(url);
        
        // Re-initialize general page listeners
        initializePage();
        
        // Auto-run AI Assistant form population check
        if (window.aiAssistant && typeof window.aiAssistant.checkAndPopulateInvoice === 'function') {
            window.aiAssistant.checkAndPopulateInvoice();
        }
        
        // Trigger scroll event to sync header scrolled state
        window.dispatchEvent(new Event('scroll'));
        
    } catch (err) {
        console.error("SPA dynamic navigation failed, falling back to full reload:", err);
        window.location.href = url;
    } finally {
        hideProgressBar();
        // Since we don't display the full page loader on SPA transition anymore,
        // we dispatch the hidden event immediately in case any new components are listening to it.
        window.dispatchEvent(new CustomEvent('page-loader-hidden'));
    }
};

function executeScripts(container) {
    const scripts = container.querySelectorAll('script');
    scripts.forEach(oldScript => {
        try {
            const newScript = document.createElement('script');
            Array.from(oldScript.attributes).forEach(attr => {
                newScript.setAttribute(attr.name, attr.value);
            });
            if (oldScript.src) {
                newScript.src = oldScript.src;
            } else {
                newScript.textContent = oldScript.textContent;
            }
            oldScript.parentNode.replaceChild(newScript, oldScript);
        } catch (err) {
            console.error("Error executing script tag in dynamic content:", err);
        }
    });
}

function updateNavLinks(url) {
    const path = new URL(url, window.location.origin).pathname;
    
    // Update premium header link highlights
    const premiumLinks = document.querySelectorAll('.premium-nav-link');
    premiumLinks.forEach(link => {
        const linkPath = new URL(link.getAttribute('href'), window.location.origin).pathname;
        if (path === linkPath) {
            link.classList.add('active-link');
        } else {
            link.classList.remove('active-link');
        }
    });
    
    // Update legacy header link highlights
    const legacyLinks = document.querySelectorAll('.nav-link');
    legacyLinks.forEach(link => {
        const linkPath = new URL(link.getAttribute('href'), window.location.origin).pathname;
        if (path === linkPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

function showProgressBar() {
    // No-op: dynamic page loaders disabled on nav bar/top layout
}

function hideProgressBar() {
    // No-op: dynamic page loaders disabled on nav bar/top layout
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        ${message}
        <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Insert at the top of main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Form validation
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

// Add error styling for invalid fields
const style = document.createElement('style');
style.textContent = `
    .form-input.error {
        border-color: #ef4444;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
    }
`;
document.head.appendChild(style);

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
});

// Add smooth transitions for alerts
const alertStyle = document.createElement('style');
alertStyle.textContent = `
    .alert {
        transition: opacity 0.3s ease;
    }
`;
document.head.appendChild(alertStyle);



