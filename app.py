from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import yt_dlp
import os
import re
import uuid

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] if name else "video"

def clean_error_message(message: str) -> str:
    message = re.sub(r'\x1b\[[0-9;]*m', '', message)
    message = re.sub(r'\[[0-9;]+m', '', message)
    message = message.replace("ERROR:", "").strip()
    return message

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download_video():
    data = request.get_json(silent=True) or {}
    video_url = data.get("url", "").strip()

    if not video_url:
        return jsonify({"success": False, "error": "حط رابط الفيديو أول"}), 400

    unique_id = str(uuid.uuid4())[:8]

    try:
        # أولًا: نجيب المعلومات بدون تحميل
        info_opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        title = safe_filename(info.get("title", "video"))
        ext = info.get("ext", "mp4")
        output_template = os.path.join(DOWNLOAD_FOLDER, f"{title}-{unique_id}.%(ext)s")

        # ثانيًا: نحمل الفيديو
        download_opts = {
    "format": "best",
    "noplaylist": True,
    "outtmpl": output_template,
    "quiet": True,
    "nocheckcertificate": True,
    "geo_bypass": True,
}

        with yt_dlp.YoutubeDL(download_opts) as ydl:
            result = ydl.extract_info(video_url, download=True)
            final_path = ydl.prepare_filename(result)

            # لو تم الدمج إلى mp4 قد يتغير الاسم النهائي
            possible_mp4 = os.path.splitext(final_path)[0] + ".mp4"
            if os.path.exists(possible_mp4):
                final_path = possible_mp4

        filename = os.path.basename(final_path)
        download_url = url_for("serve_download", filename=filename)

        return jsonify({
            "success": True,
            "title": title,
            "download_url": download_url,
            "filename": filename
        })

    except Exception as e:
     error_text = clean_error_message(str(e))

     if "DRM protected" in error_text:
        friendly_error = "هذا الفيديو محمي ولا يمكن تنزيله."
     else:
        friendly_error = f"صار خطأ أثناء التحميل: {error_text}"

    return jsonify({
        "success": False,
        "error": friendly_error
    }), 500


@app.route("/downloads/<path:filename>")
def serve_download(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)