(() => {
  const root = document.getElementById("answer-options");
  const image = document.getElementById("clue-image");
  const count = document.getElementById("clue-count");
  const feedback = document.getElementById("clue-feedback");
  const next = document.getElementById("next-clue");
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  if (!root || !image || !next || !feedback || !count) return;
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
      feedback.textContent = "Not quite. Try another character.";
      return;
    }
    found = true;
    button.classList.add("correct");
    feedback.textContent = `That’s ${clues[index].answer}! You know your stuff.`;
    next.hidden = false;
    next.firstChild.textContent =
      index === clues.length - 1 ? "Try the clues again " : "Next clue ";
  });
  next.addEventListener("click", () => {
    index = (index + 1) % clues.length;
    found = false;
    const clue = clues[index];
    image.src = `/assets/studio/${clue.image}.webp`;
    image.alt = clue.alt;
    count.textContent = `${String(index + 1).padStart(2, "0")} / 03`;
    root.replaceChildren(
      ...clue.choices.map((name) => {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.answer = name;
        button.textContent = name;
        return button;
      }),
    );
    feedback.textContent = "Who does this belong to?";
    next.hidden = true;
    root.querySelector("button").focus({ preventScroll: true });
  });
})();
