/* VC Limited — vcltd.co */
(() => {
  "use strict";

  const nav = document.querySelector(".nav");
  const toggle = document.getElementById("nav-toggle");
  const links = document.getElementById("nav-links");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* nav: solid once scrolled */
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 12);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* nav: mobile menu */
  toggle.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  });
  links.addEventListener("click", (e) => {
    if (e.target.matches("a")) {
      links.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  /* scroll reveals */
  const revealed = document.querySelectorAll(".reveal");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealed.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -5% 0px" }
    );
    revealed.forEach((el) => io.observe(el));
  }

  /* stat counters */
  const counters = document.querySelectorAll(".stat-num[data-count]");
  const runCounter = (el) => {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || "";
    const dur = 1100;
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min((t - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  if (!reduceMotion && "IntersectionObserver" in window && counters.length) {
    const cio = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            runCounter(entry.target);
            cio.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.6 }
    );
    counters.forEach((el) => cio.observe(el));
  }

  /* contact form -> prefilled email (no backend required) */
  const form = document.getElementById("contact-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      const v = (id) => document.getElementById(id).value.trim();
      const subject = `Trade enquiry — ${v("cf-name")}${v("cf-company") ? ", " + v("cf-company") : ""}`;
      const body = [
        `Name: ${v("cf-name")}`,
        `Company: ${v("cf-company") || "—"}`,
        `Email: ${v("cf-email")}`,
        "",
        v("cf-message"),
      ].join("\n");
      window.location.href =
        `mailto:info@vcltd.co?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    });
  }

  /* footer year */
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
