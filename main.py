import streamlit as st
import whisper
import os
import tempfile
from datetime import timedelta
from deep_translator import GoogleTranslator
import subprocess
import shutil

st.set_page_config(page_title="Legendador Automático EN->PT", layout="centered")

st.title("🎬 Legendador e Editor de Vídeo")
st.markdown("Faça upload de um vídeo em **Inglês**, gere a legenda e baixe o vídeo com a **legenda embutida** em Português.")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

def format_timestamp(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def generate_srt_content(transcription_segments):
    srt_content = ""
    translator = GoogleTranslator(source='en', target='pt')
    progress_bar = st.progress(0, text="Traduzindo segmentos...")
    total = len(transcription_segments)

    for i, segment in enumerate(transcription_segments):
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        original_text = segment['text'].strip()

        try:
            translated_text = translator.translate(original_text)
        except Exception:
            translated_text = original_text

        srt_content += f"{i + 1}\n"
        srt_content += f"{start} --> {end}\n"
        srt_content += f"{translated_text}\n\n"
        progress_bar.progress((i + 1) / total, text=f"Traduzindo: {i + 1}/{total}")

    progress_bar.empty()
    return srt_content

def burn_subtitles_ffmpeg(video_input, srt_input, video_output):
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise Exception("FFmpeg não encontrado no sistema.")

    cmd = [
        ffmpeg_path,
        "-i", video_input,
        "-vf", f"subtitles={srt_input}:force_style='FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=20'",
        "-c:a", "copy",
        "-preset", "veryfast",
        video_output,
        "-y"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Erro no FFmpeg: {result.stderr}")
    
    return video_output

uploaded_file = st.file_uploader("Escolha um arquivo de vídeo", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_path = tfile.name

    st.video(video_path)

    if st.button("Gerar Vídeo Legendado"):
        st.divider()
        status_text = st.empty()

        try:
            status_text.info("Carregando IA e transcrevendo áudio...")
            model = load_whisper_model()
            result = model.transcribe(video_path, task="transcribe", language="en")

            status_text.info("Traduzindo legendas...")
            srt_content = generate_srt_content(result['segments'])

            srt_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.srt', mode='w', encoding='utf-8')
            srt_temp.write(srt_content)
            srt_temp_path = srt_temp.name
            srt_temp.close()

            status_text.warning("Renderizando vídeo com legendas via FFmpeg...")
            output_video_path = video_path.replace(".mp4", "_legendado.mp4")

            try:
                burn_subtitles_ffmpeg(video_path, srt_temp_path, output_video_path)
                status_text.success("Vídeo gerado com sucesso!")

                with open(output_video_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Baixar Vídeo Legendado (.mp4)",
                        data=file,
                        file_name="video_legendado.mp4",
                        mime="video/mp4"
                    )

                st.download_button(
                    label="Baixar apenas Legenda (.srt)",
                    data=srt_content,
                    file_name="legenda.srt",
                    mime="text/plain"
                )

                st.video(output_video_path)

            except Exception as e:
                st.error(f"Erro na renderização: {e}")
                st.download_button(label="Baixar .srt (Ocorreu erro no vídeo)", data=srt_content, file_name="legenda.srt")

        except Exception as e:
            st.error(f"Ocorreu um erro geral: {e}")
        
        finally:
            if os.path.exists(video_path): os.remove(video_path)
