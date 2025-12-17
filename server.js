const express = require("express");
const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const app = express();
app.use(express.json());

const TMP_DIR = "/tmp";

// POST /download
app.post("/download", async (req, res) => {
  const { snapshot_url } = req.body;

  if (!snapshot_url) {
    return res.status(400).json({ error: "snapshot_url is required" });
  }

  const id = crypto.randomUUID();
  const outputFile = path.join(TMP_DIR, `${id}.mp4`);

  // FFmpeg command with browser headers
  const cmd = `
ffmpeg -y \
-headers "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\\r\\nReferer: https://www.facebook.com/\\r\\nAccept: */*\\r\\n" \
-i "${snapshot_url}" \
-c copy \
-movflags +faststart \
"${outputFile}"
`;

  exec(cmd, { timeout: 5 * 60 * 1000 }, (error, stdout, stderr) => {
    if (error) {
      console.error("FFmpeg error:", stderr || error.message);
      return res.status(500).json({
        error: "ffmpeg failed",
        details: stderr || error.message
      });
    }

    // Send the downloaded MP4 back
    res.download(outputFile, `${id}.mp4`, (err) => {
      // Clean up temp file
      fs.unlink(outputFile, () => {});
      if (err) {
        console.error("Download error:", err.message);
      }
    });
  });
});

// Health check endpoint
app.get("/health", (_, res) => {
  res.json({ status: "ok" });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`FFmpeg service running on port ${PORT}`);
});
