// Brand guide: play the motion samples. Each button moves its own track; durations and easings come from tokens.
document.querySelectorAll("[data-play]").forEach(function (button) {
  var track = document.getElementById(button.getAttribute("data-play"));
  if (!track) return;
  button.addEventListener("click", function () {
    var moved = track.classList.toggle("moved");
    button.setAttribute("aria-pressed", moved ? "true" : "false");
    button.textContent = moved ? "Move back" : "Play";
  });
});
