function scrollToSection(targetId) {
    const targetElement = document.getElementById(targetId);
    if (targetElement) {
        targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function removeAfterDelay(selector, seconds) {
    let e = document.querySelector(selector);
    setTimeout(() => {
        e.remove();
    }, seconds * 1000);
}
