"""Viral Formula Studio — multimodal reverse engineering of a creator's viral formula.

Pipeline: videos -> transcriptions + frames -> style & editing profiles -> dossier.
The model provider (OpenAI now, IBM watsonx/Granite for submission) is configured
in one place: studio/factory.py + MODEL_PROVIDER in .env.
"""
