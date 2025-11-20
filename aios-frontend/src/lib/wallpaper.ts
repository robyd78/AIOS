import { open } from "@tauri-apps/plugin-dialog";
import { convertFileSrc } from "@tauri-apps/api/core";
import { readFile } from "@tauri-apps/plugin-fs";

export type WallpaperSelection = { url: string; needsRevoke: boolean };

const MIME_BY_EXT: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
};

function guessMime(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "jpg";
  return MIME_BY_EXT[ext] ?? "image/*";
}

export async function pickWallpaper(): Promise<WallpaperSelection | null> {
  try {
    const path = await open({
      multiple: false,
      directory: false,
      filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "webp"] }],
    });
    if (!path || Array.isArray(path)) return null;

    try {
      const data = await readFile(path);
      const blob = new Blob([data], { type: guessMime(path) });
      const objectUrl = URL.createObjectURL(blob);
      return { url: objectUrl, needsRevoke: true };
    } catch (error) {
      console.warn("readBinaryFile failed, falling back to convertFileSrc", error);
      const url = convertFileSrc(path);
      return { url, needsRevoke: false };
    }
  } catch (error) {
    console.warn("wallpaper picker failed", error);
    return null;
  }
}
