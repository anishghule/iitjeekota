// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { initFilm } from "../src/islands/film.ts";

/** A film that plays and pauses on request, the way a browser's does. */
function setup(): { player: HTMLElement; video: HTMLVideoElement; toggle: HTMLButtonElement; label: HTMLElement } {
  document.body.innerHTML = `<figure data-film-player>
    <video data-film controls></video>
    <button type="button" data-film-toggle hidden aria-pressed="false" data-play="Play the film" data-pause="Pause the film">
      <svg><use href="#i-play"></use></svg><span data-label>Play the film</span>
    </button></figure>`;
  const video = document.querySelector("video") as HTMLVideoElement;
  let paused = true;
  Object.defineProperty(video, "paused", { get: () => paused });
  video.play = vi.fn(async () => {
    paused = false;
    video.dispatchEvent(new Event("play"));
  });
  video.pause = vi.fn(() => {
    paused = true;
    video.dispatchEvent(new Event("pause"));
  });
  initFilm(document.querySelector("figure") as HTMLElement);
  return {
    player: document.querySelector("figure") as HTMLElement,
    video,
    toggle: document.querySelector("button") as HTMLButtonElement,
    label: document.querySelector("[data-label]") as HTMLElement,
  };
}

beforeEach(() => {
  vi.stubGlobal("IntersectionObserver", class { observe() {} disconnect() {} });
});
afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("a film with Play and Pause", () => {
  it("swaps the video's own controls for one Play button", () => {
    const { video, toggle } = setup();
    expect(video.controls).toBe(false);
    expect(toggle.hidden).toBe(false);
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
  });

  it("plays on the button and pauses on the next press, with the label and icon following", async () => {
    const { video, toggle, label } = setup();
    toggle.click();
    await Promise.resolve();
    expect(video.play).toHaveBeenCalledOnce();
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(label.textContent).toBe("Pause the film");
    expect(toggle.querySelector("use")?.getAttribute("href")).toBe("#i-pause");
    toggle.click();
    expect(video.pause).toHaveBeenCalledOnce();
    expect(label.textContent).toBe("Play the film");
    expect(toggle.querySelector("use")?.getAttribute("href")).toBe("#i-play");
  });

  it("also plays and pauses when the picture is pressed", async () => {
    const { video } = setup();
    video.click();
    await Promise.resolve();
    expect(video.play).toHaveBeenCalledOnce();
  });

  it("goes back to Play when the film ends", async () => {
    const { video, toggle, label } = setup();
    toggle.click();
    await Promise.resolve();
    video.dispatchEvent(new Event("ended"));
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    expect(label.textContent).toBe("Play the film");
  });

  it("gives the reader the ordinary controls back if the film cannot play", () => {
    const { video, toggle } = setup();
    video.dispatchEvent(new Event("error"));
    expect(video.controls).toBe(true);
    expect(toggle.hidden).toBe(true);
  });

  it("never reacts to scrolling", () => {
    const { video } = setup();
    window.dispatchEvent(new Event("scroll"));
    expect(video.play).not.toHaveBeenCalled();
    expect(video.currentTime).toBe(0);
  });
});
