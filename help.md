
vigilens@0.1.0 dev
> next dev

▲ Next.js 16.2.4 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://169.254.83.107:3000
- Environments: .env.local
✓ Ready in 621ms
⚠ Warning: Next.js inferred your workspace root, but it may not be correct.
We detected multiple lockfiles and selected the directory of C:\Projects\openloop-OL08\package-lock.json as the root directory.
To silence this warning, set `turbopack.root` in your Next.js config, or consider removing one of the lockfiles if it's not needed.
  See https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack#root-directory for more information.
Detected additional lockfiles:
  * C:\Projects\openloop-OL08\frontend\pnpm-lock.yaml


GET / 200 in 454ms (next.js: 186ms, application-code: 267ms)
GET /analysis?url=https%3A%2F%2Fwww.reddit.com%2Fr%2FisthisAI%2Fcomments%2F1rukwol%2Fthis_video_from_netanyahus_official_account_meant%2F%3Futm_source%3Dshare%26utm_medium%3Dweb3x%26utm_name%3Dweb3xcss%26utm_term%3D1%26utm_content%3Dshare_button&demo=false 200 in 77ms (next.js: 36ms, application-code: 42ms)
!!! [PROXY] API ROUTE HIT !!!
[PROXY] Analyze Request: https://www.reddit.com/r/isthisAI/comments/1rukwol/this_video_from_netanyahus_official_account_meant/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
[PROXY] Target Backend: http://localhost:8000/analyze
[PROXY] Calling backend at: http://127.0.0.1:8888/analyze
!!! [PROXY] API ROUTE HIT !!!
[PROXY] Analyze Request: https://www.reddit.com/r/isthisAI/comments/1rukwol/this_video_from_netanyahus_official_account_meant/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (18/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (18/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (19/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (19/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (20/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (20/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (21/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (21/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (22/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (22/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (23/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (23/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (24/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (24/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (25/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (25/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (26/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: processing (26/120)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: processing (27/120)
[PROXY] Job 7806a872-33cc-4b01-a706-2147497c2082 Status: completed (27/120)
POST /api/analyze 200 in 3.4min (next.js: 110ms, application-code: 3.4min)
[PROXY] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 Status: completed (28/120)
POST /api/analyze 200 in 3.4min (next.js: 89ms, application-code: 3.4min)
Activating Virtual Environment...
Starting local Backend...
INFO:     Started server process [24352]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8888 (Press CTRL+C to quit)
[BACKEND] Incoming POST request to /analyze
[BACKEND] Incoming POST request to /analyze
[DEBUG] Job e0168678-72e1-4f3c-ad89-af525e54f0c0 started. Returning ID.
[BACKEND] Finished POST request to /analyze with status 200
INFO:     127.0.0.1:61087 - "POST /analyze HTTP/1.1" 200 OK
[DEBUG] Job 7806a872-33cc-4b01-a706-2147497c2082 started. Returning ID.
[BACKEND] Finished POST request to /analyze with status 200
INFO:     127.0.0.1:61088 - "POST /analyze HTTP/1.1" 200 OK
[PREPROCESS] Resolving URL with yt-dlp: https://www.reddit.com/r/isthisAI/comments/1rukwol/this_video_from_netanyahus_official_account_meant/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
[PREPROCESS] Resolving URL with yt-dlp: https://www.reddit.com/r/isthisAI/comments/1rukwol/this_video_from_netanyahus_official_account_meant/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61087 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[PREPROCESS] [SUCCESS] URL resolved to stream: https://v.redd.it/ttknb20b09pg1/CMAF_1080.mp4?source=fallbac...
[PREPROCESS] Extracting keyframes from: https://www.reddit.com/r/isthisAI/comments/1rukwol...
[DEBUG] FFmpeg Command: ffmpeg -i https://v.redd.it/ttknb20b09pg1/CMAF_1080.mp4?source=fallback -vf fps=1/2 -frames:v 10 -q:v 2 C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_%04d.jpg -y -loglevel error
[PREPROCESS] [SUCCESS] URL resolved to stream: https://v.redd.it/ttknb20b09pg1/CMAF_1080.mp4?source=fallbac...
[PREPROCESS] Extracting keyframes from: https://www.reddit.com/r/isthisAI/comments/1rukwol...
[DEBUG] FFmpeg Command: ffmpeg -i https://v.redd.it/ttknb20b09pg1/CMAF_1080.mp4?source=fallback -vf fps=1/2 -frames:v 10 -q:v 2 C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_%04d.jpg -y -loglevel error
p\vigilens_frames_bnkiy9wj\frame_0007.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0001.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0002.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0003.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0006.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0005.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0008.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0009.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_bnkiy9wj\frame_0010.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[ERROR] FFmpeg audio extraction failed.
[ERROR] Stderr: [out#0/wav @ 0000020400588280] Output file does not contain any stream
Error opening output file C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_audio_lnlrr_wg\audio.wav.
Error opening output files: Invalid argument


[AGENT] deepfake_detector: Started AI-generation check...

[AGENT] context_analyser: Started context & credibility analysis...
Using CPU. Note: This module is much faster with a GPU.
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0002.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0003.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0001.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0005.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0004.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0006.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0009.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0007.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0008.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[DeepFake/DeepSafe] Frame C:\Users\RAFANA~1\AppData\Local\Temp\vigilens_frames_e0_ge1n9\frame_0010.jpg failed: Server error '500 Internal Server Error' for url 'http://localhost:8001/predict'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61106 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[API] [SUCCESS] Metadata extracted: This video from Netanyahu’s official account meant...
[API] [SUCCESS] Metadata extracted: This video from Netanyahu’s official account meant...
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61106 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[Context/OCR] EasyOCR failed: Error(s) in loading state_dict for Model:
        size mismatch for Prediction.weight: copying a param with shape torch.Size([143, 512]) from checkpoint, the shape in current model is torch.Size([127, 512]).
        size mismatch for Prediction.bias: copying a param with shape torch.Size([143]) from checkpoint, the shape in current model is torch.Size([127]).
[Context/OCR] EasyOCR failed: Error(s) in loading state_dict for Model:
        size mismatch for Prediction.weight: copying a param with shape torch.Size([143, 512]) from checkpoint, the shape in current model is torch.Size([127, 512]).
        size mismatch for Prediction.bias: copying a param with shape torch.Size([143]) from checkpoint, the shape in current model is torch.Size([127]).
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61106 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[SourceHunter/Wayback] Failed: Server error '503 Service Unavailable' for url 'http://archive.org/wayback/available?url=https%3A%2F%2Fwww.reddit.com%2Fr%2FisthisAI%2Fcomments%2F1rukwol%2Fthis_video_from_netanyahus_official_account_meant%2F%3Futm_source%3Dshare%26utm_medium%3Dweb3x%26utm_name%3Dweb3xcss%26utm_term%3D1%26utm_content%3Dshare_button'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
[SourceHunter/Wayback] Failed: Server error '503 Service Unavailable' for url 'http://archive.org/wayback/available?url=https%3A%2F%2Fwww.reddit.com%2Fr%2FisthisAI%2Fcomments%2F1rukwol%2Fthis_video_from_netanyahus_official_account_meant%2F%3Futm_source%3Dshare%26utm_medium%3Dweb3x%26utm_name%3Dweb3xcss%26utm_term%3D1%26utm_content%3Dshare_button'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61106 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200
INFO:     127.0.0.1:61087 - "GET /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/7806a872-33cc-4b01-a706-2147497c2082
[BACKEND] Finished GET request to /status/7806a872-33cc-4b01-a706-2147497c2082 with status 200
INFO:     127.0.0.1:61106 - "GET /status/7806a872-33cc-4b01-a706-2147497c2082 HTTP/1.1" 200 OK
[BACKEND] Incoming GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0
[BACKEND] Finished GET request to /status/e0168678-72e1-4f3c-ad89-af525e54f0c0 with status 200


Can you help with my AI detector

Using gemm4:e4b and its running on docker

so currently I want the AI to detect if the video is ai or not but its failing can you check