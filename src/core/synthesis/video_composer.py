import os
import ffmpeg
import imageio_ffmpeg
import wave
import contextlib

class VideoComposer:
    def __init__(self):
        # Get ffmpeg executable path from imageio_ffmpeg
        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"VideoComposer initialized with ffmpeg: {self.ffmpeg_path}")
        # We don't have ffprobe in imageio_ffmpeg, so probing might fail if we don't have it in system path.
        # We will rely on try-except blocks or alternative duration checking.

    def get_audio_duration(self, audio_path):
        # Method 1: Use wave module if it's a wav file
        if audio_path.lower().endswith('.wav'):
            try:
                with contextlib.closing(wave.open(audio_path, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    return frames / float(rate)
            except Exception:
                pass
        
        # Method 2: Try to use ffprobe if available in system
        try:
            probe = ffmpeg.probe(audio_path)
            dur = float(probe['format']['duration'])
            print(f"Audio duration (ffprobe) for {os.path.basename(audio_path)}: {dur}")
            return dur
        except Exception as e:
            print(f"ffprobe failed: {e}")
            
        # Method 3: Use ffmpeg -i to get duration (fallback if ffprobe missing)
        try:
            import subprocess
            import re
            
            # Use the ffmpeg executable we know exists
            cmd = [self.ffmpeg_path, '-i', audio_path]
            # ffmpeg prints info to stderr
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = result.stderr
            
            # Search for "Duration: 00:00:05.32,"
            match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", output)
            if match:
                hours = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(3))
                total_seconds = hours * 3600 + minutes * 60 + seconds
                print(f"Audio duration (ffmpeg -i) for {os.path.basename(audio_path)}: {total_seconds}")
                return total_seconds
        except Exception as e:
            print(f"ffmpeg duration check failed: {e}")

        print(f"Could not determine duration for {audio_path}, defaulting to 3.0s")
        return 3.0

    def get_video_info(self, path):
        # Method 1: ffprobe
        try:
            probe = ffmpeg.probe(path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                return int(video_stream['width']), int(video_stream['height'])
        except Exception:
            pass
            
        # Method 2: ffmpeg -i
        try:
            import subprocess
            import re
            cmd = [self.ffmpeg_path, '-i', path]
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = result.stderr
            # Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1280x720, 2373 kb/s, ...
            match = re.search(r"Video: .+, (\d+)x(\d+)", output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception as e:
            print(f"ffmpeg video info check failed: {e}")
            
        return None, None

    def create_clip(self, image_path, audio_path, output_path, duration=None, width=1024, height=1024, quality="high"):
        """
        Combines image and audio into a video clip.
        Uses Crop-to-Fill to avoid distortion.
        """
        try:
            # Determine bitrate based on quality
            crf_val = 20
            if quality == "medium":
                crf_val = 24
            elif quality == "low":
                crf_val = 29

            input_image = ffmpeg.input(image_path, loop=1)
            
            if audio_path:
                input_audio = ffmpeg.input(audio_path)
                # Get audio duration if not provided
                if duration is None:
                    duration = self.get_audio_duration(audio_path)
                    print(f"Detected audio duration: {duration}s")
                    # Add a larger buffer to prevent cutting off the end
                    if duration > 0:
                        duration += 0.5 
                
                # Video stream: Scale to fill and crop
                # scale=w:h:force_original_aspect_ratio=increase
                # crop=w:h
                v = (
                    input_image
                    .filter('scale', width, height, force_original_aspect_ratio='increase', flags='lanczos')
                    .filter('crop', width, height)
                )
                
                # Combine
                out = ffmpeg.output(v, input_audio, output_path, t=duration, pix_fmt='yuv420p', vcodec='libx264', crf=crf_val, acodec='aac', ar=44100, ac=2)
            else:
                # Silent clip
                if duration is None: duration = 3.0
                v = (
                    input_image
                    .filter('scale', width, height, force_original_aspect_ratio='increase', flags='lanczos')
                    .filter('crop', width, height)
                )
                a = ffmpeg.input('anullsrc=r=44100:cl=stereo', format='lavfi', t=duration)
                out = ffmpeg.output(v, a, output_path, t=duration, pix_fmt='yuv420p', vcodec='libx264', crf=crf_val, acodec='aac', ar=44100, ac=2)

            # Explicitly pass the ffmpeg executable path
            out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            return output_path, duration
        except Exception as e:
            print(f"Error creating clip: {e}")
            return None, 0

    def extract_audio(self, video_path, output_audio_path):
        """
        Extracts audio from a video file.
        """
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output_audio_path, acodec='pcm_s16le', ac=1, ar=16000) # 16kHz mono for Whisper
                .run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            )
            return output_audio_path
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return None

    def create_video_clip(self, video_path, audio_path, output_path, duration=None, width=1024, height=1024, quality="high"):
        """
        Combines video and audio into a video clip.
        Loops video if shorter than audio.
        Uses Crop-to-Fill to avoid distortion.
        """
        try:
            # Determine bitrate based on quality
            crf_val = 20
            if quality == "medium":
                crf_val = 24
            elif quality == "low":
                crf_val = 29

            # Get audio duration if not provided
            if duration is None:
                duration = self.get_audio_duration(audio_path)
                print(f"Detected video-audio duration: {duration}s")
                # Add a larger buffer to prevent cutting off the end
                if duration > 0:
                    duration += 1.0

            input_video = ffmpeg.input(video_path, stream_loop=-1) # Loop indefinitely
            input_audio = ffmpeg.input(audio_path)
            
            # Video stream: Scale to fill and crop
            v = (
                input_video
                .filter('scale', width, height, force_original_aspect_ratio='increase', flags='lanczos')
                .filter('crop', width, height)
            )
            
            # Combine
            out = ffmpeg.output(v, input_audio, output_path, t=duration, pix_fmt='yuv420p', vcodec='libx264', crf=crf_val, acodec='aac', ar=44100, ac=2)
            out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            return output_path, duration
        except Exception as e:
            print(f"Error creating video clip: {e}")
            return None, 0

    def burn_subtitles(self, video_path, srt_path, output_path, style_config=None):
        """
        Burns subtitles into the video.
        """
        try:
            # Escape path for Windows: replace \ with / and escape :
            # e.g. C:\file.srt -> C\:/file.srt
            # Actually, ffmpeg filter syntax is complex.
            # Safest is usually forward slashes and escaping the colon after drive letter.
            
            # Method 1: Relative path if possible (risky if CWD differs)
            # Method 2: Full escaping
            
            try:
                # Try to use relative path to avoid drive letter colon issues
                rel_path = os.path.relpath(srt_path)
                safe_srt_path = rel_path.replace('\\', '/')
            except ValueError:
                # If on different drive, fallback to absolute with escaping
                # Escape backslashes and colon
                # For ffmpeg-python, we might need to be careful.
                # Trying: E:/path -> E\:/path
                safe_srt_path = srt_path.replace('\\', '/').replace(':', '\\:')

            print(f"DEBUG: Burning subtitles with path: {safe_srt_path}")
            
            # Style config can be used to set font, size, etc. in ForceStyle
            # e.g. ForceStyle='FontName=Arial,FontSize=24'
            style_str = ""
            if style_config:
                styles = []
                if 'font_size' in style_config:
                    styles.append(f"FontSize={style_config['font_size']}")
                if 'font_color' in style_config:
                    # FFmpeg expects &HBBGGRR
                    # We'll assume white for now or implement conversion later
                    pass
                if styles:
                    style_str = ":force_style='" + ",".join(styles) + "'"

            video = ffmpeg.input(video_path)
            audio = video.audio
            
            # subtitles filter
            # subtitles='filename'[options]
            # On Windows, we need to specify a font that supports Chinese to avoid boxes/garbled text.
            # Microsoft YaHei is a good default.
            
            style_settings = 'FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=20,FontName=Microsoft YaHei'
            
            out = ffmpeg.output(
                video.filter('subtitles', safe_srt_path, force_style=style_settings),
                audio,
                output_path,
                vcodec='libx264',
                acodec='aac',
                ar=44100, # Force standard sample rate
                ac=2      # Force stereo
            )
            out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=False)
            return output_path
        except Exception as e:
            print(f"Error burning subtitles: {e}")
            return None

    def replace_audio(self, video_path, audio_path, output_path):
        """
        Replaces the audio track of a video with a new audio file.
        Adjusts video duration to match audio:
        - If Audio < Video: Cuts video.
        - If Audio > Video: Freezes last frame of video to fill time.
        """
        try:
            # Get durations
            audio_dur = self.get_audio_duration(audio_path)
            # We can't easily get video duration without ffprobe, but we can let ffmpeg handle it.
            
            input_video = ffmpeg.input(video_path)
            input_audio = ffmpeg.input(audio_path)
            
            # Logic:
            # We want the output to be exactly audio_dur length.
            # We take the video stream.
            # If we just map them, ffmpeg stops at the shortest input by default (or longest depending on map).
            # To handle "Audio > Video", we need to loop or freeze.
            # Freezing last frame is complex in pure ffmpeg-python without complex filter graphs.
            # Simpler approach: Loop video? No, that looks weird for talking.
            # Let's try a simple "shortest=False" (stops at longest) but pad video?
            # Actually, tpad filter can pad video.
            
            # For now, let's implement the simple "Cut to shortest" or "Stop at audio end".
            # If video is shorter, it will just stop (black screen?).
            # Let's try to force the video to loop if needed? No.
            
            # Robust approach:
            # 1. Generate video stream that is long enough (loop or tpad).
            # 2. Cut to audio duration.
            
            # Using tpad to extend video indefinitely (by repeating last frame)
            # tpad=stop_mode=clone:stop_duration=-1 (infinite)
            # But tpad might not be available in older ffmpeg.
            
            # Fallback: Just combine. If video ends, it ends.
            # But we want to ensure the audio plays fully.
            
            v = input_video['v']
            a = input_audio['a']
            
            # Apply tpad if possible (requires ffmpeg 4.2+)
            # We assume a relatively modern ffmpeg.
            # stop_mode=clone repeats the last frame.
            v = v.filter('tpad', stop_mode='clone', stop_duration=60) # Add 60s buffer
            
            out = ffmpeg.output(v, a, output_path, t=audio_dur, vcodec='libx264', acodec='aac', strict='experimental')
            out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            return output_path
            
        except Exception as e:
            print(f"Error replacing audio: {e}")
            # Fallback: Simple mux (might cut audio if video is short)
            try:
                input_video = ffmpeg.input(video_path)
                input_audio = ffmpeg.input(audio_path)
                out = ffmpeg.output(input_video, input_audio, output_path, c='copy', map_metadata=-1)
                out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
                return output_path
            except:
                return None

    def concat_clips(self, clip_paths, output_path, bgm_path=None, quality="high", transition_duration=0.5):
        """
        Concatenates multiple video clips into one, optionally adding background music.
        quality: "high" (default), "medium", "low"
        transition_duration: Duration of cross-dissolve transition in seconds. 0 to disable.
        """
        try:
            # Determine bitrate based on quality
            crf_val = 20
            if quality == "medium":
                crf_val = 24
            elif quality == "low":
                crf_val = 29
                
            print(f"Concatenating with quality={quality} (crf={crf_val}), transition={transition_duration}s")

            # Use xfade if transition is requested and we have multiple clips
            if transition_duration > 0 and len(clip_paths) > 1:
                return self._concat_with_xfade(clip_paths, output_path, bgm_path, crf_val, transition_duration)

            # 1. Concat Video (Standard)
            list_path = output_path + ".txt"
            temp_video = output_path + ".temp.mp4"
            
            with open(list_path, 'w', encoding='utf-8') as f:
                for path in clip_paths:
                    abs_path = os.path.abspath(path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
            
            # Generate concatenated video (with voice)
            print("Concatenating clips (re-encoding for sync)...")
            (
                ffmpeg
                .input(list_path, format='concat', safe=0)
                .output(temp_video, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', r=25, crf=crf_val) # Force 25fps, apply CRF
                .run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=False)
            )
            os.remove(list_path)

            # 2. Mix BGM if provided
            self._mix_bgm(temp_video, output_path, bgm_path)
                
        except Exception as e:
            print(f"Error concatenating clips: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _mix_bgm(self, video_path, output_path, bgm_path):
        if bgm_path and os.path.exists(bgm_path):
            try:
                video = ffmpeg.input(video_path)
                bgm = ffmpeg.input(bgm_path)
                
                # Mix: [0:a] is voice, [1:a] is bgm.
                out = ffmpeg.output(
                    video['v'], 
                    ffmpeg.filter([video['a'], bgm.filter('volume', 0.2)], 'amix', inputs=2, duration='first'),
                    output_path,
                    vcodec='copy', # Video is already re-encoded above, so copy is safe here
                    acodec='aac'
                )
                out.run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
                if os.path.exists(video_path) and video_path != output_path:
                    os.remove(video_path)
            except Exception as e:
                print(f"Error mixing BGM: {e}")
                # Fallback: just move video
                if os.path.exists(output_path): os.remove(output_path)
                os.rename(video_path, output_path)
        else:
            # Just rename temp to output
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(video_path, output_path)

    def _concat_with_xfade(self, clip_paths, output_path, bgm_path, crf_val, transition_duration):
        print("Starting Cross-Dissolve Concatenation...")
        import subprocess
        
        # 1. Get durations and target resolution
        durations = []
        target_w, target_h = 0, 0
        
        for i, p in enumerate(clip_paths):
            d = self.get_audio_duration(p)
            durations.append(d)
            
            if i == 0:
                w, h = self.get_video_info(p)
                if w and h:
                    target_w, target_h = w, h
                    print(f"Target resolution set to {target_w}x{target_h} from first clip.")
                else:
                    target_w, target_h = 1920, 1080
                    print("Could not determine resolution of first clip, defaulting to 1920x1080")
            
        # 2. Build Filter Complex
        # Inputs
        inputs = []
        for p in clip_paths:
            inputs.extend(["-i", p])
            
        filter_complex = ""
        
        # Pre-process inputs to scale them to target resolution
        # This ensures xfade works even if clips have different resolutions
        scale_filters = ""
        scaled_labels = []
        
        for i in range(len(clip_paths)):
            lbl = f"s{i}"
            # Scale to fit, then pad to fill
            # Also force fps=25 and format=yuv420p to ensure timebase and pixel format match for xfade
            scale_filters += f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,format=yuv420p[{lbl}];"
            scaled_labels.append(lbl)
            
        filter_complex += scale_filters
        
        current_offset = 0
        
        # Video Chain
        # [s0][s1]xfade=...:offset=O1[v1]
        # [v1][s2]xfade=...:offset=O2[v2]
        
        # Audio Chain
        # [0:a][1:a]acrossfade=d=T[a1]
        # [a1][2:a]acrossfade=d=T[a2]
        
        accumulated_duration = 0
        
        # Video Filters
        last_v_label = scaled_labels[0]
        last_a_label = "0:a"
        
        for i in range(len(clip_paths) - 1):
            accumulated_duration += durations[i]
            offset = accumulated_duration - (i + 1) * transition_duration
            
            next_v_label = f"v_out_{i+1}"
            next_a_label = f"a_out_{i+1}"
            
            # Video xfade
            # Use last_v_label (previous result) and scaled_labels[i+1] (next clip)
            filter_complex += f"[{last_v_label}][{scaled_labels[i+1]}]xfade=transition=fade:duration={transition_duration}:offset={offset}[{next_v_label}];"
            
            # Audio acrossfade
            filter_complex += f"[{last_a_label}][{i+1}:a]acrossfade=d={transition_duration}[{next_a_label}];"
            
            last_v_label = next_v_label
            last_a_label = next_a_label
            
        # Remove trailing semicolon
        filter_complex = filter_complex.rstrip(';')
        
        # Map final labels
        map_v = f"[{last_v_label}]"
        map_a = f"[{last_a_label}]"
        
        temp_video = output_path + ".temp.mp4"
        
        # Write filter complex to file to avoid length limit
        filter_script_path = output_path + ".filter"
        with open(filter_script_path, "w", encoding="utf-8") as f:
            f.write(filter_complex)
            
        cmd = [self.ffmpeg_path] + inputs + [
            "-filter_complex_script", filter_script_path,
            "-map", map_v,
            "-map", map_a,
            "-c:v", "libx264",
            "-crf", str(crf_val),
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-y", temp_video
        ]
        
        print(f"Running xfade command with {len(clip_paths)} clips...")
        # print(" ".join(cmd)) # Debug
        
        try:
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE) # Capture stderr to avoid spam, or remove to see progress
            os.remove(filter_script_path)
            
            # Mix BGM
            self._mix_bgm(temp_video, output_path, bgm_path)
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg xfade failed: {e}")
            if e.stderr:
                print(e.stderr.decode())
            return None
