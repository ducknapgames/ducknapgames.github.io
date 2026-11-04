(() => {
  let translations = {};
  try { translations = JSON.parse(document.getElementById('site-translations')?.textContent || '{}'); } catch (_) {}
  const t = text => translations[text] || text;
  const root = document.getElementById("answer-options");
  const image = document.getElementById("clue-image");
  const count = document.getElementById("clue-count");
  const feedback = document.getElementById("clue-feedback");
  const next = document.getElementById("next-clue");
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  if (!root || !image || !next || !feedback || !count) return;
  const world = root.closest(".clue-world");
  const card = root.closest(".clue-card");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  function animateClue(frames, options) {
    if (!reducedMotion.matches) image.animate(frames, options);
  }
  function celebrate() {
    if (reducedMotion.matches) return;
    const art = image.getBoundingClientRect();
    const stage = world.getBoundingClientRect();
    const colors = ["#302543", "#f5bc7b", "#b9a3cb", "#faf8f3"];
    for (let i = 0; i < 16; i += 1) {
      const piece = document.createElement("span");
      piece.className = "celebration-piece";
      piece.setAttribute("aria-hidden", "true");
      piece.style.left = `${art.left + art.width / 2 - stage.left}px`;
      piece.style.top = `${art.top + art.height / 2 - stage.top}px`;
      piece.style.background = colors[i % colors.length];
      world.append(piece);
      const direction = (i / 16) * Math.PI * 2;
      const distance = Math.min(100 + (i % 4) * 25, stage.width * 0.4);
      const motion = piece.animate(
        [
          { transform: "translate(0, 0) rotate(0deg)", opacity: 1 },
          { transform: `translate(${Math.cos(direction) * distance}px, ${Math.sin(direction) * distance - 35}px) rotate(${i * 67}deg)`, opacity: 0 },
        ],
        { duration: 650 + (i % 3) * 100, easing: "cubic-bezier(.1,.7,.4,1)" },
      );
      motion.finished.then(() => piece.remove(), () => piece.remove());
    }
  }
  let pointerFrame = 0;
  world.addEventListener("pointermove", (event) => {
    if (!finePointer.matches || reducedMotion.matches || pointerFrame) return;
    const { clientX, clientY } = event;
    pointerFrame = requestAnimationFrame(() => {
      const bounds = world.getBoundingClientRect();
      card.style.setProperty("--tilt-x", `${((clientY - bounds.top) / bounds.height - 0.5) * -4}deg`);
      card.style.setProperty("--tilt-y", `${((clientX - bounds.left) / bounds.width - 0.5) * 4}deg`);
      pointerFrame = 0;
    });
  });
  world.addEventListener("pointerleave", () => {
    cancelAnimationFrame(pointerFrame);
    pointerFrame = 0;
    card.style.removeProperty("--tilt-x");
    card.style.removeProperty("--tilt-y");
  });
  const clues = [
    {
      image: "mario",
      alt: "A red cap and a plumber’s wrench",
      answer: "Mario",
      choices: ["Thor", "Mario", "Luigi"],
    },
    {
      image: "thor",
      alt: "A silver hammer with a short brown handle",
      answer: "Thor",
      choices: ["Thor", "Loki", "Aquaman"],
    },
    {
      image: "ariel",
      alt: "A pair of purple seashells",
      answer: "Ariel",
      choices: ["Elsa", "Belle", "Ariel"],
    },
  ];
  let index = 0;
  let found = false;
  root.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-answer]");
    if (!button || found) return;
    if (button.dataset.answer !== clues[index].answer) {
      button.classList.add("incorrect");
      feedback.textContent = t("Not quite. Try another character.");
      if (!reducedMotion.matches) {
        button.animate(
          [{ transform: "translateX(0)" }, { transform: "translateX(-5px)" }, { transform: "translateX(5px)" }, { transform: "translateX(0)" }],
          { duration: 240, easing: "ease-out" },
        );
      }
      return;
    }
    found = true;
    root.querySelectorAll("button").forEach((choice) => { choice.disabled = true; });
    button.classList.add("correct");
    world.classList.add("found");
    feedback.textContent = t('That’s {name}! You know your stuff.').replace('{name}', t(clues[index].answer));
    animateClue(
      [{ transform: "scale(1) rotate(-2deg)" }, { transform: "scale(1.1) rotate(5deg)" }, { transform: "scale(1) rotate(-2deg)" }],
      { duration: 430, easing: "cubic-bezier(.2,.8,.2,1)" },
    );
    celebrate();
    next.hidden = false;
    next.firstChild.textContent =
      t(index === clues.length - 1 ? "Try the clues again" : "Next clue") + ' ';
    next.focus({ preventScroll: true });
  });
  next.addEventListener("click", () => {
    index = (index + 1) % clues.length;
    found = false;
    world.classList.remove("found");
    const clue = clues[index];
    image.src = `/assets/studio/${clue.image}.webp`;
    image.alt = t(clue.alt);
    const shownIndex = index;
    image.decode().catch(() => {}).then(() => {
      if (index !== shownIndex) return;
      animateClue(
        [{ opacity: 0, transform: "translateY(14px) scale(.85) rotate(-12deg)" }, { opacity: 1, transform: "translateY(0) scale(1) rotate(-2deg)" }],
        { duration: 350, easing: "cubic-bezier(.2,.8,.2,1)" },
      );
    });
    count.textContent = `${String(index + 1).padStart(2, "0")} / 03`;
    card.querySelector(".clue-top > span").textContent = t(index === 0 ? "YOUR FIRST CLUE" : "YOUR NEXT CLUE");
    root.replaceChildren(
      ...clue.choices.map((name) => {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.answer = name;
        button.textContent = t(name);
        return button;
      }),
    );
    feedback.textContent = t("Who does this belong to?");
    next.hidden = true;
    root.querySelector("button").focus({ preventScroll: true });
  });
})();
