/* FYBRE — fybrelab.com */
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
      { threshold: 0.12, rootMargin: "0px 0px -5% 0px" }
    );
    revealed.forEach((el) => io.observe(el));
  }

  /* ------------------------------------------------ the 24-hour theatre
     Scrolling through #system runs the clock from 06:00 to 06:00:
     the stage darkens as the day protocol hands over to the night one. */
  const system = document.getElementById("system");
  const track = document.getElementById("sys-track");
  const stage = document.getElementById("sys-stage");
  const clock = document.getElementById("sys-clock");
  const phase = document.getElementById("sys-phase");

  if (system && !reduceMotion) {
    system.classList.add("enhanced");

    const NIGHT_AT = 22;          /* lights out */
    const clamp01 = (v) => Math.min(1, Math.max(0, v));
    const smooth = (v) => { v = clamp01(v); return v * v * (3 - 2 * v); };
    let ticking = false;

    const render = () => {
      ticking = false;
      const rect = track.getBoundingClientRect();
      const span = rect.height - window.innerHeight;
      if (span <= 0) return;
      const p = clamp01(-rect.top / span);

      const t = 6 + p * 24;                    /* 06:00 → 30:00 (= 06:00) */
      const hh = String(Math.floor(t % 24)).padStart(2, "0");
      const mm = String(Math.floor((t % 1) * 60)).padStart(2, "0");
      clock.textContent = `${hh}:${mm}`;

      const night = smooth((t - (NIGHT_AT - 1.4)) / 2.2);
      stage.style.setProperty("--p", p.toFixed(4));
      stage.style.setProperty("--night", night.toFixed(3));
      const isNight = night > 0.5;
      stage.classList.toggle("is-night", isNight);
      phase.textContent = isNight ? "Night mode. Growth mode." : "Day mode — Activation";
    };

    const queue = () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(render);
      }
    };
    render();
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", queue);
  }

  /* footer year */
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
