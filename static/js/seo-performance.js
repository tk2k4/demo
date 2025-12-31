// =============================================
// SEO & Performance Enhancements
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== LAZY LOAD IMAGES =====
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        lazyImages.forEach(img => img.classList.add('loaded'));
    }
    
    // ===== EXTERNAL LINKS - Open in new tab with security =====
    const externalLinks = document.querySelectorAll('a[href^="http"]:not([href*="whiteneuron.com"])');
    externalLinks.forEach(link => {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
    });
    
    // ===== PERFORMANCE MONITORING =====
    if ('PerformanceObserver' in window) {
        // Largest Contentful Paint (LCP)
        const lcpObserver = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
        
        // First Input Delay (FID)
        const fidObserver = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
            });
        });
        fidObserver.observe({ entryTypes: ['first-input'] });
        
        // Cumulative Layout Shift (CLS)
        let clsScore = 0;
        const clsObserver = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (!entry.hadRecentInput) {
                    clsScore += entry.value;
                }
            });
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });
    }
    
    // ===== PRELOAD NEXT PAGE =====
    const internalLinks = document.querySelectorAll('a[href^="/"], a[href^="https://whiteneuron.com"]');
    internalLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            const url = this.getAttribute('href');
            const linkElement = document.createElement('link');
            linkElement.rel = 'prefetch';
            linkElement.href = url;
            document.head.appendChild(linkElement);
        }, { once: true });
    });
    
    // ===== SERVICE WORKER FOR CACHING (Optional) =====
    // Only register in production and if supported
    if ('serviceWorker' in navigator && 
        !window.location.hostname.includes('localhost') &&
        !window.location.hostname.includes('127.0.0.1')) {
        
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then(registration => {
                    // Check for updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'activated') {
                                // Optionally show update notification to user
                            }
                        });
                    });
                })
                .catch(error => {
                });
        });
    }
    
    // ===== ADD STRUCTURED DATA DYNAMICALLY =====
    // You can add more structured data based on page content
    
    // ===== TRACK SCROLL DEPTH =====
    let maxScroll = 0;
    window.addEventListener('scroll', () => {
        const scrollPercent = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
        if (scrollPercent > maxScroll) {
            maxScroll = scrollPercent;
            
            // Track milestones
            if (maxScroll >= 25 && maxScroll < 50) {
            } else if (maxScroll >= 50 && maxScroll < 75) {
            } else if (maxScroll >= 75 && maxScroll < 100) {
            } else if (maxScroll >= 100) {
            }
        }
    }, { passive: true });
    
    // ===== OPTIMIZE IMAGES ON LOAD =====
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        // Add alt text if missing
        if (!img.hasAttribute('alt')) {
            const fileName = img.src.split('/').pop().split('.')[0];
            img.setAttribute('alt', fileName.replace(/-|_/g, ' '));
        }
        
        // Add width/height to prevent CLS
        if (!img.hasAttribute('width') || !img.hasAttribute('height')) {
            img.addEventListener('load', function() {
                if (!this.hasAttribute('width')) {
                    this.setAttribute('width', this.naturalWidth);
                }
                if (!this.hasAttribute('height')) {
                    this.setAttribute('height', this.naturalHeight);
                }
            });
        }
    });
    
});
