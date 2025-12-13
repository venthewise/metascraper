from flask import Flask, request, send_file, jsonify
import subprocess
import os
import shutil
import uuid

app = Flask(__name__)

@app.route("/combine_videos_with_bgm", methods=["POST"])
def combine_videos_with_bgm():
    data = request.json
    videos = data.get("videos", [])
    bgm_url = data.get("bgm")
    bgm_volume = str(data.get("bgm_volume", 0.15))

    if not videos or not bgm_url:
        return jsonify({"error": "Missing videos or bgm"}), 400

    workdir = f"/app/work_{uuid.uuid4().hex}"
    os.makedirs(workdir, exist_ok=True)

    concat_file = os.path.join(workdir, "files.txt")
    stitched_video = os.path.join(workdir, "video.mp4")
    bgm_path = os.path.join(workdir, "bgm.mp3")
    output_path = os.path.join(workdir, "output.mp4")

    try:
        # Download videos
        with open(concat_file, "w") as f:
            for i, url in enumerate(videos):
                clip_path = os.path.join(workdir, f"clip_{i}.mp4")
                subprocess.run(["wget", "-q", "-O", clip_path, url], check=True)
                f.write(f"file '{clip_path}'\n")

        # Download BGM
        subprocess.run(["wget", "-q", "-O", bgm_path, bgm_url], check=True)

        # Step 1: Stitch videos (VIDEO ONLY, NO AUDIO)
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            stitched_video
        ], check=True)

        # Step 2: Loop video and CUT when MP3 ends
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
            "-shortest",          # ✅ THIS IS THE FIX
            output_path
        ], check=True)

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Zero persistence — full cleanup
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
