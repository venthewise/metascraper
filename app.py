from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid
import json

app = Flask(__name__)

@app.route("/combine_videos_with_bgm", methods=["POST"])
def combine_videos_with_bgm():
    # multipart/form-data
    videos_raw = request.form.get("videos")
    bgm_file = request.files.get("bgm")
    bgm_volume = request.form.get("bgm_volume", "0.15")

    if not videos_raw or not bgm_file:
        return jsonify({"error": "Missing videos or bgm"}), 400

    try:
        videos = json.loads(videos_raw)
        if not isinstance(videos, list) or len(videos) == 0:
            raise ValueError
    except Exception:
        return jsonify({"error": "videos must be a JSON array of URLs"}), 400

    workdir = f"/app/work_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    concat_file = os.path.join(workdir, "files.txt")
    stitched_video = os.path.join(workdir, "video.mp4")
    bgm_path = os.path.join(workdir, "bgm.mp3")
    output_path = os.path.join(workdir, "output.mp4")

    try:
        # Save uploaded BGM
        bgm_file.save(bgm_path)

        # Download videos
        with open(concat_file, "w") as f:
            for i, url in enumerate(videos):
                clip_path = os.path.join(workdir, f"clip_{i}.mp4")
                subprocess.run(
                    ["wget", "-q", "-O", clip_path, url],
                    check=True
                )
                f.write(f"file '{clip_path}'\n")

        # Step 1: Stitch videos (video only, muted)
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            stitched_video
        ], check=True)

        # Step 2: Loop video, add BGM, CUT when MP3 ends
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", stitched_video,
            "-i", bgm_path,
            "-filter_complex", f"[1:a]volume={bgm_volume}[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ], check=True)

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
