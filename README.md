# Translating Helper

This github contains two different notebooks, to help with translation tasks. They are not intended for (and cannot be used to) transcribe or translate audio from scratch. Someone could probably figure out a pipeline to do that, but that isn't what this repo is.

Rather it is only used to when there is a line of dialogue you have trouble making out, or when you can't think of a way to word a phrase in English (or any other target language).

I use these notebooks from time to time when translating anime Drama CDs, so others might be able to use it too.

## Requirements

Everything on this repo is written for [Python](https://www.python.org/downloads/), and makes use of existing libraries (namely [openai-whisper](https://github.com/openai/whisper) and [openai](https://github.com/openai/openai-python)). You will also need an [OpenAI API key](https://platform.openai.com/docs/quickstart). Although you do need to pay for OpenAI API credits, the model used for this project (`gpt-4o-mini`) is pretty cheap (price per token is [pretty low](https://openai.com/api/pricing/)).

The IDE used for this project is [Visual Studio Code](https://code.visualstudio.com/)

## Set Up

```bash
python -m venv venv
venv/scripts/activate
pip install -r requirements.txt
```

### CUDA Support

If you have a CUDA GPU with large enough VRAM, you can install PyTorch with CUDA support for faster transcribing.

|  Size  | Parameters | English-only model | Multilingual model | Required VRAM | Relative speed |
|:------:|:----------:|:------------------:|:------------------:|:-------------:|:--------------:|
|  tiny  |    39 M    |     `tiny.en`      |       `tiny`       |     ~1 GB     |      ~10x      |
|  base  |    74 M    |     `base.en`      |       `base`       |     ~1 GB     |      ~7x       |
| small  |   244 M    |     `small.en`     |      `small`       |     ~2 GB     |      ~4x       |
| medium |   769 M    |    `medium.en`     |      `medium`      |     ~5 GB     |      ~2x       |
| large  |   1550 M   |        N/A         |      `large`       |    ~10 GB     |       1x       |
| turbo  |   809 M    |        N/A         |      `turbo`       |     ~6 GB     |      ~8x       |

Check the version of CUDA you have installed then install it [here](https://pytorch.org/get-started/locally/). If you can't find your CUDA version, you can check the archive [here](https://pytorch.org/get-started/previous-versions/)

```bash
nvcc --version
```

## Usage

This project is used through 2 notebooks, `nb_transcription.ipynb` and `nb_translate.ipynb`.

- `nb_transcription.ipynb` 

    1. Run cells one, two, and three to set up the libraries and install OpenAI's whisper model (this part may take a while). **By default, the large model is used**, but you can change this to any of the smaller models at the cost of accuracy.

    2. Set the path to the file you want to transcribe in cell four (This path is relative).

    3. Run the cell.

- `nb_translate.ipynb`

    1. Run cells one and two to load the model. You will be asked to provide you **OpenAI API Key**.

    2. In cell three, update the text variable with what you want to translate and run the cell.
    It will give five different answers in no specific order.

