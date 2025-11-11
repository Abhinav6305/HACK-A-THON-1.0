// Denovate-style animations and interactions for HACK-A-THON 1.0

document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation
    const navLinks = document.querySelectorAll('nav a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Enhanced scroll animations with Intersection Observer
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // Apply fade-in animations to all sections
    const sections = document.querySelectorAll('.event-details, .prizes, .themes, .terms, .rules, .contact, .container');
    sections.forEach(section => {
        section.classList.add('fade-in');
        observer.observe(section);
    });

    // Typing effect for hero text
    const heroText = document.querySelector('.hero-content p');
    if (heroText) {
        const text = heroText.textContent;
        heroText.textContent = '';
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                heroText.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 50);
            }
        };
        setTimeout(typeWriter, 1500);
    }

    // Enhanced form validation with better UX
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('input[required], select[required]');
            let isValid = true;
            let firstInvalidField = null;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#FF004D';
                    field.style.boxShadow = '0 0 0 2px rgba(255, 0, 77, 0.2)';
                    if (!firstInvalidField) firstInvalidField = field;
                } else {
                    field.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                    field.style.boxShadow = 'none';
                }
            });

            if (!isValid) {
                e.preventDefault();
                firstInvalidField.focus();
                showNotification('Please fill all required fields.', 'error');
            }
        });
    });

    // Real-time form validation feedback
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.hasAttribute('required') && !this.value.trim()) {
                this.style.borderColor = '#FF004D';
                this.style.boxShadow = '0 0 0 2px rgba(255, 0, 77, 0.2)';
            } else {
                this.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                this.style.boxShadow = 'none';
            }
        });

        input.addEventListener('focus', function() {
            this.style.borderColor = '#00C2FF';
            this.style.boxShadow = '0 0 0 2px rgba(0, 194, 255, 0.2)';
        });
    });

    // Dynamic counter animation for stats
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = 2000; // 2 seconds
        const increment = target / (duration / 16); // 60fps
        let current = 0;

        const animate = () => {
            current += increment;
            if (current >= target) {
                counter.textContent = target.toLocaleString();
            } else {
                counter.textContent = Math.floor(current).toLocaleString();
                requestAnimationFrame(animate);
            }
        };
        animate();
    });

    // Enhanced hover effects with micro-interactions
    const interactiveElements = document.querySelectorAll('.btn, .container, .logo img');
    interactiveElements.forEach(el => {
        el.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
            this.style.boxShadow = '0 10px 30px rgba(0, 194, 255, 0.2)';
        });
        el.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
            this.style.boxShadow = 'none';
        });
    });

    // Parallax effect for hero section
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.hero');
        if (hero) {
            hero.style.backgroundPositionY = -(scrolled * 0.5) + 'px';
        }
    });

    // Mobile menu toggle (if needed for very small screens)
    const nav = document.querySelector('nav');
    let isMenuOpen = false;

    function toggleMenu() {
        const navUl = document.querySelector('.nav-container ul');
        if (window.innerWidth <= 768) {
            if (isMenuOpen) {
                navUl.style.display = 'none';
                isMenuOpen = false;
            } else {
                navUl.style.display = 'flex';
                navUl.style.flexDirection = 'column';
                navUl.style.position = 'absolute';
                navUl.style.top = '100%';
                navUl.style.left = '0';
                navUl.style.right = '0';
                navUl.style.background = 'rgba(0, 0, 0, 0.95)';
                navUl.style.padding = '1rem';
                navUl.style.backdropFilter = 'blur(10px)';
                isMenuOpen = true;
            }
        }
    }

    // Add mobile menu button if screen is small
    if (window.innerWidth <= 768) {
        const menuBtn = document.createElement('button');
        menuBtn.textContent = '☰';
        menuBtn.style.background = 'none';
        menuBtn.style.border = 'none';
        menuBtn.style.color = 'var(--light)';
        menuBtn.style.fontSize = '1.5rem';
        menuBtn.style.cursor = 'pointer';
        menuBtn.addEventListener('click', toggleMenu);

        const navContainer = document.querySelector('.nav-container');
        navContainer.appendChild(menuBtn);
    }

    // Notification system
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.padding = '1rem 2rem';
        notification.style.borderRadius = '8px';
        notification.style.color = 'white';
        notification.style.fontWeight = 'bold';
        notification.style.zIndex = '1001';
        notification.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';

        if (type === 'error') {
            notification.style.background = '#FF004D';
        } else if (type === 'success') {
            notification.style.background = '#00C2FF';
        } else {
            notification.style.background = '#333';
        }

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    // Add loading animation for forms
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.form.checkValidity()) {
                this.textContent = 'Processing...';
                this.disabled = true;
                this.style.opacity = '0.7';
            }
        });
    });

    // Smooth page transitions
    const pageLinks = document.querySelectorAll('a:not([href^="#"])');
    pageLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.style.opacity = '0';
            setTimeout(() => {
                window.location.href = this.href;
            }, 300);
        });
    });

    // Initialize any counters on page load
    const prizeAmounts = document.querySelectorAll('.prize');
    prizeAmounts.forEach((prize, index) => {
        const amount = prize.textContent.match(/₹([\d,]+)/);
        if (amount) {
            prize.innerHTML = prize.innerHTML.replace(amount[0], `<span class="counter" data-target="${amount[1].replace(/,/g, '')}">0</span>`);
        }
    });
});
