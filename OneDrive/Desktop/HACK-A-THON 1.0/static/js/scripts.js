// HACK-A-THON 1.0 — Black & White Minimal UX Enhancer
document.addEventListener('DOMContentLoaded', () => {

    // Smooth scrolling
    document.querySelectorAll('nav a[href^="#"]').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const id = link.getAttribute('href').substring(1);
            const section = document.getElementById(id);
            if (section) section.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // Fade-in effect on scroll
    const fadeObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('fade-in-up');
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('section').forEach(sec => fadeObserver.observe(sec));

    // Mobile navbar toggle
    const navUl = document.querySelector('nav ul');
    const navToggle = document.createElement('button');
    navToggle.textContent = '☰';
    navToggle.className = 'nav-toggle';
    Object.assign(navToggle.style, {
        position: 'absolute',
        right: '1rem',
        top: '1rem',
        background: 'none',
        border: 'none',
        color: '#fff',
        fontSize: '1.8rem',
        cursor: 'pointer',
        display: 'none'
    });
    navUl.parentNode.insertBefore(navToggle, navUl);

    navToggle.addEventListener('click', () => navUl.classList.toggle('show'));
    window.addEventListener('resize', () => {
        navToggle.style.display = window.innerWidth <= 768 ? 'block' : 'none';
        if (window.innerWidth > 768) navUl.classList.remove('show');
    });
    if (window.innerWidth <= 768) navToggle.style.display = 'block';

    // Minimal form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', e => {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            let valid = true;
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = '#f00';
                    valid = false;
                } else {
                    input.style.borderColor = '#fff';
                }
            });
            if (!valid) {
                e.preventDefault();
                alert('Please fill in all required fields before submitting.');
            }
        });
    });
});

// === ADD FLOATING ORBS ON HOME PAGE ===
document.addEventListener('DOMContentLoaded', () => {
    const orbContainer = document.createElement('div');
    orbContainer.classList.add('bg-orb');
    document.body.appendChild(orbContainer);

    for (let i = 0; i < 10; i++) {
        const orb = document.createElement('div');
        orb.classList.add('orb');
        orb.style.left = Math.random() * 100 + '%';
        orb.style.top = Math.random() * 100 + '%';
        orb.style.animationDuration = (10 + Math.random() * 10) + 's';
        orbContainer.appendChild(orb);
    }

    // Reveal on scroll
    const revealEls = document.querySelectorAll('.reveal, .card, .container');
    const revealObs = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('visible');
        });
    }, { threshold: 0.2 });
    revealEls.forEach(el => revealObs.observe(el));

    // Cursor glow
    const glow = document.createElement('div');
    glow.classList.add('cursor-glow');
    document.body.appendChild(glow);
    document.addEventListener('mousemove', e => {
        glow.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
    });
});
