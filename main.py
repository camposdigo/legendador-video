import streamlit as st
import whisper
import os
import tempfile
from datetime import timedelta
from deep_translator import GoogleTranslator
import subprocess
import shutil
from gtts import gTTS
from pydub import AudioSegment

st.set_page_config(page_title="Legendador e Dublador EN->PT", layout="centered")

st.title("🎬 Legendador e Dublador Automático")
st.markdown("Faça upload de um vídeo em **Inglês**, traduza e escolha gerar legenda, dublagem ou ambos em **Português**.")

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

def translate_segments(transcription_segments):
    srt_content = ""
    translated_data = []
    translator = GoogleTranslator(source='en', target='pt')
    
    progress_bar = st.progress(0, text="Traduzindo segmentos...")
    total = len(transcription_segments)

    for i, segment in enumerate(transcription_segments):
        start_sec = segment['start']
        end_sec = segment['end']
        original_text = segment['text'].strip()

        try:
            translated_text = translator.translate(original_text)
        except Exception:
            translated_text = original_text

        # Guarda dados para a dublagem
        translated_data.append({
            'start': start_sec,
            'end': end_sec,
            'text': translated_text
        })

        # Formata para o SRT
        srt_content += f"{i + 1}\n"
        srt_content += f"{format_timestamp(start_sec)} --> {format_timestamp(end_sec)}\n"
        srt_content += f"{translated_text}\n\n"
        
        progress_bar.progress((i + 1) / total, text=f"Traduzindo: {i + 1}/{total}")

    progress_bar.empty()
    return srt_content, translated_data

def generate_dubbed_audio(translated_segments, video_path):
    progress_bar = st.progress(0, text="Extraindo áudio original...")
    
    # Cria uma trilha de áudio em silêncio com o mesmo tamanho do vídeo original
    original_audio = AudioSegment.from_file(video_path)
    final_audio = AudioSegment.silent(duration=len(original_audio))
    
    total = len(translated_segments)
    
    for i, seg in enumerate(translated_segments):
        progress_bar.progress((i + 1) / total, text=f"Gerando áudio (Dublagem): {i + 1}/{total}")
        text = seg['text'].strip()
        start_ms = int(seg['start'] * 1000)
        
        if text:
            try:
                # Gera o TTS
                tts = gTTS(text, lang='pt')
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_tts:
                    tts.save(temp_tts.name)
                    temp_tts_path = temp_tts.name
                
                # Carrega o áudio gerado e sobrepõe na trilha final no tempo exato
                fala = AudioSegment.from_file(temp_tts_path)
                final_audio = final_audio.overlay(fala, position=start_ms)
                
                # Limpa temp
                os.remove(temp_tts_path)
            except Exception as e:
                st.warning(f"Erro ao dublar trecho '{text}': {e}")
                
    progress_bar.empty()
    
    # Exporta o áudio dublado final
    audio_output_path = video_path.replace(".mp4", "_dub_audio.wav")
    final_audio.export(audio_output_path, format="wav")
    return audio_output_path

def process_video_ffmpeg(video_input, srt_input, audio_input, video_output, mode):
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise Exception("FFmpeg não encontrado no sistema.")

    # Ajuste de caminho do SRT para o FFmpeg no Windows (evita erros de escape)
    srt_input_escaped = srt_input.replace("\\", "/")

    cmd = [ffmpeg_path, "-i", video_input]
    
    if audio_input and mode in ["Dublado", "Legenda + Dublagem"]:
        cmd.extend(["-i", audio_input])

    if mode == "Apenas Legenda":
        cmd.extend([
            "-vf", f"subtitles='{srt_input_escaped}':force_style='FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=20'",
            "-c:a", "copy",
            "-preset", "veryfast"
        ])
    elif mode == "Dublado":
        cmd.extend([
            "-c:v", "copy",
            "-map", "0:v:0", # Pega vídeo do arquivo 0
            "-map", "1:a:0", # Pega áudio do arquivo 1 (Dublagem)
            "-c:a", "aac"
        ])
    elif mode == "Legenda + Dublagem":
        cmd.extend([
            "-vf", f"subtitles='{srt_input_escaped}':force_style='FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=20'",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:a", "aac",
            "-preset", "veryfast"
        ])

    cmd.extend([video_output, "-y"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Erro no FFmpeg: {result.stderr}")
    
    return video_output

# --- Interface do Streamlit ---

uploaded_file = st.file_uploader("Escolha um arquivo de vídeo", type=["mp4", "mov", "avi"])
process_mode = st.radio("Selecione o que deseja gerar:", ["Apenas Legenda", "Dublado", "Legenda + Dublagem"])

if uploaded_file is not None:
    # Salvar vídeo original
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_path = tfile.name
    tfile.close()

    st.video(video_path)

    if st.button("Processar Vídeo"):
        st.divider()
        status_text = st.empty()

        audio_dublado_path = None
        srt_temp_path = None

        try:
            status_text.info("Carregando IA e transcrevendo áudio original...")
            model = load_whisper_model()
            result = model.transcribe(video_path, task="transcribe", language="en")

            status_text.info("Traduzindo...")
            srt_content, translated_data = translate_segments(result['segments'])

            # Salvar SRT
            srt_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.srt', mode='w', encoding='utf-8')
            srt_temp.write(srt_content)
            srt_temp_path = srt_temp.name
            srt_temp.close()

            # Gerar Áudio se necessário
            if process_mode in ["Dublado", "Legenda + Dublagem"]:
                status_text.info("Gerando dublagem com gTTS...")
                audio_dublado_path = generate_dubbed_audio(translated_data, video_path)

            # Renderização Final
            status_text.warning("Renderizando vídeo final via FFmpeg...")
            output_video_path = video_path.replace(".mp4", "_final.mp4")

            process_video_ffmpeg(video_path, srt_temp_path, audio_dublado_path, output_video_path, process_mode)
            
            status_text.success("Vídeo gerado com sucesso!")

            # Botões de Download
            with open(output_video_path, "rb") as file:
                st.download_button(
                    label="⬇️ Baixar Vídeo Processado (.mp4)",
                    data=file,
                    file_name="video_processado.mp4",
                    mime="video/mp4"
                )

            st.download_button(
                label="Baixar Legenda gerada (.srt)",
                data=srt_content,
                file_name="legenda.srt",
                mime="text/plain"
            )

            st.video(output_video_path)

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
        
        finally:
            # Limpeza de arquivos temporários
            for p in [video_path, srt_temp_path, audio_dublado_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
