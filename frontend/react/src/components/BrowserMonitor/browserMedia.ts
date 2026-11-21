export type Detection = { name: string; conf: number; box: number[] };
export type FrameResult = {
  detections: Detection[];
  alarm: boolean;
  blocked: string[];
};

export class BrowserSiren {
  private context = new AudioContext();
  private gain = this.context.createGain();
  private oscillator = this.context.createOscillator();
  private timer: number | undefined;
  constructor() {
    this.gain.gain.value = 0;
    this.oscillator.type = "sine";
    this.oscillator.frequency.value = 850;
    this.oscillator.connect(this.gain);
    this.gain.connect(this.context.destination);
    this.oscillator.start();
  }
  enable() {
    return this.context.resume();
  }
  set(active: boolean) {
    window.clearInterval(this.timer);
    this.gain.gain.setTargetAtTime(
      active ? 0.15 : 0,
      this.context.currentTime,
      0.025,
    );
    if (active) {
      let high = false;
      this.timer = window.setInterval(() => {
        high = !high;
        this.oscillator.frequency.setValueAtTime(
          high ? 1200 : 850,
          this.context.currentTime,
        );
      }, 600);
    }
  }
  close() {
    window.clearInterval(this.timer);
    this.oscillator.stop();
    void this.context.close();
  }
}

export function capture(video: HTMLVideoElement, canvas: HTMLCanvasElement) {
  if (!video.videoWidth) return null;
  const ratio = Math.min(1, 1280 / video.videoWidth, 720 / video.videoHeight);
  canvas.width = Math.max(1, Math.round(video.videoWidth * ratio));
  canvas.height = Math.max(1, Math.round(video.videoHeight * ratio));
  const context = canvas.getContext("2d")!;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.72).split(",")[1];
}

export function annotate(canvas: HTMLCanvasElement, detections: Detection[]) {
  const context = canvas.getContext("2d")!;
  context.font = "16px Arial";
  context.lineWidth = 2;
  for (const detection of detections) {
    const [x1, y1, x2, y2] = detection.box;
    context.strokeStyle = "#FF3B8D";
    context.strokeRect(x1, y1, x2 - x1, y2 - y1);
    const label = `${detection.name} ${Math.round(detection.conf * 100)}%`;
    const y = Math.max(22, y1);
    context.fillStyle = "#111111";
    context.fillRect(x1, y - 22, context.measureText(label).width + 12, 22);
    context.fillStyle = "#ffffff";
    context.fillText(label, x1 + 6, y - 6);
  }
}
