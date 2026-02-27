import streamlit as st
import whisper
import os
import tempfile
from datetime import timedelta
from deep_translator import GoogleTranslator
import subprocess
import shutil
import asyncio
import edge_tts
from pydub import AudioSegment

st.set_page_config(page_title="Legendador e Dublador EN->PT", layout="centered")

st.title("🎬 Legendador e Dublador Automático")
st.markdown("Faça upload de um vídeo em **Inglês**, traduza e escolha gerar legenda, dublagem ou ambos em **Português**.")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")

def format_timestamp(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def translate_segments(transcription_segments):
    srt_content = ""
    translated_data = []
    translator = GoogleTranslator(source='en', target='pt')

    progress_bar = st.progress(0)
    total = len(transcription_segments)

    for i, segment in enumerate(transcription_segments):
        start_sec = segment['start']
        end_sec = segment['end']
        original_text = segment['text'].strip()

        try:
            translated_text = translator.translate(original_text)
        except:
            translated_text = original_text

        translated_data.append({
            'start': start_sec,
            'end': end_sec,
            'text': translated_text
        })

        srt_content += f"{i + 1}\n"
        srt_content += f"{format_timestamp(start_sec)} --> {format_timestamp(end_sec)}\n"
        srt_content += f"{translated_text}\n\n"

        progress_bar.progress((i + 1) / total)

    progress_bar.empty()
    return srt_content, translated_data


async def generate_tts(text, output_path, voice):
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(output_path)


def generate_dubbed_audio(translated_segments, video_path):
    progress_bar = st.progress(0)

    original_audio = AudioSegment.from_file(video_path)
    final_audio = AudioSegment.silent(duration=len(original_audio))

    total = len(translated_segments)

    for i, seg in enumerate(translated_segments):
        progress_bar.progress((i + 1) / total)

        text = seg['text'].strip()
        start_ms = int(seg['start'] * 1000)

        if text:
            try:
                temp_tts_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

                # Alterna voz masculina/feminina
                voice = "pt-BR-AntonioNeural" if i % 2 == 0 else "pt-BR-FranciscaNeural"

                asyncio.run(generate_tts(text, temp_tts_path, voice))

                fala = AudioSegment.from_file(temp_tts_path)
                final_audio = final_audio.overlay(fala, position=start_ms)

                os.remove(temp_tts_path)

            except Exception as e:
                st.warning(f"Erro na dublagem: {e}")

    progress_bar.empty()

    audio_output_path = video_path.replace(".mp4", "_dub_audio.wav")
    final_audio.export(audio_output_path, format="wav")

    return audio_output_path


def process_video_ffmpeg(video_input, srt_input, audio_input, video_output, mode):
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise Exception("FFmpeg não encontrado no sistema.")

    srt_input_escaped = srt_input.replace("\\", "/")
    cmd = [ffmpeg_path, "-i", video_input]

    if audio_input and mode in ["Dublado", "Legenda + Dublagem"]:
        cmd.extend(["-i", audio_input])

    if mode == "Apenas Legenda":
        cmd.extend(["-vf", f"subtitles='{srt_input_escaped}'", "-c:a", "copy"])
    elif mode == "Dublado":
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac"])
    elif mode == "Legenda + Dublagem":
        cmd.extend([
            "-vf", f"subtitles='{srt_input_escaped}'",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:a", "aac"
        ])

    cmd.extend([video_output, "-y"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)

    return video_output


uploaded_file = st.file_uploader("Escolha um vídeo", type=["mp4", "mov", "avi"])
process_mode = st.radio("Selecione o modo:", ["Apenas Legenda", "Dublado(Demo)", "Legenda + Dublagem"])

if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_path = tfile.name
    tfile.close()

    st.video(video_path)

    if st.button("Processar Vídeo"):
        st.divider()
        status = st.empty()

        try:
            status.info("Transcrevendo áudio...")
            model = load_whisper_model()
            result = model.transcribe(video_path, task="transcribe", language="en")

            status.info("Traduzindo...")
            srt_content, translated_data = translate_segments(result['segments'])

            srt_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.srt', mode='w', encoding='utf-8')
            srt_temp.write(srt_content)
            srt_temp_path = srt_temp.name
            srt_temp.close()

            audio_path = None
            if process_mode in ["Dublado", "Legenda + Dublagem"]:
                status.info("Gerando dublagem neural...")
                audio_path = generate_dubbed_audio(translated_data, video_path)

            status.info("Renderizando vídeo final...")
            output_video_path = video_path.replace(".mp4", "_final.mp4")

            process_video_ffmpeg(video_path, srt_temp_path, audio_path, output_video_path, process_mode)

            status.success("Concluído!")

            with open(output_video_path, "rb") as file:
                st.download_button("⬇️ Baixar Vídeo", file, "video_final.mp4")

            st.download_button("Baixar Legenda (.srt)", srt_content, "legenda.srt")

            st.video(output_video_path)

        except Exception as e:
            st.error(f"Erro: {e}")

        finally:
            for p in [video_path, srt_temp_path if 'srt_temp_path' in locals() else None]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
