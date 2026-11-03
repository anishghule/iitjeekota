/**
 * A film (components/ui/FilmPlayer.astro) is an ordinary film with one Play
 * and Pause button. Scrolling never moves it. It stops when it ends or when it leaves the
 * screen. If the film cannot play, or this script does not run, the video keeps its own controls.
 */

export function initFilm(player: HTMLElement): void {
  const video = player.querySelector<HTMLVideoElement>("video[data-film]");
  const toggle = player.querySelector<HTMLButtonElement>("[data-film-toggle]");
  if (!video || !toggle) return;

  const label = toggle.querySelector<HTMLElement>("[data-label]");
  const icon = toggle.querySelector("use");
  const setPlaying = (on: boolean) => {
    toggle.setAttribute("aria-pressed", String(on));
    if (label) label.textContent = (on ? toggle.dataset.pause : toggle.dataset.play) ?? "";
    icon?.setAttribute("href", on ? "#i-pause" : "#i-play");
  };

  video.controls = false;
  video.muted = true;
  toggle.hidden = false;

  const flip = () => {
    if (video.paused) video.play().catch(() => setPlaying(false));
    else video.pause();
  };
  toggle.addEventListener("click", flip);
  video.addEventListener("click", flip);
  video.addEventListener("play", () => setPlaying(true));
  video.addEventListener("pause", () => setPlaying(false));
  video.addEventListener("ended", () => setPlaying(false));
  // If the film cannot be played, hand the reader the ordinary controls.
  video.addEventListener("error", () => {
    video.controls = true;
    toggle.hidden = true;
  });

  // A film left playing out of sight wastes battery: stop it when it leaves the screen.
  new IntersectionObserver((entries) => {
    if (!video.paused && entries.every((e) => !e.isIntersecting)) video.pause();
  }).observe(player);
}
