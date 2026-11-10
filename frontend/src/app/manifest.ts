import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DaJuice OS",
    short_name: "DaJuice",
    description: "科目选择、概念卡片与专注练习组成的 Y2K 学习终端。",
    start_url: "/",
    display: "standalone",
    background_color: "#08060d",
    theme_color: "#ff2ea6",
    icons: [
      {
        src: "/icons/dajuice-192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icons/dajuice-512.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  };
}
