# AutoSubtitle AI

### Automatic Video Transcription, Translation & Dubbing

Aplicação em Python que transforma vídeos em inglês em conteúdo acessível em português por meio de **transcrição automática, tradução, geração de legendas e dublagem neural**.

> **Problema:** legendar e adaptar vídeos para outro idioma manualmente exige transcrição, tradução, sincronização e edição de áudio.
>
> **Solução:** o AutoSubtitle AI automatiza esse fluxo em uma única interface: o usuário envia o vídeo, escolhe o modo de processamento e recebe o conteúdo final em português.

## Pipeline

```text
Vídeo em inglês
      ↓
OpenAI Whisper
      ↓
Transcrição segmentada
      ↓
Tradução EN → PT-BR
      ↓
┌──────────────┬──────────────┐
│ Legenda SRT  │ Dublagem TTS │
└──────────────┴──────────────┘
      ↓
FFmpeg
      ↓
Vídeo final
```

## Funcionalidades

- Upload de vídeos MP4, MOV e AVI
- Transcrição automática de áudio em inglês
- Tradução dos segmentos para português
- Geração automática de arquivo `.srt`
- Sincronização das legendas com o vídeo
- Dublagem neural em português brasileiro
- Alternância de vozes durante a dublagem
- Renderização do vídeo final com FFmpeg
- Download do vídeo processado e da legenda
- Interface web com Streamlit

## Modos disponíveis

### Apenas Legenda

Transcreve, traduz e incorpora legendas em português ao vídeo.

### Dublado (Demo)

Gera uma faixa de áudio em português e substitui o áudio do vídeo.

### Legenda + Dublagem

Combina os dois fluxos e entrega um vídeo traduzido com legenda e áudio em português.

## Tecnologias

- Python
- OpenAI Whisper
- Streamlit
- FFmpeg
- Edge TTS
- pydub
- deep-translator
- asyncio

## Casos de uso

A arquitetura pode ser adaptada para:

- localização de vídeos e treinamentos
- criação automática de legendas
- tradução de conteúdo educacional
- acessibilidade audiovisual
- processamento de vídeos em lote
- geração de arquivos SRT para edição profissional

## Instalação

Clone o projeto:

```bash
git clone https://github.com/camposdigo/legendador-video.git
cd legendador-video
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

O FFmpeg também precisa estar disponível no sistema.

### Ubuntu / Debian

```bash
sudo apt install ffmpeg
```

## Execução

```bash
streamlit run main.py
```

Depois, abra o endereço informado pelo Streamlit no navegador.

## Fluxo de utilização

1. Faça upload de um vídeo em inglês.
2. Escolha entre legenda, dublagem ou ambos.
3. Clique em **Processar Vídeo**.
4. Aguarde a transcrição, tradução e renderização.
5. Baixe o vídeo final ou o arquivo de legenda `.srt`.

## Estrutura

```text
legendador-video/
├── main.py
├── requirements.txt
├── packages.txt
└── runtime.txt
```

## Próximas evoluções

- seleção de idioma de origem e destino
- escolha manual de voz
- processamento em lote
- revisão da transcrição antes da renderização
- identificação automática de diferentes locutores
- API para integração com outras aplicações

## Autor

**Rodrigo Campos**

Python • Automação • IA • Processamento de Áudio e Vídeo
