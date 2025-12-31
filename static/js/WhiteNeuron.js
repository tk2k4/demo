// ===================================
// White Neuron - Main JavaScript
// Interactive 3D Particles & Animations
// ===================================

// Quick loaders/debuggers to help identify why clicks/logs may be missing

window.addEventListener('error', function(evt) {
    try {
    } catch (e) {
    }
});
window.addEventListener('unhandledrejection', function(evt) {
});

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== INTERSECTION OBSERVER FOR ANIMATIONS =====
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    const section = document.querySelector('.platform-wrapper');
    if (section) {
        observer.observe(section);
    }

    // ===== THREE.JS PARTICLE SYSTEM =====
    let scene, camera, renderer, particles;
    let mouseX = 0, mouseY = 0;
    let windowHalfX = window.innerWidth / 2;
        let windowHalfY = window.innerHeight / 2;

        // Particle settings
        const PARTICLE_SETTINGS = {
            count: 3000,
            size: window.devicePixelRatio > 1 ? 2 : 3,
            opacity: 0.6,
            connectionOpacity: 0.2,
            enableLowPerformanceMode: false
        };

        function init() {
            
            const container = document.getElementById('canvas-container');
            if (!container) return;
            
            // Scene setup
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 3000);
            camera.position.z = 1000;

            // Renderer setup with optimization
            renderer = new THREE.WebGLRenderer({ 
                alpha: true, 
                antialias: true,
                powerPreference: "high-performance"
            });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setClearColor(0x000000, 0);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit pixel ratio
            container.appendChild(renderer.domElement);

            // Create particle system
            createParticleSphere();

            // Event listeners
            document.addEventListener('mousemove', onDocumentMouseMove, false);
            window.addEventListener('resize', onWindowResize, false);
        }

        function createParticleSphere() {
            const geometry = new THREE.BufferGeometry();
            const vertices = [];
            const colors = [];
            const originalPositions = [];
            const floatSpeeds = [];

            // Create sphere of particles - Sử dụng settings
            const radius = 500;
            const particleCount = PARTICLE_SETTINGS.count;

            for (let i = 0; i < particleCount; i++) {
                // Spherical coordinates for even distribution
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                
                const x = radius * Math.sin(phi) * Math.cos(theta);
                const y = radius * Math.sin(phi) * Math.sin(theta);
                const z = radius * Math.cos(phi);

                vertices.push(x, y, z);
                
                // Store original positions for floating effect
                originalPositions.push(x, y, z);
                
                // Random float speed for each particle
                floatSpeeds.push(Math.random() * 1.5 + 0.5);

                // Color gradient from blue to cyan - softer colors
                const color = new THREE.Color();
                color.setHSL(0.55 + Math.random() * 0.15, 0.6, 0.4 + Math.random() * 0.2);
                colors.push(color.r, color.g, color.b);
            }

            geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

            // Particle material - sử dụng settings
            const material = new THREE.PointsMaterial({
                size: PARTICLE_SETTINGS.size,
                sizeAttenuation: true,
                vertexColors: true,
                transparent: true,
                opacity: PARTICLE_SETTINGS.opacity,
                blending: THREE.AdditiveBlending
            });

            particles = new THREE.Points(geometry, material);
            particles.originalPositions = originalPositions;
            particles.floatSpeeds = floatSpeeds;
            scene.add(particles);

            // Turn off connecting lines to avoid drawing lines
            // createConnections();
        }

        function createConnections() {
            const positions = particles.geometry.attributes.position.array;
            const lineGeometry = new THREE.BufferGeometry();
            const lineVertices = [];

            // Create random connections between nearby particles
            const connectionDensity = PARTICLE_SETTINGS.enableLowPerformanceMode ? 0.9995 : 0.998;
            const maxConnections = PARTICLE_SETTINGS.enableLowPerformanceMode ? 100 : 300;
            const connectionDistance = PARTICLE_SETTINGS.enableLowPerformanceMode ? 100 : 120;

            for (let i = 0; i < positions.length; i += 3) {
                if (Math.random() > connectionDensity) {
                    const x1 = positions[i];
                    const y1 = positions[i + 1];
                    const z1 = positions[i + 2];

                    // Find nearby particles
                    for (let j = i + 3; j < positions.length && lineVertices.length < maxConnections; j += 3) {
                        const x2 = positions[j];
                        const y2 = positions[j + 1];
                        const z2 = positions[j + 2];

                        const distance = Math.sqrt(
                            (x2 - x1) * (x2 - x1) +
                            (y2 - y1) * (y2 - y1) +
                            (z2 - z1) * (z2 - z1)
                        );

                        if (distance < connectionDistance) {
                            lineVertices.push(x1, y1, z1);
                            lineVertices.push(x2, y2, z2);
                            break;
                        }
                    }
                }
            }

            lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(lineVertices, 3));

            const lineMaterial = new THREE.LineBasicMaterial({
                color: 0x64b5f6,
                transparent: true,
                opacity: PARTICLE_SETTINGS.connectionOpacity,
                blending: THREE.AdditiveBlending
            });

            const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
            scene.add(lines);
        }

        function onDocumentMouseMove(event) {
            mouseX = (event.clientX - windowHalfX) * 0.1;
            mouseY = (event.clientY - windowHalfY) * 0.1;
            
            // Tạo ripple effect tại vị trí chuột
            createMouseRipple(event.clientX, event.clientY);
        }
        
        function createMouseRipple(x, y) {
            // Tạo hiệu ứng sóng lan tỏa từ vị trí chuột
            if (particles && particles.geometry) {
                const positions = particles.geometry.attributes.position.array;
                const colors = particles.geometry.attributes.color.array;
                
                // Convert screen coordinates to world coordinates
                const mouseWorldX = (x - windowHalfX) * 2;
                const mouseWorldY = -(y - windowHalfY) * 2;
                
                for (let i = 0; i < positions.length; i += 3) {
                    const distance = Math.sqrt(
                        (positions[i] - mouseWorldX) * (positions[i] - mouseWorldX) +
                        (positions[i + 1] - mouseWorldY) * (positions[i + 1] - mouseWorldY)
                    );
                    
                    // Highlight particles gần chuột
                    if (distance < 200) {
                        const intensity = (200 - distance) / 200;
                        colors[i] = 0.2 + intensity * 0.8;     // red
                        colors[i + 1] = 0.4 + intensity * 0.6; // green  
                        colors[i + 2] = 1.0;                   // blue
                    } else {
                        // Reset về màu gốc
                        colors[i] = 0.2 + Math.random() * 0.3;
                        colors[i + 1] = 0.4 + Math.random() * 0.2;
                        colors[i + 2] = 1.0;
                    }
                }
                
                particles.geometry.attributes.color.needsUpdate = true;
            }
        }

        function onWindowResize() {
            windowHalfX = window.innerWidth / 2;
            windowHalfY = window.innerHeight / 2;

            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();

            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function animate() {
            requestAnimationFrame(animate);

            const time = Date.now() * 0.001;

            // Floating particles effect với mouse interaction
            if (particles && particles.originalPositions) {
                const positions = particles.geometry.attributes.position.array;
                const originalPos = particles.originalPositions;
                const floatSpeeds = particles.floatSpeeds;

                for (let i = 0; i < positions.length; i += 3) {
                    const particleIndex = i / 3;
                    
                    // Original position
                    const origX = originalPos[i];
                    const origY = originalPos[i + 1];
                    const origZ = originalPos[i + 2];
                    
                    // Enhanced floating effect
                    const floatOffset = Math.sin(time * 0.8 + particleIndex * 0.02) * 50;
                    const upwardDrift = Math.sin(time * 0.3 + particleIndex * 0.01) * 80;
                    const sideFloat = Math.cos(time * 0.4 + particleIndex * 0.03) * 30;
                    
                    const randomFloat = Math.sin(time * floatSpeeds[particleIndex] + particleIndex) * 25;
                    
                    // Mouse interaction - particles bị đẩy ra khỏi vị trí chuột
                    const mouseInfluence = 100;
                    const mouseDistance = Math.sqrt(
                        (positions[i] - mouseX * 5) * (positions[i] - mouseX * 5) +
                        (positions[i + 1] - mouseY * 5) * (positions[i + 1] - mouseY * 5)
                    );
                    
                    let mouseEffectX = 0;
                    let mouseEffectY = 0;
                    
                    if (mouseDistance < mouseInfluence) {
                        const strength = (mouseInfluence - mouseDistance) / mouseInfluence;
                        const angle = Math.atan2(positions[i + 1] - mouseY * 5, positions[i] - mouseX * 5);
                        mouseEffectX = Math.cos(angle) * strength * 30;
                        mouseEffectY = Math.sin(angle) * strength * 30;
                    }
                    
                    positions[i] = origX + sideFloat + randomFloat * 0.3 + mouseEffectX;
                    positions[i + 1] = origY + floatOffset + upwardDrift + randomFloat + mouseEffectY;
                    positions[i + 2] = origZ + Math.sin(time * 0.6 + particleIndex * 0.04) * 25;
                }
                
                particles.geometry.attributes.position.needsUpdate = true;
            }

            // Rotate the particle sphere với mouse influence
            particles.rotation.x += 0.002 + mouseY * 0.0001;
            particles.rotation.y += 0.003 + mouseX * 0.0001;

            // Smooth camera movement theo chuột
            camera.position.x += (mouseX - camera.position.x) * 0.02;
            camera.position.y += (-mouseY - camera.position.y) * 0.02;
            camera.lookAt(scene.position);

            // Dynamic pulse effect dựa trên mouse movement
            const mouseIntensity = Math.sqrt(mouseX * mouseX + mouseY * mouseY) / 100;
            particles.material.opacity = 0.6 + Math.sin(time * 2) * 0.1 + mouseIntensity * 0.2;

            renderer.render(scene, camera);
        }

        // Initialize and start animation
        init();
        animate();

    // ===== NAVBAR SCROLL EFFECT - OPTIMIZED =====
    let ticking = false;
    
    function updateNavbar() {
        const navbar = document.getElementById('navbar');
        if (!navbar) return;
        
        const scrolled = window.pageYOffset;
        
        if (scrolled > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        ticking = false;
    }
    
    function requestTick() {
        if (!ticking) {
            requestAnimationFrame(updateNavbar);
            ticking = true;
        }
    }
    
    window.addEventListener('scroll', requestTick, { passive: true });

    // ===== FADE IN ANIMATIONS =====
        //     threshold: 0.1,
        //     rootMargin: '0px 0px -50px 0px'
        // };

        // const observer = new IntersectionObserver((entries) => {
        //     entries.forEach(entry => {
        //         if (entry.isIntersecting) {
        //             entry.target.style.animationDelay = '0.2s';
        //             entry.target.classList.add('fade-in');
        //         }
        //     });
        // }, observerOptions);

        // document.querySelectorAll('.fade-in').forEach(el => {
        //     observer.observe(el);
        // });

        // Create floating particles - REDUCE NUMBER TO INCREASE PERFORMANCE
        function createParticles() {
            const particlesContainer = document.querySelector('.floating-particles');
            if (!particlesContainer) return; // Check if container exists
            
            const particleCount = 10; // Giảm từ 20 xuống 10

            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDelay = Math.random() * 6 + 's';
                particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
                particlesContainer.appendChild(particle);
            }
        }

        // Animate stats on scroll
        function animateStats() {
            const stats = document.querySelectorAll('.stat-number');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const element = entry.target;
                        const finalValue = element.textContent;
                        const numericValue = parseInt(finalValue.replace(/\D/g, ''));
                        
                        let current = 0;
                        const increment = numericValue / 50;
                        const timer = setInterval(() => {
                            current += increment;
                            if (current >= numericValue) {
                                element.textContent = finalValue;
                                clearInterval(timer);
                            } else {
                                const suffix = finalValue.includes('M+') ? 'M+' : 
                                              finalValue.includes('+') ? '+' : '';
                                element.textContent = Math.floor(current) + suffix;
                            }
                        }, 40);
                    }
                });
            });

            stats.forEach(stat => observer.observe(stat));
        }

        // Add hover effects to devices
        function addDeviceEffects() {
            const devices = document.querySelectorAll('.device');
            devices.forEach(device => {
                device.addEventListener('mouseenter', () => {
                    device.style.boxShadow = '0 15px 40px rgba(100, 200, 255, 0.3)';
                });
                
                device.addEventListener('mouseleave', () => {
                    device.style.boxShadow = 'none';
                });
            });
        }

        // Initialize everything
        document.addEventListener('DOMContentLoaded', () => {
            createParticles();
            animateStats();
            addDeviceEffects();
        });

        // TURN OFF DYNAMIC PARTICLE CREATION - CAUSES LAG AND AUTO SCROLLING
        // Add more floating particles dynamically
        // function createParticle() {
        //     const particle = document.createElement('div');
        //     particle.className = 'w3-particle';
        //     particle.style.left = Math.random() * 100 + '%';
        //     particle.style.animationDelay = '-' + Math.random() * 20 + 's';
        //     particle.style.animationDuration = (15 + Math.random() * 10) + 's';
        //     document.body.appendChild(particle);
        //     
        //     // Remove particle after animation
        //     setTimeout(() => {
        //         if (particle.parentNode) {
        //             particle.parentNode.removeChild(particle);
        //         }
        //     }, 25000);
        // }

        // TURN OFF PERIODIC PARTICLE CREATION
        // Create particles periodically
        // setInterval(createParticle, 3000);

        // Add hover effects for chart bars
        document.querySelectorAll('.w3-chart-bar').forEach((bar, index) => {
            bar.addEventListener('mouseenter', () => {
                bar.style.background = 'linear-gradient(to top, rgba(139, 92, 246, 0.5), rgba(139, 92, 246, 0.9))';
            });
            
            bar.addEventListener('mouseleave', () => {
                bar.style.background = 'linear-gradient(to top, rgba(139, 92, 246, 0.3), rgba(139, 92, 246, 0.7))';
            });
        });

        // Add click effects for feature cards
        document.querySelectorAll('.w3-feature-card').forEach(card => {
            card.addEventListener('click', () => {
                card.style.transform = 'translateY(-12px) scale(1.02)';
                setTimeout(() => {
                    card.style.transform = 'translateY(-8px)';
                }, 150);
            });
        });

        // Animate network nodes on hover
        document.querySelectorAll('.w3-network-visualization').forEach(network => {
            network.addEventListener('mouseenter', () => {
                const nodes = network.querySelectorAll('.w3-network-node');
                nodes.forEach((node, index) => {
                    node.style.animationDuration = '1s';
                    node.style.transform = 'scale(1.5)';
                });
            });
            
            network.addEventListener('mouseleave', () => {
                const nodes = network.querySelectorAll('.w3-network-node');
                nodes.forEach((node, index) => {
                    node.style.animationDuration = '3s';
                    node.style.transform = 'scale(1)';
                });
            });
        });

        // Add smooth scrolling effect for better UX
        document.addEventListener('DOMContentLoaded', () => {
            // Animate elements on scroll
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });

            // Set initial state and observe cards
            document.querySelectorAll('.w3-feature-card').forEach(card => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(card);
            });
        });

        // TẮM BACKGROUND ANIMATION COLORS - CÓ THỂ GÂY LAG
        // Add dynamic background color changes
        // const bgAnimation = document.querySelector('.w3-bg-animation');
        // let colorIndex = 0;
        // const colors = [
        //     'radial-gradient(ellipse at 25% 20%, rgba(120, 119, 198, 0.2) 0%, transparent 50%), radial-gradient(ellipse at 75% 80%, rgba(255, 107, 107, 0.15) 0%, transparent 50%), radial-gradient(ellipse at 50% 40%, rgba(34, 197, 94, 0.1) 0%, transparent 50%)',
        //     'radial-gradient(ellipse at 35% 30%, rgba(255, 107, 107, 0.2) 0%, transparent 50%), radial-gradient(ellipse at 65% 70%, rgba(34, 197, 94, 0.15) 0%, transparent 50%), radial-gradient(ellipse at 40% 60%, rgba(120, 119, 198, 0.1) 0%, transparent 50%)',
        //     'radial-gradient(ellipse at 45% 10%, rgba(34, 197, 94, 0.2) 0%, transparent 50%), radial-gradient(ellipse at 85% 90%, rgba(120, 119, 198, 0.15) 0%, transparent 50%), radial-gradient(ellipse at 30% 70%, rgba(255, 107, 107, 0.1) 0%, transparent 50%)'
        // ];

        class BlogSlider {
            constructor() {
                this.slider = document.getElementById('sliderWrapper');
                if (!this.slider) {
                    return; // Check if slider exists
                }
                
                this.prevBtn = document.getElementById('prevBtn');
                this.nextBtn = document.getElementById('nextBtn');
                this.dotsContainer = document.getElementById('sliderDots');
                
                this.cards = this.slider.querySelectorAll('.blog-card');
                this.currentIndex = 0;
                this.cardsPerView = this.getCardsPerView();
                this.maxIndex = Math.max(0, this.cards.length - this.cardsPerView);
                this.autoSlideEnabled = false; // TURN OFF AUTO SLIDE BY DEFAULT
                
                this.init();
            }

            getCardsPerView() {
                const containerWidth = this.slider.parentElement.offsetWidth;
                if (containerWidth < 768) return 1;
                if (containerWidth < 1024) return 2;
                return 3;
            }

            init() {
                this.createDots();
                this.updateSlider();
                this.bindEvents();
                // TURN OFF AUTO SLIDE - this.startAutoSlide();
            }

            createDots() {
                if (!this.dotsContainer) return;
                this.dotsContainer.innerHTML = '';
                for (let i = 0; i <= this.maxIndex; i++) {
                    const dot = document.createElement('div');
                    dot.className = 'dot';
                    dot.addEventListener('click', () => this.goToSlide(i));
                    this.dotsContainer.appendChild(dot);
                }
            }

            updateSlider() {
                if (!this.cards.length) {
                    return;
                }
                
                const cardWidth = this.cards[0].offsetWidth;
                const gap = window.innerWidth < 768 ? 16 : 24;
                const translateX = -(this.currentIndex * (cardWidth + gap));
                
                this.slider.style.transform = `translateX(${translateX}px)`;
                
                if (this.dotsContainer) {
                    this.dotsContainer.querySelectorAll('.dot').forEach((dot, index) => {
                        dot.classList.toggle('active', index === this.currentIndex);
                    });
                }
                
                if (this.prevBtn) this.prevBtn.disabled = this.currentIndex === 0;
                if (this.nextBtn) this.nextBtn.disabled = this.currentIndex === this.maxIndex;
            }

            goToSlide(index) {
                this.currentIndex = Math.max(0, Math.min(index, this.maxIndex));
                this.updateSlider();
            }

            nextSlide() {
                if (this.currentIndex < this.maxIndex) {
                    this.currentIndex++;
                } else {
                    this.currentIndex = 0;
                }
                this.updateSlider();
            }

            prevSlide() {
                if (this.currentIndex > 0) {
                    this.currentIndex--;
                } else {
                    this.currentIndex = this.maxIndex;
                }
                this.updateSlider();
            }

            bindEvents() {
                
                if (this.nextBtn) {
                    this.nextBtn.addEventListener('click', () => {
                        this.nextSlide();
                    });
                } else {
                }
                
                if (this.prevBtn) {
                    this.prevBtn.addEventListener('click', () => {
                        this.prevSlide();
                    });
                } else {
                }
                
                // Touch support
                let startX = 0;
                let endX = 0;
                
                this.slider.addEventListener('touchstart', (e) => {
                    startX = e.touches[0].clientX;
                });
                
                this.slider.addEventListener('touchend', (e) => {
                    endX = e.changedTouches[0].clientX;
                    const diff = startX - endX;
                    
                    if (Math.abs(diff) > 50) {
                        if (diff > 0) {
                            this.nextSlide();
                        } else {
                            this.prevSlide();
                        }
                    }
                });
                
                // Keyboard navigation
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'ArrowLeft') this.prevSlide();
                    if (e.key === 'ArrowRight') this.nextSlide();
                });
                
                // MANUAL CONTROL - CHỈ START AUTO-SLIDE KHI HOVER
                this.slider.addEventListener('mouseenter', () => {
                    if (this.autoSlideEnabled) this.stopAutoSlide();
                });
                this.slider.addEventListener('mouseleave', () => {
                    if (this.autoSlideEnabled) this.startAutoSlide();
                });
            }

            startAutoSlide() {
                if (!this.autoSlideEnabled) return;
                this.stopAutoSlide();
                this.autoSlideInterval = setInterval(() => {
                    this.nextSlide();
                }, 10000); // Tăng từ 5s lên 10s
            }

            stopAutoSlide() {
                if (this.autoSlideInterval) {
                    clearInterval(this.autoSlideInterval);
                }
            }

            // THÊM PHƯƠNG THỨC ĐỂ BẬT/TẮT AUTO SLIDE
            enableAutoSlide() {
                this.autoSlideEnabled = true;
                this.startAutoSlide();
            }

            disableAutoSlide() {
                this.autoSlideEnabled = false;
                this.stopAutoSlide();
            }

            handleResize() {
                const newCardsPerView = this.getCardsPerView();
                if (newCardsPerView !== this.cardsPerView) {
                    this.cardsPerView = newCardsPerView;
                    this.maxIndex = Math.max(0, this.cards.length - this.cardsPerView);
                    this.currentIndex = Math.min(this.currentIndex, this.maxIndex);
                    this.createDots();
                    this.updateSlider();
                }
            }
        }

        // ===== BLOG SLIDER INITIALIZATION =====
        function initBlogSlider() {
            
            // Check if elements exist
            const slider = document.getElementById('sliderWrapper');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            
            if (slider && prevBtn && nextBtn) {
                const blogSlider = new BlogSlider();
                window.blogSlider = blogSlider;
                
                // Add direct event listeners as backup
                prevBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (window.blogSlider) {
                        window.blogSlider.prevSlide();
                    }
                });
                
                nextBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (window.blogSlider) {
                        window.blogSlider.nextSlide();
                    }
                });
                
                return blogSlider;
            } else {
                setTimeout(initBlogSlider, 100);
                return null;
            }
        }
    
        (function() {
            let currentReview = 0;
            let isScrolling = false;
            let autoRotateEnabled = true;
            
            const clientReviews = [
                {
                    name: "Daniel Redhill",
                    title: "Chief Executive Officer",
                    quote: "By controlling our own tokens, it allows us the flexibility to be nimble. We can move to other processors if necessary. We can chase better revenue opportunities.",
                    image: "/static/imgs/photo/photo.jpeg"
                },
                {
                    name: "Robert Kim",
                    title: "Chief Financial Officer",
                    quote: "The cost savings and efficiency gains have been remarkable. This solution has delivered measurable ROI within the first quarter of implementation.",
                    image: "/static/imgs/photo/photo.jpeg"
                },
                {
                    name: "Michael Torres",
                    title: "Head of Operations",
                    quote: "Implementation was seamless and the support team has been exceptional. We've seen a 40% improvement in processing efficiency since switching platforms.",
                    image: "/static/imgs/photo/photo.jpeg"
                },
                {
                    name: "Emily Rodriguez",
                    title: "VP of Marketing",  
                    quote: "The analytics and insights provided have transformed our decision-making process. We can now track performance metrics in real-time with incredible accuracy.",
                    image: "/static/imgs/photo/photo.jpeg"
                },
                {
                    name: "Sarah Johnson",
                    title: "Director of Technology",
                    quote: "The platform's scalability and reliability have exceeded our expectations. We've handled peak loads without any performance degradation.",
                    image: "/static/imgs/photo/photo.jpeg"
                }
            ];

            function updateClientReview() {
                const review = clientReviews[currentReview];
                const nextIndex = (currentReview + 1) % clientReviews.length;
                const previewIndex = (currentReview + 2) % clientReviews.length;
                const nextReview = clientReviews[nextIndex];
                const previewReview = clientReviews[previewIndex];
                
                // CHECK IF ELEMENTS EXIST BEFORE UPDATING
                const clientName = document.getElementById('client-name');
                const clientPosition = document.getElementById('client-position');
                const clientFeedback = document.getElementById('client-feedback');
                const clientPhoto = document.getElementById('client-photo');
                const reviewCounter = document.getElementById('review-counter');
                const upcomingPhoto = document.getElementById('upcoming-client-photo');
                const previewPhoto = document.getElementById('preview-client-photo');
                
                if (clientName) clientName.textContent = review.name;
                if (clientPosition) clientPosition.textContent = review.title;
                if (clientFeedback) clientFeedback.textContent = `"${review.quote}"`;
                if (clientPhoto) clientPhoto.src = review.image;
                if (reviewCounter) reviewCounter.textContent = `${currentReview + 1}/5`;
                if (upcomingPhoto) upcomingPhoto.src = nextReview.image;
                if (previewPhoto) previewPhoto.src = previewReview.image;
            }

            // Make functions global so they can be called from HTML
            window.nextReview = function() {
                currentReview = (currentReview + 1) % clientReviews.length;
                updateClientReview();
            };

            window.previousReview = function() {
                currentReview = (currentReview - 1 + clientReviews.length) % clientReviews.length;
                updateClientReview();
            };

            // THÊM CONTROLS ĐỂ BẬT/TẮT AUTO ROTATE
            window.enableAutoRotate = function() {
                autoRotateEnabled = true;
                startAutoRotate();
            };

            window.disableAutoRotate = function() {
                autoRotateEnabled = false;
                stopAutoRotate();
            };

            let autoRotateInterval;

            function startAutoRotate() {
                if (!autoRotateEnabled) return;
                stopAutoRotate();
                autoRotateInterval = setInterval(() => {
                    window.nextReview();
                }, 10000); // Auto next every 10s
            }

            function stopAutoRotate() {
                if (autoRotateInterval) {
                    clearInterval(autoRotateInterval);
                }
            }

            // Initialize when DOM is ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    updateClientReview();
                    startAutoRotate();
                });
            } else {
                updateClientReview();
                startAutoRotate();
            }
        })();

        // THÊM GLOBAL CONTROLS ĐỂ BẬT/TẮT CÁC ANIMATIONS
        window.AnimationControls = {
            enableBlogSlider: function() {
                if (window.blogSlider) {
                    window.blogSlider.enableAutoSlide();
                }
            },
            disableBlogSlider: function() {
                if (window.blogSlider) {
                    window.blogSlider.disableAutoSlide();
                }
            },
            enableReviewRotation: function() {
                window.enableAutoRotate();
            },
            disableReviewRotation: function() {
                window.disableAutoRotate();
            },
            disableAllAnimations: function() {
                this.disableBlogSlider();
                this.disableReviewRotation();
            },
            enableAllAnimations: function() {
                this.enableBlogSlider();
                this.enableReviewRotation();
            }
        };

        // TỰ ĐỘNG TẮT TẤT CẢ ANIMATIONS KHI LOAD TRANG
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize scroll spy
            initScrollSpy();
            
            // Initialize BlogSlider
            initBlogSlider();
            
            // Add smooth scrolling for navigation links
            const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
            navLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const targetId = link.getAttribute('href');
                    const targetElement = document.querySelector(targetId);
                    
                    if (targetElement) {
                        const offsetTop = targetElement.offsetTop - 80; // Account for navbar height
                        window.scrollTo({
                            top: offsetTop,
                            behavior: 'smooth'
                        });
                    }
                });
            });
        });

        // ===== MOBILE MENU HANDLING =====
        const hamburger = document.getElementById('hamburger');
        const mobileMenu = document.getElementById('mobileMenu');
        
        if (hamburger && mobileMenu) {
            hamburger.addEventListener('click', () => {
                hamburger.classList.toggle('active');
                mobileMenu.classList.toggle('active');
                
                // Prevent body scroll when menu is open
                if (mobileMenu.classList.contains('active')) {
                    document.body.style.overflow = 'hidden';
                } else {
                    document.body.style.overflow = '';
                }
            });

            // Đóng menu khi click vào link hoặc button
            const mobileLinks = mobileMenu.querySelectorAll('a, button');
            mobileLinks.forEach(link => {
                link.addEventListener('click', () => {
                    hamburger.classList.remove('active');
                    mobileMenu.classList.remove('active');
                    document.body.style.overflow = '';
                });
            });

            // Đóng menu khi click outside
            mobileMenu.addEventListener('click', (e) => {
                if (e.target === mobileMenu) {
                    hamburger.classList.remove('active');
                    mobileMenu.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
            
            // Đóng menu khi resize window
            window.addEventListener('resize', () => {
                if (window.innerWidth > 768) {
                    hamburger.classList.remove('active');
                    mobileMenu.classList.remove('active');
                    document.body.style.overflow = '';
                }
            });
        }

// Scroll Spy Function
function initScrollSpy() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
    const mobileNavLinks = document.querySelectorAll('.mobile-menu .nav-links a[href^="#"]');
    const navbar = document.getElementById('navbar');
    
    function updateActiveNav() {
        let current = '';
        const scrollPosition = window.scrollY + 100; // Offset for better detection
        
        // Toggle navbar background based on scroll position
        if (window.scrollY > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });
        
        // Update desktop nav
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
        
        // Update mobile nav
        mobileNavLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }
    
    // Listen for scroll events
    window.addEventListener('scroll', updateActiveNav);
    
    // Initial check
    updateActiveNav();
}

 AOS.init({
        duration: 800,
        once: true
    });

// Navbar scroll effect - REMOVED (already handled above with optimized version)

// Service card hover effect - brighten and rotate random shapes + display title
function initServiceCardHover() {
    const serviceItems = document.querySelectorAll('.service-item');
    const shapes = document.querySelectorAll('.shape');
    const titleDisplay = document.querySelector('.card-title-display');
    
    if (serviceItems.length > 0 && shapes.length > 0) {
        serviceItems.forEach((item, index) => {
            item.addEventListener('mouseenter', () => {
                // Get a random shape
                const randomIndex = Math.floor(Math.random() * shapes.length);
                const randomShape = shapes[randomIndex];
                
                // Add active class to trigger animation
                randomShape.classList.add('active');
                
                // Display card title in central glow
                if (titleDisplay) {
                    const cardTitle = item.querySelector('h3');
                    if (cardTitle) {    
                        titleDisplay.textContent = cardTitle.textContent;
                        titleDisplay.classList.add('show');
                    }
                }
                
                // Remove active class after animation completes (600ms)
                setTimeout(() => {
                    randomShape.classList.remove('active');
                }, 600);
            });
            
            item.addEventListener('mouseleave', () => {
                // Hide title display when mouse leaves
                if (titleDisplay) {
                    titleDisplay.classList.remove('show');
                }
            });
        });
    } else {
    }
}

// ===== INITIALIZE SERVICE CARD HOVER =====
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initServiceCardHover);
} else {
    initServiceCardHover();
}

// Ensure initialization after DOM render
setTimeout(initServiceCardHover, 500);

}); // End DOMContentLoaded