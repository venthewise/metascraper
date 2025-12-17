const express = require("express");
const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const app = express();
app.use(express.json());

const TMP_DIR = "/tmp";

app.post("/download", async (req, res) => {
  const { snapshot_url } = req.body;

  if (!snapshot_url) {
    return res.status(400).json({ error: "snapshot_url is required" });
  }

  const id = crypto.randomUUID();
  const outputFile = path.join(TMP_DIR, `${id}.mp4`);

  const cmd = `ffmpeg -y -i "${snapshot_url}" -c copy -movflags +faststart "${outputFile}"`;

  exec(cmd, { timeout: 5 * 60 * 1000 }, (error) => {
    if (error) {
      return res.status(500).json({
        error: "ffmpeg failed",
        details: error.message
      });
    }

    res.download(outputFile, `${id}.mp4`, () => {
      fs.unlink(outputFile, () => {});
    });
  });
});

app.get("/health", (_, res) => {
  res.json({ status: "ok" });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`ffmpeg service running on ${PORT}`);
});
