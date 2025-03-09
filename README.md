# Translating Helper 📝🎤

This repository provides a **translation helper tool** designed to assist when **transcribing difficult-to-hear dialogue** or **refining translations into natural phrasing**. 
It is **not intended for full audio transcription or translation automation**, though an advanced pipeline could be built for such tasks.

Originally, I created this tool to help with **translating anime Drama CDs**, especially when struggling with unclear dialogue  or finding the best way to phrase something in English (or another target language). 
With the new **interactive UI**, it is now easier for others to use as well.

⚠ **Note**: This tool is **not meant** for automatic translation of full audio files. It assists in transcribing difficult-to-hear dialogue and improving translations by providing multiple phrasing options.

## Features 🌟
- **🎤 Transcribe:** Convert spoken dialogue into text.
- **🌍 Translate:** Generate multiple translation options for a given phrase.
- **✅ Grade:** Evaluate translation accuracy, fluency, and cultural appropriateness.
- **⚙ Configuration:** Customize settings for transcription and translation.

## **Installation & Setup** 🛠

### **1. Clone the Repository**

```bash
git clone https://github.com/dragonstonehafiz/translator-helper.git
cd translator-helper
```

### **2. Create a Virtual Environment & Install Dependencies**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### **3. Run the Streamlit UI**
```bash
streamlit run TranslatorHelper.py
```

## **Usage Guide 📖**

Once the UI is launched, navigate to the provided URL. You'll see the following tabs:

### **1️⃣ Transcribe**
- Upload an audio file (`.mp3`, `.wav`).
- Select your model and language.
- Click **"Transcribe"** to generate a text transcript.

### **2️⃣ Translate**
- Enter the text you want to translate.
- Choose the target language.
- Click **"Translate"** to receive multiple translation suggestions.

### **3️⃣ Grade**
- Enter both the original and translated text.
- Click **"Grade Translation"** to evaluate accuracy, fluency, and cultural adaptation.

### **4️⃣ Configuration**
- Set API keys, select models, and adjust translation settings.

## **Requirements 📋**
- Python 3.8+
- [Streamlit](https://streamlit.io/) (for UI)
- [OpenAI Whisper](https://github.com/openai/whisper) (for transcription)
- [OpenAI GPT-4](https://openai.com/api/) (for translation)
- CUDA (optional, for faster transcription)

### **CUDA Support (Optional) 🚀**
If you have a **CUDA-compatible GPU**, you can install **PyTorch with CUDA** for **faster transcription**.

1. **Check your installed CUDA version**:
   ```bash
   nvcc --version
   ```

2. **Download the correct PyTorch version** based on your CUDA version:  
   - Official installation guide: [PyTorch CUDA Installation](https://pytorch.org/get-started/locally/)  
   - For older versions: [PyTorch Archive](https://pytorch.org/get-started/previous-versions/)  

3. **Install PyTorch with CUDA support**:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

#### **Whisper Model VRAM Requirements**
|  Size  | Parameters | English-only model | Multilingual model | Required VRAM | Relative speed |
|:------:|:----------:|:------------------:|:------------------:|:-------------:|:--------------:|
|  tiny  |    39 M    |     `tiny.en`      |       `tiny`       |     ~1 GB     |      ~10x      |
|  base  |    74 M    |     `base.en`      |       `base`       |     ~1 GB     |      ~7x       |
| small  |   244 M    |     `small.en`     |      `small`       |     ~2 GB     |      ~4x       |
| medium |   769 M    |    `medium.en`     |      `medium`      |     ~5 GB     |      ~2x       |
| large  |   1550 M   |        N/A         |      `large`       |    ~10 GB     |       1x       |
| turbo  |   809 M    |        N/A         |      `turbo`       |     ~6 GB     |      ~8x       |
