import { useEffect, useRef, useState } from "react";
import { api, ApiError, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import {
  BrowserSiren,
  capture,
  annotate,
  type FrameResult,
} from "./browserMedia";

type Active = {
  id: string;
  stream: MediaStream;
  video: HTMLVideoElement;
  siren: BrowserSiren;
  timer?: number;
  request?: AbortController;
  lastAlarm: boolean;
};
export function useBrowserMonitor(notify: Notify) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const active = useRef<Active | null>(null);
  const generation = useRef(0);
  const starting = useRef(false);
  const inspecting = useRef(false);
  const resumeAfter = useRef(0);
  const [preview, setPreview] = useState(false);
  const [running, setRunning] = useState(false),
    [busy, setBusy] = useState(false);
  const [alarm, setAlarm] = useState(false),
    [status, setStatus] = useState("Not sharing");
  const [result, setResult] = useState<FrameResult | null>(null);
  const [model, setModel] = useState("");

  function release() {
    generation.current++;
    const current = active.current;
    active.current = null;
    if (current) {
      clearTimeout(current.timer);
      current.request?.abort();
      current.stream.getTracks().forEach((track) => track.stop());
      current.video.srcObject = null;
      current.siren.close();
    }
    return current;
  }
  useEffect(() => {
    const teardown = () => {
      const current = release();
      if (current)
        void api(`/teacher/browser/${current.id}/stop`, {
          ...json("POST"),
          keepalive: true,
        }).catch(() => {});
    };
    const restored = () => {
      if (!active.current) {
        setRunning(false);
        setAlarm(false);
        setBusy(false);
        setStatus("Not sharing");
        inspecting.current = false;
        setPreview(false);
      }
    };
    window.addEventListener("pagehide", teardown);
    window.addEventListener("pageshow", restored);
    return () => {
      window.removeEventListener("pagehide", teardown);
      window.removeEventListener("pageshow", restored);
      teardown();
    };
  }, []);

  async function stop() {
    const current = release();
    setRunning(false);
    setAlarm(false);
    setBusy(false);
    setStatus("Sharing stopped");
    inspecting.current = false;
    setPreview(false);
    if (current) {
      try {
        await api(`/teacher/browser/${current.id}/stop`, json("POST"));
      } catch (error) {
        notify("Sharing stopped on this PC. " + errorText(error), "error");
      }
    }
  }
  async function start() {
    if (starting.current || active.current) return;
    if (!window.isSecureContext || !navigator.mediaDevices?.getDisplayMedia) {
      notify(
        "Use a desktop Chrome or Edge browser with the HTTPS link to share a screen.",
        "error",
      );
      return;
    }
    starting.current = true;
    const attempt = ++generation.current;
    setBusy(true);
    setStatus("Choose Entire screen in the browser window");
    let stream: MediaStream | null = null,
      siren: BrowserSiren | null = null,
      id = "";
    try {
      // Both permission requests start directly from the teacher's click.
      siren = new BrowserSiren();
      const sound = siren.enable();
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "monitor" },
        audio: false,
      });
      await sound;
      if (generation.current !== attempt)
        throw new Error("Screen sharing cancelled.");
      const video = document.createElement("video");
      video.muted = true;
      video.playsInline = true;
      video.srcObject = stream;
      await video.play();
      const session = await api<{ id: string; model: string }>(
        "/teacher/browser/start",
        json("POST"),
      );
      id = session.id;
      if (
        generation.current !== attempt ||
        stream.getVideoTracks()[0].readyState === "ended"
      )
        throw new Error("Screen sharing ended before monitoring could start.");
      const current: Active = { id, stream, video, siren, lastAlarm: false };
      active.current = current;
      stream.getVideoTracks()[0].addEventListener(
        "ended",
        () => {
          if (active.current === current) void stop();
        },
        { once: true },
      );
      setModel(session.model);
      inspecting.current = false;
      setPreview(false);
      setResult(null);
      setRunning(true);
      setStatus("Sharing · waiting for the first result");
      const next = async () => {
        if (active.current !== current) return;
        if (inspecting.current || performance.now() < resumeAfter.current) {
          current.timer = window.setTimeout(next, 1000);
          return;
        }
        try {
          const frame = document.createElement("canvas");
          const jpeg = capture(video, frame);
          if (jpeg) {
            current.request = new AbortController();
            const response = await api<FrameResult>(
              `/teacher/browser/${id}/frame`,
              {
                ...json("POST", { jpeg }),
                signal: current.request.signal,
              },
            );
            if (active.current !== current) return;
            if (inspecting.current) {
              current.timer = window.setTimeout(next, 1000);
              return;
            }
            if (canvas.current) {
              canvas.current.width = frame.width;
              canvas.current.height = frame.height;
              canvas.current.getContext("2d")!.drawImage(frame, 0, 0);
              annotate(canvas.current, response.detections);
            }
            current.siren.set(response.alarm);
            if (response.alarm && !current.lastAlarm)
              notify(
                "Shared PC opened: " + response.blocked.join(", "),
                "error",
              );
            current.lastAlarm = response.alarm;
            setAlarm(response.alarm);
            setResult(response);
            setStatus("Sharing · AI checked the latest screen");
          }
        } catch (error) {
          if (active.current !== current) return;
          if (!inspecting.current) setStatus(errorText(error));
          if (error instanceof ApiError && [401, 403].includes(error.status)) {
            void stop();
            return;
          }
        }
        if (active.current === current)
          current.timer = window.setTimeout(next, 2000);
      };
      void next();
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      siren?.close();
      if (id)
        void api(`/teacher/browser/${id}/stop`, json("POST")).catch(() => {});
      if (generation.current === attempt) {
        setStatus("Not sharing");
        notify(errorText(error), "error");
      }
    } finally {
      starting.current = false;
      if (generation.current === attempt) setBusy(false);
    }
  }
  function togglePreview() {
    inspecting.current = !inspecting.current;
    setPreview(inspecting.current);
    if (inspecting.current) {
      active.current?.request?.abort();
      setStatus("Monitoring paused · reviewing the latest capture");
    } else {
      // Let the shared display update after the old screenshot is hidden.
      resumeAfter.current = performance.now() + 1500;
      setStatus("Resuming monitoring · waiting for a fresh capture");
    }
  }
  async function silence() {
    const current = active.current;
    if (!current) return;
    setBusy(true);
    try {
      await api(`/teacher/browser/${current.id}/stop-alarm`, json("POST"));
      if (active.current === current) {
        current.request?.abort();
        current.lastAlarm = false;
        current.siren.set(false);
        setAlarm(false);
        notify("Browser alarm stopped.");
      }
    } catch (error) {
      notify(errorText(error), "error");
    } finally {
      setBusy(false);
    }
  }
  return {
    canvas,
    start,
    stop,
    silence,
    running,
    busy,
    alarm,
    status,
    result,
    model,
    preview,
    togglePreview,
  };
}
