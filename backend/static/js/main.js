/* =========================================================
   MEDICHAT GLOBAL JAVASCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* -----------------------------------------------------
       MOBILE NAVIGATION
    ----------------------------------------------------- */

    const navbar = document.querySelector(".mc-navbar");
    const mobileMenuButton = document.querySelector(".mobile-menu-btn");

    if (navbar && mobileMenuButton) {

        mobileMenuButton.addEventListener("click", () => {
            navbar.classList.toggle("mobile-open");

            const isOpen = navbar.classList.contains("mobile-open");

            mobileMenuButton.setAttribute(
                "aria-expanded",
                isOpen ? "true" : "false"
            );
        });

    }


    /* -----------------------------------------------------
       CLOSE MOBILE MENU AFTER CLICKING A LINK
    ----------------------------------------------------- */

    const mobileNavLinks = document.querySelectorAll(
        ".mc-nav a, .mc-auth a"
    );

    mobileNavLinks.forEach((link) => {

        link.addEventListener("click", () => {

            if (navbar) {
                navbar.classList.remove("mobile-open");
            }

            if (mobileMenuButton) {
                mobileMenuButton.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }

        });

    });


    /* -----------------------------------------------------
       SMOOTH SCROLL FOR INTERNAL LINKS
    ----------------------------------------------------- */

    document.querySelectorAll('a[href^="#"]').forEach((link) => {

        link.addEventListener("click", (event) => {

            const targetId = link.getAttribute("href");

            if (!targetId || targetId === "#") {
                return;
            }

            const target = document.querySelector(targetId);

            if (!target) {
                return;
            }

            event.preventDefault();

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        });

    });


    /* -----------------------------------------------------
       ACTIVE NAVIGATION
    ----------------------------------------------------- */

    const sections = document.querySelectorAll(
        "section[id], footer[id]"
    );

    const navLinks = document.querySelectorAll(
        '.mc-nav a[href^="#"]'
    );

    if (sections.length && navLinks.length) {

        const updateActiveNavigation = () => {

            let currentSection = "";

            sections.forEach((section) => {

                const sectionTop =
                    section.getBoundingClientRect().top;

                if (sectionTop <= 140) {
                    currentSection = section.id;
                }

            });

            navLinks.forEach((link) => {

                const targetId =
                    link.getAttribute("href").substring(1);

                link.classList.toggle(
                    "active",
                    targetId === currentSection
                );

            });

        };

        window.addEventListener(
            "scroll",
            updateActiveNavigation,
            { passive: true }
        );

        updateActiveNavigation();
    }


    /* -----------------------------------------------------
       BUTTON PRESS FEEDBACK
    ----------------------------------------------------- */

    document
        .querySelectorAll(".primary-btn, .secondary-btn, .login-btn, .register-btn")
        .forEach((button) => {

            button.addEventListener("mousedown", () => {
                button.classList.add("pressed");
            });

            button.addEventListener("mouseup", () => {
                button.classList.remove("pressed");
            });

            button.addEventListener("mouseleave", () => {
                button.classList.remove("pressed");
            });

        });


    /* -----------------------------------------------------
       ESC KEY
    ----------------------------------------------------- */

    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {

            if (navbar) {
                navbar.classList.remove("mobile-open");
            }

            if (mobileMenuButton) {
                mobileMenuButton.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }

        }

    });

});