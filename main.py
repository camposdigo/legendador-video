import streamlit as st
import whisper
import os
import tempfile
from datetime import timedelta
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
from deep_translator import GoogleTranslator
import subprocess


def fix_imagemagick_policy():
    try:
        cmd = """sed -i 's/rights="none" pattern="@*"/rights="read|write" pattern="@*"/g' /etc/ImageMagick-6/policy.xml"""
        subprocess.run(cmd, shell=True, check=True)
        print("✅ Política do ImageMagick atualizada com sucesso.")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível atualizar policy.xml automaticamente. Erro: {e}")


fix_imagemagick_policy()

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


def burn_subtitles(video_path, srt_path, output_path):
    def generator(txt):
        return TextClip(
            txt,
            font='Arial',
            fontsize=24,
            color='white',
            stroke_color='black',
            stroke_width=1,
            method='caption',
            size=(500, None)
        )

    video = VideoFileClip(video_path)
    subtitles = SubtitlesClip(srt_path, generator)

    result = CompositeVideoClip([video, subtitles.set_pos(('center', 'bottom'))])

    result.write_videofile(
        output_path,
        fps=video.fps,
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        codec="libx264",
        audio_codec="aac"
    )

    video.close()
    return output_path


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
            srt_temp.close()

            status_text.warning("Renderizando vídeo com legendas... Isso pode demorar alguns minutos.")
            output_video_path = video_path.replace(".mp4", "_legendado.mp4")

            try:
                burn_subtitles(video_path, srt_temp.name, output_video_path)

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

            except OSError as e:
                if "ImageMagick" in str(e):
                    st.error("Erro: ImageMagick não foi encontrado.")
                    st.download_button(label="Baixar .srt", data=srt_content, file_name="legenda.srt")
                else:
                    st.error(f"Erro na renderização: {e}")

        except Exception as e:
            st.error(f"Ocorreu um erro geral: {e}")
