// Main JavaScript functionality for Khata

document.addEventListener('DOMContentLoaded', function() {
    // Initialize standard page interactions
    initializePage();
    // Initialize SPA smooth AJAX navigation
    initSPANavigation();
    // Initialize premium header scroll tracking
    initScrollTracker();
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

// Globally accessible navigation function
window.navigateToPage = async function(url, pushState = true) {
    showProgressBar();
    
    try {
        const response = await fetch(url);
        if (!response.ok) {
            window.location.href = url;
            return;
        }
        
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Swap Title
        document.title = doc.title;
        
        // Swap Main Content Area
        const currentMain = document.querySelector('main');
        const newMain = doc.querySelector('main');
        if (currentMain && newMain) {
            currentMain.innerHTML = newMain.innerHTML;
            
            // Execute any scripts within the dynamic content block (e.g., canvas shaders)
            executeScripts(currentMain);
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
    }
};

function executeScripts(container) {
    const scripts = container.querySelectorAll('script');
    scripts.forEach(oldScript => {
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
    let bar = document.getElementById('spa-progress-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'spa-progress-bar';
        bar.style.position = 'fixed';
        bar.style.top = '0';
        bar.style.left = '0';
        bar.style.height = '3.5px';
        bar.style.backgroundColor = '#4648d4';
        bar.style.boxShadow = '0 0 10px #4648d4, 0 0 5px rgba(70, 72, 212, 0.5)';
        bar.style.zIndex = '99999';
        bar.style.width = '0%';
        bar.style.transition = 'width 0.4s cubic-bezier(0.08, 0.82, 0.17, 1), opacity 0.3s ease';
        document.body.appendChild(bar);
    }
    bar.style.opacity = '1';
    bar.style.width = '15%';
    
    // Simulate incremental loads
    setTimeout(() => { if (bar.style.width === '15%') bar.style.width = '45%'; }, 200);
    setTimeout(() => { if (bar.style.width === '45%') bar.style.width = '75%'; }, 600);
}

function hideProgressBar() {
    const bar = document.getElementById('spa-progress-bar');
    if (bar) {
        bar.style.width = '100%';
        setTimeout(() => {
            bar.style.opacity = '0';
            setTimeout(() => {
                bar.style.width = '0%';
            }, 300);
        }, 150);
    }
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

// System color scheme change listener
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    const savedTheme = localStorage.getItem('theme') || 'system';
    if (savedTheme === 'system') {
        const newTheme = e.matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
    }
});

