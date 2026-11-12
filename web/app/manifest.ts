import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FINN — your portfolio's editor",
    short_name: "FINN",
    description: "Indian equities: only what changes your view, with proof.",
    start_url: "/brief",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#f7f6f2",
    theme_color: "#16150f",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
